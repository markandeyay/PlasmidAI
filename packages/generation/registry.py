from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal


DEFAULT_REGISTRY_PATH = Path("data/models/registry.jsonl")
ROLLOUT_STATES = {"registered", "shadow", "canary", "full", "retired", "blocked"}

RolloutState = Literal["registered", "shadow", "canary", "full", "retired", "blocked"]


@dataclass(frozen=True)
class ModelRegistryRecord:
    model_version: str
    base_model: str
    training_data_snapshot_id: str
    hyperparameter_config: dict[str, Any]
    eval_scores: dict[str, Any]
    training_timestamp: str
    license_status: str
    rollout_state: RolloutState = "registered"
    training_cost: float | None = None
    artifact_uri: str | None = None
    model_id: str = "sequence-generator"
    code_revision: str | None = None
    notes: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.model_version.strip():
            raise ValueError("model_version is required")
        if not self.base_model.strip():
            raise ValueError("base_model is required")
        if not self.training_data_snapshot_id.strip():
            raise ValueError("training_data_snapshot_id is required")
        if self.rollout_state not in ROLLOUT_STATES:
            raise ValueError(f"unsupported rollout_state: {self.rollout_state}")

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> ModelRegistryRecord:
        return cls(
            model_version=str(row["model_version"]),
            base_model=str(row["base_model"]),
            training_data_snapshot_id=str(row["training_data_snapshot_id"]),
            hyperparameter_config=dict(row.get("hyperparameter_config") or {}),
            eval_scores=dict(row.get("eval_scores") or {}),
            training_timestamp=str(row["training_timestamp"]),
            training_cost=float(row["training_cost"]) if row.get("training_cost") is not None else None,
            license_status=str(row.get("license_status") or "unknown"),
            rollout_state=str(row.get("rollout_state") or "registered"),  # type: ignore[arg-type]
            artifact_uri=row.get("artifact_uri"),
            model_id=str(row.get("model_id") or "sequence-generator"),
            code_revision=row.get("code_revision"),
            notes=row.get("notes"),
            metadata=dict(row.get("metadata") or {}),
        )

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


class ModelRegistry:
    def __init__(self, path: Path = DEFAULT_REGISTRY_PATH) -> None:
        self.path = path

    def list(self) -> list[ModelRegistryRecord]:
        if not self.path.exists():
            return []
        records: list[ModelRegistryRecord] = []
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                records.append(ModelRegistryRecord.from_dict(json.loads(line)))
            except Exception as exc:
                raise ValueError(f"invalid model registry row {self.path}:{line_number}: {exc}") from exc
        return records

    def get(self, model_version: str) -> ModelRegistryRecord | None:
        for record in self.list():
            if record.model_version == model_version:
                return record
        return None

    def append(self, record: ModelRegistryRecord) -> None:
        if self.get(record.model_version) is not None:
            raise ValueError(f"model version already registered: {record.model_version}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(record.to_json_line() + "\n")

    def active_by_state(self, state: RolloutState) -> list[ModelRegistryRecord]:
        return [record for record in self.list() if record.rollout_state == state]


def register_record(
    *,
    registry_path: Path,
    model_version: str,
    base_model: str,
    training_data_snapshot_id: str,
    hyperparameter_config: dict[str, Any],
    eval_scores: dict[str, Any],
    license_status: str,
    rollout_state: RolloutState,
    training_cost: float | None = None,
    artifact_uri: str | None = None,
    model_id: str = "sequence-generator",
    code_revision: str | None = None,
    notes: str | None = None,
    metadata: dict[str, Any] | None = None,
    training_timestamp: str | None = None,
) -> ModelRegistryRecord:
    record = ModelRegistryRecord(
        model_version=model_version,
        base_model=base_model,
        training_data_snapshot_id=training_data_snapshot_id,
        hyperparameter_config=hyperparameter_config,
        eval_scores=eval_scores,
        training_timestamp=training_timestamp or datetime.now(UTC).isoformat(),
        training_cost=training_cost,
        license_status=license_status,
        rollout_state=rollout_state,
        artifact_uri=artifact_uri,
        model_id=model_id,
        code_revision=code_revision,
        notes=notes,
        metadata=metadata or {},
    )
    ModelRegistry(registry_path).append(record)
    return record


def parse_json_arg(value: str, *, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} must be a JSON object")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the Phase 2 sequence-generator model registry.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    register = subparsers.add_parser("register", help="Append one model registry record.")
    register.add_argument("--registry-path", type=Path, default=DEFAULT_REGISTRY_PATH)
    register.add_argument("--version", required=True)
    register.add_argument("--base-model", required=True)
    register.add_argument("--training-data-snapshot-id", required=True)
    register.add_argument("--hyperparameters-json", default="{}")
    register.add_argument("--eval-scores-json", default="{}")
    register.add_argument("--license-status", default="unknown")
    register.add_argument("--rollout-state", choices=sorted(ROLLOUT_STATES), default="registered")
    register.add_argument("--training-cost", type=float, default=None)
    register.add_argument("--artifact-uri", default=None)
    register.add_argument("--model-id", default="sequence-generator")
    register.add_argument("--code-revision", default=None)
    register.add_argument("--notes", default=None)
    register.add_argument("--metadata-json", default="{}")

    list_models = subparsers.add_parser("list", help="List registered model versions.")
    list_models.add_argument("--registry-path", type=Path, default=DEFAULT_REGISTRY_PATH)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "register":
        record = register_record(
            registry_path=args.registry_path,
            model_version=args.version,
            base_model=args.base_model,
            training_data_snapshot_id=args.training_data_snapshot_id,
            hyperparameter_config=parse_json_arg(args.hyperparameters_json, label="hyperparameters-json"),
            eval_scores=parse_json_arg(args.eval_scores_json, label="eval-scores-json"),
            license_status=args.license_status,
            rollout_state=args.rollout_state,
            training_cost=args.training_cost,
            artifact_uri=args.artifact_uri,
            model_id=args.model_id,
            code_revision=args.code_revision,
            notes=args.notes,
            metadata=parse_json_arg(args.metadata_json, label="metadata-json"),
        )
        print(record.to_json_line())
        return 0
    if args.command == "list":
        records = ModelRegistry(args.registry_path).list()
        print(json.dumps([asdict(record) for record in records], indent=2, sort_keys=True))
        return 0
    raise ValueError(f"unsupported registry command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
