from __future__ import annotations

from datetime import UTC, datetime

from packages.application.outcomes import InMemoryOutcomeStore
from packages.core.schemas import OutcomeReport
from packages.feedback.training_signal import derive_training_signal
from packages.generation.registry import ModelRegistry, ModelRegistryRecord


def registry(tmp_path) -> ModelRegistry:
    path = tmp_path / "registry.jsonl"
    ModelRegistry(path).append(
        ModelRegistryRecord(
            model_version="generator-v1",
            base_model="Carbon-3B",
            training_data_snapshot_id="phase2-snapshot",
            hyperparameter_config={},
            eval_scores={},
            training_timestamp="2026-06-07T00:00:00Z",
            license_status="research-ok",
        )
    )
    return ModelRegistry(path)


def report(*, label: str = "positive", consent: bool = True, model_version: str = "generator-v1") -> OutcomeReport:
    return OutcomeReport(
        design_id="design-1",
        model_version=model_version,
        construct_validated=(label == "positive"),
        sequencing_result="Sanger sequencing matched expected insert.",
        expression_result="Reporter signal observed.",
        training_consent=consent,
        outcome_label=label,
        provenance={
            "request_text": "Design a GFP reporter plasmid.",
            "template": {"plasmid_id": "curated:pEGFP-N1"},
            "target": {"sequence_sha256": "abc123"},
        },
    )


def test_derive_training_signal_writes_examples_and_marks_derived(tmp_path) -> None:
    store = InMemoryOutcomeStore()
    store.create(report=report(), user_id="user-1", outcome_id="outcome-1")

    summary = derive_training_signal(
        outcome_store=store,
        registry=registry(tmp_path),
        output_dir=tmp_path / "phase5",
        timestamp=datetime(2026, 6, 7, 12, 0, tzinfo=UTC),
    )

    output = (tmp_path / "phase5" / "outcomes_2026-06-07-120000.jsonl").read_text(encoding="utf-8")
    assert summary["examples_written"] == 1
    assert "positive_triplet" in output
    assert store.list_underived() == []


def test_derive_training_signal_excludes_missing_consent_and_unknown_models(tmp_path) -> None:
    store = InMemoryOutcomeStore()
    store.create(report=report(consent=False), user_id="user-1", outcome_id="outcome-no-consent")
    store.create(report=report(model_version="missing-model"), user_id="user-1", outcome_id="outcome-missing-model")

    summary = derive_training_signal(
        outcome_store=store,
        registry=registry(tmp_path),
        output_dir=tmp_path / "phase5",
        timestamp=datetime(2026, 6, 7, 12, 0, tzinfo=UTC),
    )

    exclusions = (tmp_path / "phase5" / "outcomes_2026-06-07-120000_exclusions.jsonl").read_text(encoding="utf-8")
    assert summary["examples_written"] == 0
    assert summary["exclusions_written"] == 2
    assert "training_consent_missing" in exclusions
    assert "model_version_not_registered" in exclusions
