from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from packages.core.schemas import AnnotatedSequence, DesignSpec
from packages.validation.common import CHECK_VERSION
from packages.validation.engine import ConstraintEngine
from packages.validation.gold import DEFAULT_GOLD_PATH


def load_gold(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate_gold(path: Path) -> dict[str, Any]:
    engine = ConstraintEngine()
    cases = load_gold(path)
    results = []
    correct = 0
    for case in cases:
        spec = DesignSpec.model_validate(case["design_spec"])
        annotated = AnnotatedSequence.model_validate(case["annotated_sequence"])
        report = engine.validate(annotated, spec)
        predicted = "FAIL" if report.overall == "FAIL" else "PASS"
        expected = case["expected"]
        is_correct = predicted == expected
        correct += int(is_correct)
        results.append(
            {
                "id": case["id"],
                "category": case["category"],
                "expected": expected,
                "predicted": predicted,
                "overall": report.overall,
                "correct": is_correct,
                "checks": [check.model_dump(mode="json") for check in report.checks],
            }
        )
    accuracy = correct / len(cases) if cases else 0.0
    return {
        "gold_path": str(path),
        "engine_version": CHECK_VERSION,
        "total": len(cases),
        "correct": correct,
        "accuracy": accuracy,
        "phase3_gate_met": accuracy >= 0.95 and len(cases) >= 100,
        "results": results,
    }


def write_report(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    json_path = output_dir / f"{timestamp}-validation-baseline.json"
    md_path = output_dir / f"{timestamp}-validation-baseline.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    failures = [item for item in report["results"] if not item["correct"]]
    md_path.write_text(
        "\n".join(
            [
                "# Phase 3 Validation Baseline",
                "",
                f"- Engine version: `{report['engine_version']}`",
                f"- Gold cases: `{report['total']}`",
                f"- Accuracy: `{report['accuracy']:.3f}`",
                f"- Phase 3 gate met: `{report['phase3_gate_met']}`",
                f"- Misclassified cases: `{len(failures)}`",
                "",
                "## Misclassifications",
                "",
                *(f"- `{item['id']}` expected `{item['expected']}` predicted `{item['predicted']}`" for item in failures),
                "",
            ]
        ),
        encoding="utf-8",
    )
    return json_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the deterministic Phase 3 validation gold set.")
    parser.add_argument("--gold-path", type=Path, default=DEFAULT_GOLD_PATH)
    parser.add_argument("--output-dir", type=Path, default=Path("data/eval/validation"))
    args = parser.parse_args()
    report = evaluate_gold(args.gold_path)
    json_path, md_path = write_report(report, args.output_dir)
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "accuracy": report["accuracy"], "phase3_gate_met": report["phase3_gate_met"]}))


if __name__ == "__main__":
    main()
