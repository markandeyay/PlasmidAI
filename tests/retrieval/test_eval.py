from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from packages.core.schemas import DesignSpec, Plasmid, RetrievalResult, RetrievedPlasmid
from packages.retrieval.eval import (
    GoldRecord,
    RetrievedEvalMatch,
    evaluate_pipeline,
    first_acceptable_rank,
    is_acceptable_match,
    load_gold,
    render_markdown_report,
    write_report,
)


class FakePipeline:
    def __init__(self, results: dict[str, RetrievalResult]) -> None:
        self.results = results
        self.calls: list[tuple[str, int]] = []

    def design_retrieval(self, free_text: str, *, k: int = 5) -> RetrievalResult:
        self.calls.append((free_text, k))
        return self.results[free_text]


def plasmid(plasmid_id: str, name: str | None = None) -> Plasmid:
    return Plasmid(
        id=plasmid_id,
        source="curated" if plasmid_id.startswith("curated:") else "genbank",
        name=name or plasmid_id,
        sequence="ACGT" * 100,
        length=400,
        organism="synthetic construct",
        vector_type="plasmid",
        markers=[],
        promoters=[],
        use_cases=[],
        annotation_complete=True,
        raw_ref=f"raw/{plasmid_id}.gb",
    )


def retrieval_result(ids: list[str]) -> RetrievalResult:
    return RetrievalResult(
        spec=DesignSpec(organism="Escherichia coli"),
        retrieved=[
            RetrievedPlasmid(plasmid=plasmid(plasmid_id), score=1.0 / (index + 1), matched_fields=["semantic"])
            for index, plasmid_id in enumerate(ids)
        ],
        recommendations=[],
        generated_by="fake",
    )


def test_id_matching_handles_source_prefix_and_case() -> None:
    assert is_acceptable_match("curated:pUC19", ["puc19"])
    assert is_acceptable_match("pUC19", ["curated:pUC19"])
    assert not is_acceptable_match("curated:pUC18", ["pUC19"])


def test_first_acceptable_rank_is_one_based() -> None:
    matches = [
        RetrievedEvalMatch("curated:pBR322", "pBR322", 0.9, []),
        RetrievedEvalMatch("curated:pUC19", "pUC19", 0.8, []),
    ]

    assert first_acceptable_rank(matches, ["pUC19"]) == 2
    assert first_acceptable_rank(matches, ["pGEX-4T-1"]) is None


def test_evaluate_pipeline_computes_top1_top5_and_mrr() -> None:
    records = [
        GoldRecord("q1", ["pUC19"], "r1", "s1"),
        GoldRecord("q2", ["pGEX-4T-1"], "r2", "s2"),
        GoldRecord("q3", ["pRS416"], "r3", "s3"),
    ]
    pipeline = FakePipeline(
        {
            "q1": retrieval_result(["curated:pUC19", "curated:pBR322"]),
            "q2": retrieval_result(["curated:pUC19", "curated:pBR322", "curated:pGEX-4T-1"]),
            "q3": retrieval_result(["curated:pUC19"]),
        }
    )

    report = evaluate_pipeline(
        records,
        pipeline,
        gold_path="gold.jsonl",
        top_k=5,
        generated_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert report.top1_hit_rate == pytest.approx(1 / 3)
    assert report.top5_hit_rate == pytest.approx(2 / 3)
    assert report.mrr == pytest.approx((1.0 + (1.0 / 3.0)) / 3.0)
    assert pipeline.calls == [("q1", 5), ("q2", 5), ("q3", 5)]


def test_load_gold_validates_jsonl_records(tmp_path) -> None:
    path = tmp_path / "gold.jsonl"
    path.write_text(
        json.dumps({"query": "q", "acceptable_target_ids": ["pUC19"], "rationale": "because", "source": "manifest"}),
        encoding="utf-8",
    )

    records = load_gold(path)

    assert records == [GoldRecord("q", ["pUC19"], "because", "manifest")]

    path.write_text(json.dumps({"query": "q", "acceptable_target_ids": [], "rationale": "because", "source": "manifest"}), encoding="utf-8")
    with pytest.raises(ValueError, match="acceptable_target_ids"):
        load_gold(path)


def test_render_markdown_report_and_write_report(tmp_path) -> None:
    records = [GoldRecord("q1", ["pUC19"], "r1", "s1")]
    report = evaluate_pipeline(
        records,
        FakePipeline({"q1": retrieval_result(["curated:pUC19"])}),
        gold_path="gold.jsonl",
        generated_at=datetime(2026, 5, 31, 12, 30, tzinfo=UTC),
    )

    markdown = render_markdown_report(report)
    markdown_path, json_path = write_report(report, tmp_path)

    assert "Top-1 hit rate" in markdown
    assert "curated:pUC19" in markdown
    assert markdown_path.exists()
    assert json_path is not None and json_path.exists()
    assert json.loads(json_path.read_text(encoding="utf-8"))["top1_hit_rate"] == 1.0
