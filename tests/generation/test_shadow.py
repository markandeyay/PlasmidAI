from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from packages.core.schemas import DesignSpec, Plasmid, RetrievedPlasmid
from packages.generation import FakeGenerator, MarkerSwap
from packages.generation.registry import ModelRegistryRecord
from packages.generation.shadow import (
    InMemoryShadowLogSink,
    JsonlShadowLogSink,
    ShadowComparisonRecord,
    ShadowComparisonGenerator,
    ShadowPayload,
    ShadowRetentionPolicy,
    incumbent_record,
    payload_is_expired,
    shadow_candidate_records,
    should_serve_model,
    should_shadow_model,
    should_sample_payload,
)


def _template() -> RetrievedPlasmid:
    plasmid = Plasmid(
        id="curated:pUC19",
        source="curated",
        name="pUC19c",
        sequence="AAAACCCCGGGGTTTT",
        length=16,
        organism="Cloning vector pUC19c",
        vector_type="bacterial_cloning_vector",
        markers=["AmpR"],
        promoters=["lac promoter region"],
        use_cases=["bacterial_cloning"],
        annotation_complete=True,
        raw_ref="raw/curated/pUC19.gb",
    )
    return RetrievedPlasmid(plasmid=plasmid, score=1.0, matched_fields=["semantic"])


def _registry_record(version: str, state: str) -> ModelRegistryRecord:
    return ModelRegistryRecord(
        model_version=version,
        base_model="HuggingFaceBio/Carbon-3B",
        training_data_snapshot_id="snapshot",
        hyperparameter_config={},
        eval_scores={},
        training_timestamp="2026-06-06T00:00:00+00:00",
        license_status="internal_eval_only",
        rollout_state=state,  # type: ignore[arg-type]
    )


def test_shadow_generator_returns_incumbent_output_and_logs_candidate() -> None:
    sink = InMemoryShadowLogSink()
    incumbent = FakeGenerator(version="incumbent")
    candidate = FakeGenerator(version="candidate")
    generator = ShadowComparisonGenerator(
        incumbent=incumbent,
        candidate=candidate,
        log_sink=sink,
        request_id_factory=lambda: "request-1",
    )

    generated = generator.generate(DesignSpec(organism="Escherichia coli"), [_template()], n=2)

    assert [item.model_version for item in generated] == ["incumbent", "incumbent"]
    assert len(sink.records) == 1
    record = sink.records[0]
    assert record.request_id == "request-1"
    assert record.incumbent_model_version == "incumbent"
    assert record.candidate_model_version == "candidate"
    assert record.served_model_version == "incumbent"
    assert record.incumbent_count == 2
    assert record.candidate_count == 2
    assert record.candidate_error is None
    assert record.incumbent_latency_ms is not None
    assert record.candidate_latency_ms is not None
    assert record.total_latency_ms is not None
    assert len(record.incumbent_outputs) == 2
    assert len(record.candidate_outputs) == 2
    assert record.exact_sequence_match is True
    assert record.comparison_label == "candidate_equal"
    assert record.payload_retention == "hash_only"


def test_shadow_generator_suppresses_candidate_failure() -> None:
    @dataclass(frozen=True)
    class FailingGenerator:
        @property
        def model_version(self) -> str:
            return "failing-candidate"

        def generate(self, spec, templates, n=1):
            del spec, templates, n
            raise RuntimeError("candidate unavailable")

    sink = InMemoryShadowLogSink()
    generator = ShadowComparisonGenerator(
        incumbent=FakeGenerator(version="incumbent"),
        candidate=FailingGenerator(),
        log_sink=sink,
    )

    generated = generator.generate(DesignSpec(organism="Escherichia coli"), [_template()])

    assert generated[0].model_version == "incumbent"
    assert sink.records[0].candidate_count == 0
    assert sink.records[0].candidate_error == "candidate unavailable"
    assert sink.records[0].candidate_error_class == "RuntimeError"
    assert sink.records[0].comparison_label == "not_evaluable"
    assert sink.records[0].reason_codes == ["candidate_error"]


def test_shadow_generator_logs_candidate_divergence() -> None:
    sink = InMemoryShadowLogSink()
    generator = ShadowComparisonGenerator(
        incumbent=FakeGenerator(version="incumbent"),
        candidate=FakeGenerator(
            marker_swap=MarkerSwap(original_sequence="CCCC", replacement_sequence="TTTT"),
            version="candidate",
        ),
        log_sink=sink,
    )

    generated = generator.generate(DesignSpec(organism="Escherichia coli"), [_template()])

    assert generated[0].model_version == "incumbent"
    record = sink.records[0]
    assert record.exact_sequence_match is False
    assert record.sequence_identity == 0.0
    assert record.length_delta_bp == 0
    assert record.parent_template_overlap == 1
    assert record.comparison_label == "candidate_diverged"
    assert record.reason_codes == ["sequence_hash_differs"]


def test_shadow_log_sink_failure_does_not_break_served_output() -> None:
    class FailingSink:
        def record(self, comparison: ShadowComparisonRecord) -> None:
            del comparison
            raise RuntimeError("log sink unavailable")

    generator = ShadowComparisonGenerator(
        incumbent=FakeGenerator(version="incumbent"),
        candidate=FakeGenerator(version="candidate"),
        log_sink=FailingSink(),
    )

    generated = generator.generate(DesignSpec(organism="Escherichia coli"), [_template()])

    assert generated[0].model_version == "incumbent"


def test_rollout_state_helpers_gate_serving_and_shadow_records() -> None:
    registered = _registry_record("registered", "registered")
    shadow = _registry_record("shadow", "shadow")
    canary = _registry_record("canary", "canary")
    full = _registry_record("full", "full")

    assert should_serve_model(full) is True
    assert should_serve_model(canary) is True
    assert should_serve_model(shadow) is False
    assert should_shadow_model(shadow) is True
    assert should_shadow_model(registered) is False
    assert incumbent_record([registered, shadow, canary, full]) == full
    assert shadow_candidate_records([registered, shadow, canary, full]) == [shadow]


def test_shadow_log_sink_writes_jsonl_payload_records(tmp_path) -> None:
    sink = JsonlShadowLogSink(tmp_path)
    created_at = datetime(2026, 6, 6, 12, 0, tzinfo=UTC)

    written = sink.append(
        ShadowPayload(
            payload_id="payload-1",
            payload_class="raw",
            created_at=created_at,
            payload={"prompt": "design reporter"},
        )
    )

    assert written is True
    records = sink.iter_records("raw")
    assert records == [
        {
            "payload_id": "payload-1",
            "payload_class": "raw",
            "created_at": "2026-06-06T12:00:00+00:00",
            "payload": {"prompt": "design reporter"},
        }
    ]


def test_shadow_log_sink_applies_class_sampling(tmp_path) -> None:
    sink = JsonlShadowLogSink(
        tmp_path,
        policy=ShadowRetentionPolicy(raw_sample_rate=0.0, redacted_sample_rate=1.0),
    )

    assert sink.append(ShadowPayload(payload_id="raw-1", payload_class="raw", payload={"secret": "drop"})) is False
    assert sink.append(ShadowPayload(payload_id="redacted-1", payload_class="redacted", payload={"prompt": "keep"})) is True

    assert sink.iter_records("raw") == []
    assert [record["payload_id"] for record in sink.iter_records("redacted")] == ["redacted-1"]


def test_shadow_log_sink_prunes_expired_payloads_by_class(tmp_path) -> None:
    now = datetime(2026, 6, 30, tzinfo=UTC)
    sink = JsonlShadowLogSink(tmp_path)
    sink.append(ShadowPayload(payload_id="raw-old", payload_class="raw", created_at=now - timedelta(days=8), payload={}))
    sink.append(ShadowPayload(payload_id="redacted-kept", payload_class="redacted", created_at=now - timedelta(days=20), payload={}))
    sink.append(ShadowPayload(payload_id="aggregate-kept", payload_class="aggregate", created_at=now - timedelta(days=80), payload={}))
    sink.append(ShadowPayload(payload_id="aggregate-old", payload_class="aggregate", created_at=now - timedelta(days=91), payload={}))

    result = sink.prune(now=now)

    assert result.removed == 2
    assert result.kept == 2
    assert sink.iter_records("raw") == []
    assert [record["payload_id"] for record in sink.iter_records("redacted")] == ["redacted-kept"]
    assert [record["payload_id"] for record in sink.iter_records("aggregate")] == ["aggregate-kept"]


def test_payload_is_expired_uses_default_phase2_retention_windows() -> None:
    now = datetime(2026, 6, 30, tzinfo=UTC)

    assert payload_is_expired("raw", now - timedelta(days=8), now=now) is True
    assert payload_is_expired("redacted", now - timedelta(days=8), now=now) is False
    assert payload_is_expired("aggregate", now - timedelta(days=80), now=now) is False


def test_sampling_is_deterministic_for_fractional_rates() -> None:
    first = should_sample_payload("payload-42", 0.25)

    assert should_sample_payload("payload-42", 0.25) is first
