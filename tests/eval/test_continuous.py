from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from packages.eval.continuous import (
    RegressionThresholds,
    build_dashboard,
    collect_suite_reports,
    compare_metrics,
    render_dashboard_markdown,
    write_dashboard,
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_collect_suite_reports_and_render_dashboard(tmp_path: Path) -> None:
    write_fixture_reports(tmp_path)

    suites = collect_suite_reports(
        retrieval_dir=tmp_path / "retrieval",
        generation_dir=tmp_path / "generation",
        validation_dir=tmp_path / "validation",
        quality_dir=tmp_path / "quality",
    )
    dashboard = build_dashboard(
        suites,
        commit="abc123",
        generated_at=datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC),
    )
    markdown = render_dashboard_markdown(dashboard)

    assert dashboard["overall_status"] == "PASS"
    assert dashboard["metrics"]["retrieval"]["top5_hit_rate"] == 1.0
    assert dashboard["metrics"]["generation"]["strict_generation_success_rate"] == 0.0
    assert dashboard["metrics"]["validation"]["accuracy"] == 1.0
    assert dashboard["metrics"]["validation"]["known_good_tiers"]["A"]["total"] == 25
    assert dashboard["metrics"]["quality"]["complete_annotations"] == 141
    assert "## Headline Metrics" in markdown
    assert "### Known-Good Tiers" in markdown
    assert "No threshold breaches." in markdown


def test_compare_metrics_flags_regressions() -> None:
    current = {
        "retrieval": {"top5_hit_rate": 0.90, "mrr": 0.80},
        "validation": {"accuracy": 0.96},
        "quality": {"complete_annotations": 120, "parse_errors": 1},
    }
    previous = {
        "retrieval": {"top5_hit_rate": 1.0, "mrr": 0.95},
        "validation": {"accuracy": 1.0},
        "quality": {"complete_annotations": 141, "parse_errors": 0},
    }

    regressions = compare_metrics(current, previous, RegressionThresholds())

    breached = {(item["area"], item["metric"]) for item in regressions if item["breached"]}
    assert ("retrieval", "top5_hit_rate") in breached
    assert ("retrieval", "mrr") in breached
    assert ("validation", "accuracy") in breached
    assert ("quality", "complete_annotations") in breached
    assert ("quality", "parse_errors") in breached


def test_write_dashboard_emits_json_and_markdown(tmp_path: Path) -> None:
    write_fixture_reports(tmp_path)
    suites = collect_suite_reports(
        retrieval_dir=tmp_path / "retrieval",
        generation_dir=tmp_path / "generation",
        validation_dir=tmp_path / "validation",
        quality_dir=tmp_path / "quality",
    )
    dashboard = build_dashboard(
        suites,
        commit="abc123",
        generated_at=datetime(2026, 6, 15, 12, 34, 56, tzinfo=UTC),
    )

    json_path, markdown_path = write_dashboard(dashboard, tmp_path)

    assert json_path.name == "dashboard_2026-06-15-123456.json"
    assert markdown_path.name == "dashboard_2026-06-15-123456.md"
    assert load_json(json_path)["commit"] == "abc123"
    assert "# Continuous Evaluation Dashboard" in markdown_path.read_text(encoding="utf-8")


def write_fixture_reports(root: Path) -> None:
    write_json(
        root / "retrieval" / "2026-06-15-000000-retrieval-baseline.json",
        {
            "total_queries": 21,
            "retrieval_queries": 20,
            "clarification_queries": 1,
            "top1_hit_rate": 0.9,
            "top5_hit_rate": 1.0,
            "mrr": 0.9375,
            "clarification_pass_rate": 1.0,
        },
    )
    write_json(
        root / "generation" / "2026-06-15-000000-generation-eval.json",
        {
            "generator_mode": "fake",
            "generator_version": "fake-template-generator-v1",
            "metrics": {
                "gold_cases": 15,
                "scored_cases": 13,
                "component_complete_rate": 0.615,
                "phase2_gate_proxy_rate": 0.615,
                "strict_generation_success_rate": 0.0,
                "novel_rate": 0.0,
            },
        },
    )
    write_json(
        root / "validation" / "2026-06-15-000000-validation-baseline.json",
        {
            "accuracy": 1.0,
            "known_good_count": 36,
            "known_bad_count": 52,
            "known_good_tiers": {
                "A": {"accuracy": 1.0, "correct": 25, "total": 25},
                "B": {"accuracy": 1.0, "correct": 11, "total": 11},
            },
            "tier_a_accuracy": 1.0,
            "tier_b_accuracy": 1.0,
            "total": 88,
            "phase3_gate_met": True,
            "per_check_accuracy": {
                "codon_usage": {"accuracy": 1.0, "correct": 44, "total": 44},
            },
        },
    )
    write_json(
        root / "quality" / "2026-06-15-000000-quality-report.json",
        {
            "total_records": 256,
            "annotation_complete": {"count": 141, "rate": 0.550781},
            "profiles": {"unclassified": 99},
            "parse_errors": [],
            "duplicate_cluster_count": 3,
        },
    )


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
