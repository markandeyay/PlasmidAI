from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.generation.registry import ModelRegistry, ModelRegistryRecord, main, register_record


def test_model_registry_appends_and_lists_records(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.jsonl"
    record = ModelRegistryRecord(
        model_version="carbon-lora-001",
        base_model="HuggingFaceBio/Carbon-3B",
        training_data_snapshot_id="snapshot-1",
        hyperparameter_config={"learning_rate": 2e-4},
        eval_scores={"strict_generation_success_rate": 0.5},
        training_timestamp="2026-06-06T00:00:00+00:00",
        training_cost=12.5,
        license_status="internal_eval_only",
        rollout_state="shadow",
    )

    registry = ModelRegistry(registry_path)
    registry.append(record)

    loaded = registry.list()
    assert loaded == [record]
    assert registry.get("carbon-lora-001") == record
    assert registry.active_by_state("shadow") == [record]


def test_model_registry_rejects_duplicate_versions(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.jsonl"
    registry = ModelRegistry(registry_path)
    record = ModelRegistryRecord(
        model_version="duplicate",
        base_model="base",
        training_data_snapshot_id="snapshot",
        hyperparameter_config={},
        eval_scores={},
        training_timestamp="2026-06-06T00:00:00+00:00",
        license_status="unknown",
    )

    registry.append(record)

    with pytest.raises(ValueError, match="already registered"):
        registry.append(record)


def test_register_record_creates_parent_directory(tmp_path: Path) -> None:
    registry_path = tmp_path / "models" / "registry.jsonl"

    record = register_record(
        registry_path=registry_path,
        model_version="carbon-lora-002",
        base_model="HuggingFaceBio/Carbon-3B",
        training_data_snapshot_id="snapshot-2",
        hyperparameter_config={"lora_r": 16},
        eval_scores={"novel_rate": 1.0},
        license_status="internal_eval_only",
        rollout_state="registered",
        training_timestamp="2026-06-06T00:00:00+00:00",
    )

    assert registry_path.exists()
    assert ModelRegistry(registry_path).get("carbon-lora-002") == record


def test_registry_cli_registers_and_lists_models(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    registry_path = tmp_path / "registry.jsonl"

    assert (
        main(
            [
                "register",
                "--registry-path",
                str(registry_path),
                "--version",
                "carbon-lora-cli",
                "--base-model",
                "HuggingFaceBio/Carbon-3B",
                "--training-data-snapshot-id",
                "snapshot-cli",
                "--hyperparameters-json",
                '{"learning_rate": 0.0002}',
                "--eval-scores-json",
                '{"strict_generation_success_rate": 0.5}',
                "--license-status",
                "internal_eval_only",
            ]
        )
        == 0
    )
    registered = json.loads(capsys.readouterr().out)
    assert registered["model_version"] == "carbon-lora-cli"

    assert main(["list", "--registry-path", str(registry_path)]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed[0]["base_model"] == "HuggingFaceBio/Carbon-3B"
