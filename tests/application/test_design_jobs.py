from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from packages.application.design_jobs import GenerationDesignJobHandler
from packages.application.designs import InMemoryDesignStore
from packages.core.schemas import AnnotatedSequence


@dataclass
class FakePipeline:
    calls: list[str]
    result: Any | None = None

    def run(self, free_text: str) -> Any:
        self.calls.append(free_text)
        return self.result if self.result is not None else object()


def _annotated_sequence() -> AnnotatedSequence:
    return AnnotatedSequence(
        sequence="ACGT" * 10,
        topology="circular",
        vector_profile="bacterial_cloning_vector",
        annotation_complete=True,
        features=[],
    )


def test_generation_design_job_handler_uses_accumulated_context(monkeypatch) -> None:
    design_store = InMemoryDesignStore()
    pipeline = FakePipeline(calls=[], result=SimpleNamespace(reannotated_sequence=_annotated_sequence()))
    monkeypatch.setattr(
        "packages.application.design_jobs.spike_result_as_dict",
        lambda result: {
            "design_spec": {"organism": "Escherichia coli"},
            "annotated_sequence": result.reannotated_sequence.model_dump(mode="json"),
            "validation_report": {"overall": "PASS"},
            "retrieved_templates": [],
            "recommendations": [{"why_relevant": "Template is relevant."}],
        },
    )

    result = GenerationDesignJobHandler(pipeline=pipeline, design_store=design_store)(
        job_id="job-ctx",
        session_id="session-1",
        action="refine",
        payload={"instruction": "switch marker", "context": ["build vector", "switch marker"]},
    )

    assert pipeline.calls == ["build vector\nswitch marker"]
    assert result["design_spec"] == {"organism": "Escherichia coli"}
    assert result["recommendation_text"] == "Template is relevant."
    assert result["design_id"]
    stored = design_store.get(result["design_id"])
    assert stored is not None
    assert stored.job_id == "job-ctx"
    assert stored.session_id == "session-1"


def test_generation_design_job_handler_rejects_invalid_action_and_empty_text() -> None:
    pipeline = FakePipeline(calls=[])
    handler = GenerationDesignJobHandler(pipeline=pipeline, design_store=InMemoryDesignStore())

    for action, payload in [("delete", {"text": "no"}), ("design", {})]:
        try:
            handler(job_id="job-1", session_id="session-1", action=action, payload=payload)
        except ValueError:
            pass
        else:
            raise AssertionError("expected invalid queued design job to fail")


def test_generation_design_job_handler_returns_clarification_as_result() -> None:
    class ClarifyingPipeline:
        def run(self, free_text: str) -> Any:
            assert free_text == "make a viral vector"
            raise ValueError("intent clarification required: Which viral vector system should this use?")

    design_store = InMemoryDesignStore()
    result = GenerationDesignJobHandler(ClarifyingPipeline(), design_store)(
        job_id="job-clarify",
        session_id="session-1",
        action="design",
        payload={"text": "make a viral vector"},
    )

    assert result["design_id"] is None
    assert result["clarification_question"] == "Which viral vector system should this use?"
    assert result["design_spec"]["clarification_needed"] is True
    assert design_store.records == {}
