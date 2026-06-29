from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from packages.application.designs import DesignStore
from packages.generation.spike import GenerationSpikePipeline, spike_result_as_dict


CLARIFICATION_ERROR_PREFIX = "intent clarification required:"


class DesignPipeline(Protocol):
    def run(self, free_text: str) -> Any: ...


@dataclass(frozen=True)
class GenerationDesignJobHandler:
    """Run the retrieval-grounded generation pipeline behind the worker queue."""

    pipeline: DesignPipeline
    design_store: DesignStore

    def __call__(self, *, job_id: str, session_id: str, action: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if action not in {"design", "refine"}:
            raise ValueError(f"unsupported design job action: {action}")
        context = payload.get("context")
        if isinstance(context, list) and context:
            free_text = "\n".join(str(item) for item in context)
        else:
            free_text = str(payload.get("text") or payload.get(action) or "").strip()
        if not free_text:
            raise ValueError("design job requires non-empty text")
        try:
            result = self.pipeline.run(free_text)
        except ValueError as exc:
            clarification = _clarification_from_error(exc)
            if clarification is None:
                raise
            return {
                "design_id": None,
                "design_spec": {
                    "clarification_needed": True,
                    "clarification_question": clarification,
                },
                "clarification_question": clarification,
                "annotated_sequence": None,
                "validation_report": None,
                "retrieved_templates": [],
                "recommendations": [],
                "recommendation_text": None,
            }
        serialized = spike_result_as_dict(result)
        design = self.design_store.create(
            session_id=session_id,
            job_id=job_id,
            annotated_sequence=result.reannotated_sequence,
        )
        return {
            "design_id": design.design_id,
            "design_spec": serialized["design_spec"],
            "clarification_question": None,
            "annotated_sequence": serialized["annotated_sequence"],
            "validation_report": serialized["validation_report"],
            "retrieved_templates": serialized["retrieved_templates"],
            "recommendations": serialized["recommendations"],
            "recommendation_text": _recommendation_text(serialized["recommendations"]),
        }


def build_generation_design_job_handler(pipeline: GenerationSpikePipeline, design_store: DesignStore) -> GenerationDesignJobHandler:
    return GenerationDesignJobHandler(pipeline=pipeline, design_store=design_store)


def _clarification_from_error(exc: ValueError) -> str | None:
    message = str(exc).strip()
    if not message.lower().startswith(CLARIFICATION_ERROR_PREFIX):
        return None
    clarification = message[len(CLARIFICATION_ERROR_PREFIX) :].strip()
    return clarification or "Could you clarify the design goal?"


def _recommendation_text(recommendations: list[dict[str, Any]]) -> str | None:
    if not recommendations:
        return None
    first = recommendations[0].get("why_relevant")
    return str(first) if isinstance(first, str) and first.strip() else None
