from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_EVAL_DIR = Path("data/eval")
DEFAULT_RETRIEVAL_DIR = DEFAULT_EVAL_DIR / "retrieval"
DEFAULT_GENERATION_DIR = DEFAULT_EVAL_DIR / "generation"
DEFAULT_VALIDATION_DIR = DEFAULT_EVAL_DIR / "validation"
DEFAULT_QUALITY_DIR = DEFAULT_EVAL_DIR / "quality"


@dataclass(frozen=True)
class RegressionThresholds:
    retrieval_top5_drop: float = 0.05
    retrieval_mrr_drop: float = 0.10
    validation_accuracy_drop: float = 0.02
    complete_annotation_drop: int = 10
    parse_error_increase: int = 0


def latest_json(directory: Path, pattern: str) -> Path:
    paths = sorted(directory.glob(pattern), key=lambda path: (path.stat().st_mtime, path.name), reverse=True)
    if not paths:
        raise FileNotFoundError(f"no reports matching {directory / pattern}")
    return paths[0]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_suite_reports(
    *,
    retrieval_dir: Path = DEFAULT_RETRIEVAL_DIR,
    generation_dir: Path = DEFAULT_GENERATION_DIR,
    validation_dir: Path = DEFAULT_VALIDATION_DIR,
    quality_dir: Path = DEFAULT_QUALITY_DIR,
) -> dict[str, dict[str, Any]]:
    retrieval_path = latest_json(retrieval_dir, "*-retrieval-baseline.json")
    generation_path = latest_json(generation_dir, "*-generation-eval.json")
    validation_path = latest_json(validation_dir, "*-validation-baseline.json")
    quality_path = latest_json(quality_dir, "*-quality-report.json")
    return {
        "retrieval": {"path": str(retrieval_path), "report": load_json(retrieval_path)},
        "generation": {"path": str(generation_path), "report": load_json(generation_path)},
        "validation": {"path": str(validation_path), "report": load_json(validation_path)},
        "quality": {"path": str(quality_path), "report": load_json(quality_path)},
    }


def build_dashboard(
    suites: dict[str, dict[str, Any]],
    *,
    commit: str,
    generated_at: datetime | None = None,
    previous: dict[str, Any] | None = None,
    thresholds: RegressionThresholds | None = None,
) -> dict[str, Any]:
    timestamp = generated_at or datetime.now(UTC)
    thresholds = thresholds or RegressionThresholds()
    metrics = extract_metrics(suites)
    regressions = compare_metrics(metrics, previous.get("metrics") if previous else None, thresholds)
    return {
        "generated_at": timestamp.astimezone(UTC).isoformat(),
        "commit": commit,
        "compared_to": previous.get("dashboard_path") if previous else None,
        "overall_status": "REGRESSION" if any(item["breached"] for item in regressions) else "PASS",
        "thresholds": {
            "retrieval_top5_drop": thresholds.retrieval_top5_drop,
            "retrieval_mrr_drop": thresholds.retrieval_mrr_drop,
            "validation_accuracy_drop": thresholds.validation_accuracy_drop,
            "complete_annotation_drop": thresholds.complete_annotation_drop,
            "parse_error_increase": thresholds.parse_error_increase,
        },
        "source_reports": {name: value["path"] for name, value in suites.items()},
        "metrics": metrics,
        "regressions": regressions,
    }


def extract_metrics(suites: dict[str, dict[str, Any]]) -> dict[str, Any]:
    retrieval = suites["retrieval"]["report"]
    generation = suites["generation"]["report"]
    validation = suites["validation"]["report"]
    quality = suites["quality"]["report"]
    generation_metrics = generation["metrics"]
    annotation = quality["annotation_complete"]
    return {
        "retrieval": {
            "total_queries": retrieval["total_queries"],
            "retrieval_queries": retrieval["retrieval_queries"],
            "clarification_queries": retrieval["clarification_queries"],
            "top1_hit_rate": retrieval["top1_hit_rate"],
            "top5_hit_rate": retrieval["top5_hit_rate"],
            "mrr": retrieval["mrr"],
            "clarification_pass_rate": retrieval.get("clarification_pass_rate"),
        },
        "generation": {
            "generator_mode": generation["generator_mode"],
            "generator_version": generation["generator_version"],
            "gold_cases": generation_metrics["gold_cases"],
            "scored_cases": generation_metrics["scored_cases"],
            "component_complete_rate": generation_metrics["component_complete_rate"],
            "phase2_gate_proxy_rate": generation_metrics["phase2_gate_proxy_rate"],
            "strict_generation_success_rate": generation_metrics["strict_generation_success_rate"],
            "novel_rate": generation_metrics["novel_rate"],
        },
        "validation": {
            "accuracy": validation["accuracy"],
            "known_good_count": validation.get("known_good_count"),
            "known_bad_count": validation.get("known_bad_count"),
            "known_good_tiers": validation.get("known_good_tiers", {}),
            "tier_a_accuracy": validation.get("tier_a_accuracy"),
            "tier_b_accuracy": validation.get("tier_b_accuracy"),
            "total": validation["total"],
            "phase3_gate_met": validation["phase3_gate_met"],
            "per_check_accuracy": validation.get("per_check_accuracy", {}),
        },
        "quality": {
            "total_records": quality["total_records"],
            "complete_annotations": annotation["count"],
            "complete_annotation_rate": annotation["rate"],
            "unclassified_records": quality["profiles"]["unclassified"],
            "parse_errors": len(quality["parse_errors"]),
            "duplicate_clusters": quality["duplicate_cluster_count"],
        },
    }


def compare_metrics(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
    thresholds: RegressionThresholds,
) -> list[dict[str, Any]]:
    comparisons = [
        metric_row(
            "retrieval",
            "top5_hit_rate",
            current["retrieval"]["top5_hit_rate"],
            previous["retrieval"]["top5_hit_rate"] if previous else None,
            -thresholds.retrieval_top5_drop,
            lower_is_better=False,
        ),
        metric_row(
            "retrieval",
            "mrr",
            current["retrieval"]["mrr"],
            previous["retrieval"]["mrr"] if previous else None,
            -thresholds.retrieval_mrr_drop,
            lower_is_better=False,
        ),
        metric_row(
            "validation",
            "accuracy",
            current["validation"]["accuracy"],
            previous["validation"]["accuracy"] if previous else None,
            -thresholds.validation_accuracy_drop,
            lower_is_better=False,
        ),
        metric_row(
            "quality",
            "complete_annotations",
            current["quality"]["complete_annotations"],
            previous["quality"]["complete_annotations"] if previous else None,
            -thresholds.complete_annotation_drop,
            lower_is_better=False,
        ),
        metric_row(
            "quality",
            "parse_errors",
            current["quality"]["parse_errors"],
            previous["quality"]["parse_errors"] if previous else None,
            thresholds.parse_error_increase,
            lower_is_better=True,
        ),
    ]
    return comparisons


def metric_row(
    area: str,
    metric: str,
    current: float | int,
    previous: float | int | None,
    threshold: float | int,
    *,
    lower_is_better: bool,
) -> dict[str, Any]:
    delta = None if previous is None else current - previous
    breached = False
    if delta is not None:
        breached = delta > threshold if lower_is_better else delta < threshold
    return {
        "area": area,
        "metric": metric,
        "current": current,
        "previous": previous,
        "delta": delta,
        "threshold": threshold,
        "status": "REGRESSION" if breached else "PASS",
        "breached": breached,
    }


def render_dashboard_markdown(dashboard: dict[str, Any]) -> str:
    metrics = dashboard["metrics"]
    lines = [
        "# Continuous Evaluation Dashboard",
        "",
        f"- Generated at: `{dashboard['generated_at']}`",
        f"- Commit: `{dashboard['commit']}`",
        f"- Compared to: `{dashboard['compared_to'] or '<none>'}`",
        f"- Overall status: `{dashboard['overall_status']}`",
        "",
        "## Headline Metrics",
        "",
        "| Area | Metric | Current | Previous | Delta | Threshold | Status |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in dashboard["regressions"]:
        lines.append(
            "| {area} | {metric} | {current} | {previous} | {delta} | {threshold} | {status} |".format(
                area=item["area"],
                metric=item["metric"],
                current=format_value(item["current"]),
                previous=format_value(item["previous"]),
                delta=format_value(item["delta"]),
                threshold=format_value(item["threshold"]),
                status=item["status"],
            )
        )
    lines.extend(
        [
            "",
            "## Retrieval",
            "",
            f"- Source: `{dashboard['source_reports']['retrieval']}`",
            f"- Queries: `{metrics['retrieval']['total_queries']}`",
            f"- Scored retrieval queries: `{metrics['retrieval']['retrieval_queries']}`",
            f"- Top-1 hit rate: `{metrics['retrieval']['top1_hit_rate']:.3f}`",
            f"- Top-5 hit rate: `{metrics['retrieval']['top5_hit_rate']:.3f}`",
            f"- MRR: `{metrics['retrieval']['mrr']:.3f}`",
            f"- Clarification pass rate: `{format_value(metrics['retrieval']['clarification_pass_rate'])}`",
            "",
            "## Generation",
            "",
            f"- Source: `{dashboard['source_reports']['generation']}`",
            f"- Generator: `{metrics['generation']['generator_version']}`",
            f"- Mode: `{metrics['generation']['generator_mode']}`",
            f"- Scored cases: `{metrics['generation']['scored_cases']}`",
            f"- Component-complete rate: `{metrics['generation']['component_complete_rate']:.3f}`",
            f"- Phase 2 proxy rate: `{metrics['generation']['phase2_gate_proxy_rate']:.3f}`",
            f"- Strict generation success rate: `{metrics['generation']['strict_generation_success_rate']:.3f}`",
            "- Note: fake generation strict success is expected to remain zero because template-copy novelty is false.",
            "",
            "## Validation",
            "",
            f"- Source: `{dashboard['source_reports']['validation']}`",
            f"- Accuracy: `{metrics['validation']['accuracy']:.3f}`",
            f"- Known-good / known-bad: `{metrics['validation']['known_good_count']} / {metrics['validation']['known_bad_count']}`",
            f"- Total cases: `{metrics['validation']['total']}`",
            f"- Phase 3 gate met: `{metrics['validation']['phase3_gate_met']}`",
            "",
            "### Known-Good Tiers",
            "",
            "| Tier | Accuracy | Correct | Total |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for tier, stats in metrics["validation"]["known_good_tiers"].items():
        lines.append(f"| `{tier}` | {stats['accuracy']:.3f} | {stats['correct']} | {stats['total']} |")
    lines.extend(
        [
            "",
            "### Validation Checks",
            "",
            "| Check | Accuracy | Correct | Total |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for name, stats in metrics["validation"]["per_check_accuracy"].items():
        lines.append(f"| `{name}` | {stats['accuracy']:.3f} | {stats['correct']} | {stats['total']} |")
    lines.extend(
        [
            "",
            "## Corpus Health",
            "",
            f"- Source: `{dashboard['source_reports']['quality']}`",
            f"- Total records: `{metrics['quality']['total_records']}`",
            f"- Complete annotations: `{metrics['quality']['complete_annotations']}`",
            f"- Complete annotation rate: `{metrics['quality']['complete_annotation_rate']:.3f}`",
            f"- Unclassified records: `{metrics['quality']['unclassified_records']}`",
            f"- Parse errors: `{metrics['quality']['parse_errors']}`",
            f"- Duplicate clusters: `{metrics['quality']['duplicate_clusters']}`",
            "",
            "## Regressions",
            "",
        ]
    )
    breached = [item for item in dashboard["regressions"] if item["breached"]]
    if breached:
        lines.extend(f"- `{item['area']}.{item['metric']}` breached threshold: delta `{format_value(item['delta'])}`" for item in breached)
    else:
        lines.append("No threshold breaches.")
    return "\n".join(lines).rstrip() + "\n"


def format_value(value: Any) -> str:
    if value is None:
        return "<none>"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def previous_dashboard(output_dir: Path) -> dict[str, Any] | None:
    dashboards = sorted(output_dir.glob("dashboard_*.json"), key=lambda path: (path.stat().st_mtime, path.name), reverse=True)
    if not dashboards:
        return None
    report = load_json(dashboards[0])
    report["dashboard_path"] = str(dashboards[0])
    return report


def two_latest_dashboards(output_dir: Path) -> tuple[Path, Path | None]:
    dashboards = sorted(output_dir.glob("dashboard_*.json"), key=lambda path: (path.stat().st_mtime, path.name), reverse=True)
    if not dashboards:
        raise FileNotFoundError(f"no dashboard JSON files found under {output_dir}")
    return dashboards[0], dashboards[1] if len(dashboards) > 1 else None


def write_dashboard(dashboard: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.fromisoformat(dashboard["generated_at"]).astimezone(UTC).strftime("%Y-%m-%d-%H%M%S")
    stem = output_dir / f"dashboard_{timestamp}"
    json_path = stem.with_suffix(".json")
    markdown_path = stem.with_suffix(".md")
    json_path.write_text(json.dumps(dashboard, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_dashboard_markdown(dashboard), encoding="utf-8")
    return json_path, markdown_path


def git_commit_hash() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def dashboard_command(args: argparse.Namespace) -> int:
    thresholds = RegressionThresholds(
        retrieval_top5_drop=args.retrieval_top5_drop,
        retrieval_mrr_drop=args.retrieval_mrr_drop,
        validation_accuracy_drop=args.validation_accuracy_drop,
        complete_annotation_drop=args.complete_annotation_drop,
        parse_error_increase=args.parse_error_increase,
    )
    previous = previous_dashboard(args.output_dir)
    suites = collect_suite_reports()
    dashboard = build_dashboard(suites, commit=git_commit_hash(), previous=previous, thresholds=thresholds)
    json_path, markdown_path = write_dashboard(dashboard, args.output_dir)
    print(json.dumps({"json": str(json_path), "markdown": str(markdown_path), "status": dashboard["overall_status"]}, indent=2))
    return 0


def check_command(args: argparse.Namespace) -> int:
    current_path, previous_path = two_latest_dashboards(args.output_dir)
    current = load_json(current_path)
    current["dashboard_path"] = str(current_path)
    previous = load_json(previous_path) if previous_path else None
    if previous is not None:
        previous["dashboard_path"] = str(previous_path)
    thresholds = RegressionThresholds(
        retrieval_top5_drop=args.retrieval_top5_drop,
        retrieval_mrr_drop=args.retrieval_mrr_drop,
        validation_accuracy_drop=args.validation_accuracy_drop,
        complete_annotation_drop=args.complete_annotation_drop,
        parse_error_increase=args.parse_error_increase,
    )
    regressions = compare_metrics(current["metrics"], previous.get("metrics") if previous else None, thresholds)
    breached = [item for item in regressions if item["breached"]]
    print(json.dumps({"current": str(current_path), "previous": str(previous_path) if previous_path else None, "regressions": breached}, indent=2))
    return 1 if breached else 0


def add_threshold_args(parser: argparse.ArgumentParser) -> None:
    # Conservative defaults: retrieval top-5 should not lose a full gold query,
    # validation should remain effectively stable, corpus completeness should
    # not lose more than a small batch, and new parser errors should fail checks.
    parser.add_argument("--retrieval-top5-drop", type=float, default=0.05)
    parser.add_argument("--retrieval-mrr-drop", type=float, default=0.10)
    parser.add_argument("--validation-accuracy-drop", type=float, default=0.02)
    parser.add_argument("--complete-annotation-drop", type=int, default=10)
    parser.add_argument("--parse-error-increase", type=int, default=0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aggregate and check project evaluation reports.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    dashboard_parser = subparsers.add_parser("dashboard", help="Write a continuous-eval dashboard from newest suite reports.")
    dashboard_parser.add_argument("--output-dir", type=Path, default=DEFAULT_EVAL_DIR)
    add_threshold_args(dashboard_parser)
    dashboard_parser.set_defaults(func=dashboard_command)

    check_parser = subparsers.add_parser("check", help="Compare the newest dashboard to the previous dashboard.")
    check_parser.add_argument("--output-dir", type=Path, default=DEFAULT_EVAL_DIR)
    add_threshold_args(check_parser)
    check_parser.set_defaults(func=check_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
