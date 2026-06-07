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

DEFAULT_CURATED_GOOD_PATH = Path("data/eval/validation/curated_known_good.jsonl")
DEFAULT_CURATED_BAD_PATH = Path("data/eval/validation/curated_known_bad.jsonl")


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


def evaluate_curated_gold(good_path: Path, bad_path: Path) -> dict[str, Any]:
    engine = ConstraintEngine()
    good_cases = load_gold(good_path)
    bad_cases = load_gold(bad_path)
    results: list[dict[str, Any]] = []
    per_check: dict[str, dict[str, int]] = {}
    correct = 0

    def record_check(name: str, is_correct: bool) -> None:
        bucket = per_check.setdefault(name, {"total": 0, "correct": 0})
        bucket["total"] += 1
        bucket["correct"] += int(is_correct)

    for case in good_cases:
        spec = DesignSpec.model_validate(case["design_spec"])
        annotated = AnnotatedSequence.model_validate(case["annotated_sequence"])
        report = engine.validate(annotated, spec)
        check_statuses = {check.name: check.status for check in report.checks}
        is_correct = report.overall != "FAIL"
        correct += int(is_correct)
        for check_name, status in check_statuses.items():
            record_check(check_name, status != "FAIL")
        results.append(
            {
                "id": case["plasmid_id"],
                "set": "known_good",
                "name": case.get("name"),
                "vector_profile": case.get("vector_profile"),
                "expected": "PASS_OR_WARN",
                "predicted": "FAIL" if report.overall == "FAIL" else "PASS_OR_WARN",
                "overall": report.overall,
                "correct": is_correct,
                "checks": [check.model_dump(mode="json") for check in report.checks],
                "warn_justifications": case.get("warn_justifications", []),
            }
        )

    for case in bad_cases:
        spec = DesignSpec.model_validate(case["design_spec"])
        annotated = AnnotatedSequence.model_validate(case["annotated_sequence"])
        report = engine.validate(annotated, spec)
        check_statuses = {check.name: check.status for check in report.checks}
        expected_failing_checks = case.get("expected_failing_checks", [])
        failed_expected_checks = [
            check_name for check_name in expected_failing_checks if check_statuses.get(check_name) == "FAIL"
        ]
        is_correct = report.overall == "FAIL" and len(failed_expected_checks) == len(expected_failing_checks)
        correct += int(is_correct)
        for check_name in expected_failing_checks:
            record_check(check_name, check_statuses.get(check_name) == "FAIL")
        results.append(
            {
                "id": case["case_id"],
                "set": "known_bad",
                "category": case.get("check_category"),
                "source_plasmid_id": case.get("source_plasmid_id"),
                "defect_type": case.get("defect_type"),
                "expected": "FAIL",
                "predicted": "FAIL" if report.overall == "FAIL" else "PASS_OR_WARN",
                "overall": report.overall,
                "correct": is_correct,
                "expected_failing_checks": expected_failing_checks,
                "observed_failing_checks": [name for name, status in check_statuses.items() if status == "FAIL"],
                "checks": [check.model_dump(mode="json") for check in report.checks],
            }
        )

    total = len(good_cases) + len(bad_cases)
    accuracy = correct / total if total else 0.0
    per_check_accuracy = {
        name: {
            "total": bucket["total"],
            "correct": bucket["correct"],
            "accuracy": bucket["correct"] / bucket["total"] if bucket["total"] else 0.0,
        }
        for name, bucket in sorted(per_check.items())
    }
    return {
        "gold_policy": "curated_profile_diverse_quality_over_arbitrary_count",
        "known_good_path": str(good_path),
        "known_bad_path": str(bad_path),
        "engine_version": CHECK_VERSION,
        "known_good_count": len(good_cases),
        "known_bad_count": len(bad_cases),
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "per_check_accuracy": per_check_accuracy,
        "phase3_gate_met": accuracy >= 0.95 and len(good_cases) > 0 and len(bad_cases) > 0,
        "results": results,
    }


def write_report(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    json_path = output_dir / f"{timestamp}-validation-baseline.json"
    md_path = output_dir / f"{timestamp}-validation-baseline.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    failures = [item for item in report["results"] if not item["correct"]]
    per_check_lines = []
    if "per_check_accuracy" in report:
        per_check_lines = [
            "",
            "## Per-Check Accuracy",
            "",
            "| Check | Correct | Total | Accuracy |",
            "| --- | ---: | ---: | ---: |",
            *(
                f"| `{name}` | {stats['correct']} | {stats['total']} | {stats['accuracy']:.3f} |"
                for name, stats in report["per_check_accuracy"].items()
            ),
        ]
    md_path.write_text(
        "\n".join(
            [
                "# Phase 3 Validation Baseline",
                "",
                f"- Engine version: `{report['engine_version']}`",
                *( [f"- Gold policy: `{report['gold_policy']}`"] if "gold_policy" in report else [] ),
                *( [f"- Known-good cases: `{report['known_good_count']}`"] if "known_good_count" in report else [] ),
                *( [f"- Known-bad cases: `{report['known_bad_count']}`"] if "known_bad_count" in report else [] ),
                f"- Gold cases: `{report['total']}`",
                f"- Accuracy: `{report['accuracy']:.3f}`",
                f"- Phase 3 gate met: `{report['phase3_gate_met']}`",
                f"- Misclassified cases: `{len(failures)}`",
                *per_check_lines,
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
    parser.add_argument("--curated", action="store_true", help="Evaluate curated known-good and known-bad gold files.")
    parser.add_argument("--known-good-path", type=Path, default=DEFAULT_CURATED_GOOD_PATH)
    parser.add_argument("--known-bad-path", type=Path, default=DEFAULT_CURATED_BAD_PATH)
    parser.add_argument("--output-dir", type=Path, default=Path("data/eval/validation"))
    args = parser.parse_args()
    if args.curated:
        report = evaluate_curated_gold(args.known_good_path, args.known_bad_path)
    else:
        report = evaluate_gold(args.gold_path)
    json_path, md_path = write_report(report, args.output_dir)
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "accuracy": report["accuracy"], "phase3_gate_met": report["phase3_gate_met"]}))


if __name__ == "__main__":
    main()
