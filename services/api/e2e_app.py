from __future__ import annotations

"""Deterministic API app used by the browser-level full-stack E2E target."""

from typing import Any, Mapping

from packages.application import FakeJobQueue, InMemoryDesignStore, InMemoryJobStore, InMemorySessionStore
from packages.core.schemas import AnnotatedFeature, AnnotatedSequence, SequenceTopology
from services.api.app import RateLimitConfig, create_app


DESIGN_ID = "e2e-design"

_sessions = InMemorySessionStore()
_designs = InMemoryDesignStore()


def _annotated_sequence() -> AnnotatedSequence:
    sequence = "ATGC" * 300
    return AnnotatedSequence(
        sequence=sequence,
        topology=SequenceTopology.CIRCULAR,
        vector_profile="e2e_reporter_vector",
        annotation_complete=True,
        features=[
            AnnotatedFeature(start=0, end=180, type="promoter", strand=1, name="CMV promoter", confidence=0.95),
            AnnotatedFeature(start=210, end=780, type="GOI", strand=1, name="EGFP", confidence=0.98),
            AnnotatedFeature(start=820, end=980, type="terminator", strand=1, name="SV40 polyA", confidence=0.91),
            AnnotatedFeature(start=1000, end=1160, type="ORI", strand=1, name="pUC origin", confidence=0.93),
        ],
    )


def _handle_design_job(*, session_id: str, action: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    annotated = _annotated_sequence()
    _designs.create(
        session_id=session_id,
        job_id=str(payload.get("correlation_id") or "e2e-job"),
        design_id=DESIGN_ID,
        annotated_sequence=annotated,
    )
    return {
        "session_id": session_id,
        "action": action,
        "design_id": DESIGN_ID,
        "recommendation_text": "Generated deterministic full-stack E2E reporter plasmid.",
        "annotated_sequence": annotated.model_dump(mode="json"),
        "retrieved_templates": [
            {
                "source_id": "curated:e2e-template",
                "name": "E2E Reporter Template",
                "score": 0.99,
                "source": "curated",
                "vector_profile": "e2e_reporter_vector",
            }
        ],
        "validation_report": {
            "overall": "PASS",
            "checks": [
                {"name": "Sequence assembly", "status": "PASS", "message": "Deterministic E2E sequence assembled."}
            ],
            "generated_by_model_version": "e2e-deterministic-v1",
        },
    }


app = create_app(
    session_store=_sessions,
    job_queue=FakeJobQueue(store=InMemoryJobStore(), handler=_handle_design_job),
    design_store=_designs,
    rate_limit_config=RateLimitConfig(enabled=False),
)
