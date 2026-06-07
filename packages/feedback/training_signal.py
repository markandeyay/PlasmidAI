from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.application.outcomes import OutcomeRecord, OutcomeStore, PostgresOutcomeStore
from packages.generation.registry import DEFAULT_REGISTRY_PATH, ModelRegistry


DEFAULT_OUTPUT_DIR = Path("data/training/phase5")
FORMATTER_VERSION = "phase5-outcome-v1"


def derive_training_signal(
    *,
    outcome_store: OutcomeStore,
    registry: ModelRegistry,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    limit: int = 100,
    timestamp: datetime | None = None,
    mark_derived: bool = True,
) -> dict[str, Any]:
    timestamp = timestamp or datetime.now(UTC)
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_id = timestamp.strftime("outcomes_%Y-%m-%d-%H%M%S")
    output_path = output_dir / f"{snapshot_id}.jsonl"
    exclusions_path = output_dir / f"{snapshot_id}_exclusions.jsonl"

    records = outcome_store.list_underived(limit=limit)
    examples: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    derived_ids: list[str] = []

    for record in records:
        example, exclusion = _example_or_exclusion(record, registry)
        if example is not None:
            examples.append(example)
            derived_ids.append(record.outcome_id)
        else:
            exclusions.append(exclusion or _exclude(record, "unknown_exclusion"))

    _write_jsonl(output_path, examples)
    _write_jsonl(exclusions_path, exclusions)
    if mark_derived and derived_ids:
        outcome_store.mark_derived(derived_ids, derived_at=timestamp)

    summary = {
        "snapshot_id": snapshot_id,
        "formatter_version": FORMATTER_VERSION,
        "records_examined": len(records),
        "examples_written": len(examples),
        "exclusions_written": len(exclusions),
        "output_path": str(output_path),
        "exclusions_path": str(exclusions_path),
        "derived_outcome_ids": derived_ids,
        "model_registry_path": str(registry.path),
    }
    manifest_path = output_dir / f"{snapshot_id}_manifest.json"
    manifest_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary["manifest_path"] = str(manifest_path)
    return summary


def _example_or_exclusion(
    record: OutcomeRecord,
    registry: ModelRegistry,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    report = record.report
    if not report.training_consent:
        return None, _exclude(record, "training_consent_missing")
    model = registry.get(report.model_version)
    if model is None:
        return None, _exclude(record, "model_version_not_registered")
    if report.outcome_label == "ambiguous":
        return None, _exclude(record, "outcome_ambiguous")
    if report.outcome_label == "positive" and report.construct_validated is not True:
        return None, _exclude(record, "positive_requires_construct_validated")
    if report.outcome_label == "negative" and report.construct_validated is not False:
        return None, _exclude(record, "negative_requires_construct_failed")

    disposition = "positive_triplet" if report.outcome_label == "positive" else "negative_example"
    return {
        "example_id": f"{FORMATTER_VERSION}::{record.outcome_id}::{report.outcome_label}",
        "formatter_version": FORMATTER_VERSION,
        "training_disposition": disposition,
        "outcome_label": report.outcome_label,
        "design_id": report.design_id,
        "outcome_id": record.outcome_id,
        "model": {
            "model_version": report.model_version,
            "model_id": model.model_id,
            "base_model": model.base_model,
            "training_data_snapshot_id": model.training_data_snapshot_id,
        },
        "context": {
            "text": report.provenance.get("request_text", ""),
            "design_spec": report.provenance.get("design_spec", {}),
            "source": "outcome_capture",
        },
        "template": report.provenance.get("template", {}),
        "target": report.provenance.get("target", {"design_id": report.design_id}),
        "outcome": report.model_dump(mode="json"),
        "provenance": {
            "user_id": record.user_id,
            "created_at": record.created_at.isoformat(),
            "source": report.provenance,
        },
        "quality_flags": [],
    }, None


def _exclude(record: OutcomeRecord, reason: str) -> dict[str, Any]:
    return {
        "outcome_id": record.outcome_id,
        "design_id": record.design_id,
        "model_version": record.report.model_version,
        "reason": reason,
        "outcome_label": record.report.outcome_label,
        "training_consent": record.report.training_consent,
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Derive Phase 5 training signal from consented outcomes.")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--registry-path", type=Path, default=DEFAULT_REGISTRY_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.database_url:
        raise RuntimeError("DATABASE_URL must be set or passed with --database-url")
    summary = derive_training_signal(
        outcome_store=PostgresOutcomeStore(args.database_url),
        registry=ModelRegistry(args.registry_path),
        output_dir=args.output_dir,
        limit=args.limit,
        mark_derived=not args.dry_run,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
