from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from packages.application.design_jobs import GenerationDesignJobHandler


@dataclass
class FakePipeline:
    calls: list[str]

    def run(self, free_text: str) -> Any:
        self.calls.append(free_text)
        return object()


def test_generation_design_job_handler_uses_accumulated_context(monkeypatch) -> None:
    pipeline = FakePipeline(calls=[])
    monkeypatch.setattr(
        "packages.application.design_jobs.spike_result_as_dict",
        lambda result: {"serialized": result is not None},
    )

    result = GenerationDesignJobHandler(pipeline)(
        session_id="session-1",
        action="refine",
        payload={"instruction": "switch marker", "context": ["build vector", "switch marker"]},
    )

    assert pipeline.calls == ["build vector\nswitch marker"]
    assert result == {
        "session_id": "session-1",
        "action": "refine",
        "design": {"serialized": True},
    }


def test_generation_design_job_handler_rejects_invalid_action_and_empty_text() -> None:
    pipeline = FakePipeline(calls=[])
    handler = GenerationDesignJobHandler(pipeline)

    for action, payload in [("delete", {"text": "no"}), ("design", {})]:
        try:
            handler(session_id="session-1", action=action, payload=payload)
        except ValueError:
            pass
        else:
            raise AssertionError("expected invalid queued design job to fail")
