from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from packages.generation.spike import GenerationSpikePipeline, spike_result_as_dict


CLARIFICATION_ERROR_PREFIX = "intent clarification required:"


class DesignPipeline(Protocol):
    def run(self, free_text: str) -> Any: ...


@dataclass(frozen=True)
class GenerationDesignJobHandler:
    """Run the retrieval-grounded generation pipeline behind the worker queue."""

    pipeline: DesignPipeline

    def __call__(self, *, session_id: str, action: str, payload: Mapping[str, Any]) -> dict[str, Any]:
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
                "session_id": session_id,
                "action": action,
                "design": {
                    "design_spec": {
                        "clarification_needed": True,
                        "clarification_question": clarification,
                    },
                    "clarification_question": clarification,
                    "retrieved_templates": [],
                    "recommendations": [],
                    "recommendation_text": None,
                    "annotated_sequence": None,
                    "validation_report": None,
                },
            }
        serialized = spike_result_as_dict(result)
        return {
            "session_id": session_id,
            "action": action,
            "design": serialized,
        }


def build_generation_design_job_handler(pipeline: GenerationSpikePipeline) -> GenerationDesignJobHandler:
    return GenerationDesignJobHandler(pipeline=pipeline)


def _clarification_from_error(exc: ValueError) -> str | None:
    message = str(exc).strip()
    if not message.lower().startswith(CLARIFICATION_ERROR_PREFIX):
        return None
    clarification = message[len(CLARIFICATION_ERROR_PREFIX) :].strip()
    return clarification or "Could you clarify the design goal?"
