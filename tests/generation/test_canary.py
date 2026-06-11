from __future__ import annotations

from dataclasses import dataclass

import pytest

from packages.core.schemas import DesignSpec
from packages.generation import CanaryGenerator, CanaryPolicy, FakeGenerator, InMemoryCanaryMetricsSink
from tests.generation.test_shadow import _template


def _policy(percent: float, *, failures: int = 2, enabled: bool = True) -> CanaryPolicy:
    return CanaryPolicy(
        policy_id="policy-1",
        candidate_model_version="candidate",
        incumbent_model_version="incumbent",
        traffic_percent=percent,
        enabled=enabled,
        assignment_salt="test",
        max_consecutive_candidate_failures=failures,
    )


def test_canary_routes_candidate_when_bucket_in_percentage() -> None:
    sink = InMemoryCanaryMetricsSink()
    generator = CanaryGenerator(
        incumbent=FakeGenerator(version="incumbent"),
        candidate=FakeGenerator(version="candidate"),
        policy=_policy(100),
        metrics_sink=sink,
    )

    generated = generator.generate_for_request(
        DesignSpec(organism="Escherichia coli"),
        [_template()],
        assignment_key="session-1",
        request_id="request-1",
    )

    assert generated[0].model_version == "candidate"
    assert sink.records[0].assigned_model_version == "candidate"
    assert sink.records[0].served_model_version == "candidate"
    assert sink.records[0].fallback_served is False
    assert sink.records[0].reason_codes == ["candidate_assigned"]


def test_canary_routes_incumbent_when_policy_disabled() -> None:
    sink = InMemoryCanaryMetricsSink()
    generator = CanaryGenerator(
        incumbent=FakeGenerator(version="incumbent"),
        candidate=FakeGenerator(version="candidate"),
        policy=_policy(100, enabled=False),
        metrics_sink=sink,
    )

    generated = generator.generate_for_request(
        DesignSpec(organism="Escherichia coli"),
        [_template()],
        assignment_key="session-1",
        request_id="request-1",
    )

    assert generated[0].model_version == "incumbent"
    assert sink.records[0].eligible is False
    assert sink.records[0].reason_codes == ["policy_disabled", "incumbent_assigned"]


def test_canary_falls_back_and_triggers_rollback_after_repeated_candidate_failures() -> None:
    @dataclass(frozen=True)
    class FailingGenerator:
        @property
        def model_version(self) -> str:
            return "candidate"

        def generate(self, spec, templates, n=1):
            del spec, templates, n
            raise RuntimeError("candidate failed")

    sink = InMemoryCanaryMetricsSink()
    generator = CanaryGenerator(
        incumbent=FakeGenerator(version="incumbent"),
        candidate=FailingGenerator(),
        policy=_policy(100, failures=2),
        metrics_sink=sink,
    )

    for index in range(2):
        generated = generator.generate_for_request(
            DesignSpec(organism="Escherichia coli"),
            [_template()],
            assignment_key=f"session-{index}",
            request_id=f"request-{index}",
        )
        assert generated[0].model_version == "incumbent"

    assert sink.records[0].fallback_served is True
    assert sink.records[0].candidate_error_class == "RuntimeError"
    assert sink.records[1].rollback_active is True
    assert "rollback_triggered" in sink.records[1].reason_codes
    assert generator.rollback_active is True


def test_canary_policy_validates_percentage() -> None:
    with pytest.raises(ValueError, match="traffic_percent"):
        _policy(101)
