from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from packages.generation.spike import GenerationSpikePipeline, spike_result_as_dict


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
        result = self.pipeline.run(free_text)
        serialized = spike_result_as_dict(result)
        return {
            "session_id": session_id,
            "action": action,
            "design": serialized,
        }


def build_generation_design_job_handler(pipeline: GenerationSpikePipeline) -> GenerationDesignJobHandler:
    return GenerationDesignJobHandler(pipeline=pipeline)
