from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

from packages.core.schemas import DesignSpec, Plasmid, RetrievedPlasmid
from packages.generation.generator import FakeGenerator, MarkerSwap
from packages.generation.shadow import InMemoryShadowLogSink, ShadowComparisonGenerator, ShadowComparisonRecord


def load_gold_queries(path: Path, *, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("clarification_expected"):
            continue
        rows.append(row)
        if len(rows) >= limit:
            break
    if not rows:
        raise ValueError(f"no evaluable gold queries found in {path}")
    return rows


def shadow_template() -> RetrievedPlasmid:
    plasmid = Plasmid(
        id="shadow:template",
        source="generated",
        name="shadow-template",
        sequence="AAAACCCCGGGGTTTT",
        length=16,
        organism="Escherichia coli",
        vector_type="bacterial_cloning_vector",
        markers=["AmpR"],
        promoters=["lac promoter region"],
        use_cases=["shadow_eval"],
        annotation_complete=True,
        raw_ref="shadow://template",
    )
    return RetrievedPlasmid(plasmid=plasmid, score=1.0, matched_fields=["shadow_fixture"])


def summarize_records(records: list[ShadowComparisonRecord]) -> dict[str, Any]:
    identities = [record.sequence_identity for record in records if record.sequence_identity is not None]
    latency_incumbent = [record.incumbent_latency_ms for record in records if record.incumbent_latency_ms is not None]
    latency_candidate = [record.candidate_latency_ms for record in records if record.candidate_latency_ms is not None]
    label_counts: dict[str, int] = {}
    for record in records:
        label_counts[record.comparison_label] = label_counts.get(record.comparison_label, 0) + 1
    return {
        "records": len(records),
        "candidate_errors": sum(1 for record in records if record.candidate_error),
        "candidate_timeouts": sum(1 for record in records if record.candidate_timed_out),
        "exact_sequence_match_rate": rate(record.exact_sequence_match is True for record in records),
        "output_divergence_rate": rate(record.exact_sequence_match is False for record in records),
        "mean_sequence_identity": round(mean(identities), 4) if identities else None,
        "mean_incumbent_latency_ms": round(mean(latency_incumbent), 3) if latency_incumbent else None,
        "mean_candidate_latency_ms": round(mean(latency_candidate), 3) if latency_candidate else None,
        "comparison_labels": label_counts,
    }


def rate(values: Iterable[bool]) -> float:
    materialized = list(values)
    if not materialized:
        return 0.0
    return round(sum(1 for value in materialized if value) / len(materialized), 4)


def run_shadow_eval(gold_path: Path, *, limit: int, output_dir: Path) -> tuple[Path, Path]:
    rows = load_gold_queries(gold_path, limit=limit)
    sink = InMemoryShadowLogSink()
    generator = ShadowComparisonGenerator(
        incumbent=FakeGenerator(version="fake-incumbent-template-v1"),
        candidate=FakeGenerator(
            marker_swap=MarkerSwap(original_sequence="CCCC", replacement_sequence="TTTT"),
            version="fake-candidate-marker-swap-v1",
        ),
        log_sink=sink,
        request_id_factory=request_id_factory(),
    )
    template = shadow_template()
    for row in rows:
        spec = DesignSpec(organism="Escherichia coli", application=str(row["query"]))
        generator.generate(spec, [template], n=1)
    summary = summarize_records(sink.records)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{timestamp}-shadow-eval.json"
    md_path = output_dir / f"{timestamp}-shadow-eval.md"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gold_path": str(gold_path),
        "limit": limit,
        "summary": summary,
        "records": [asdict(record) for record in sink.records],
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return json_path, md_path


def request_id_factory():
    counter = 0

    def next_id() -> str:
        nonlocal counter
        counter += 1
        return f"shadow-gold-{counter:03d}"

    return next_id


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    return "\n".join(
        [
            "# Shadow Evaluation Baseline",
            "",
            f"- Generated at: `{payload['generated_at']}`",
            f"- Gold set: `{payload['gold_path']}`",
            f"- Records compared: `{summary['records']}`",
            f"- Candidate errors: `{summary['candidate_errors']}`",
            f"- Candidate timeouts: `{summary['candidate_timeouts']}`",
            f"- Exact sequence match rate: `{summary['exact_sequence_match_rate']}`",
            f"- Output divergence rate: `{summary['output_divergence_rate']}`",
            f"- Mean sequence identity: `{summary['mean_sequence_identity']}`",
            f"- Mean incumbent latency ms: `{summary['mean_incumbent_latency_ms']}`",
            f"- Mean candidate latency ms: `{summary['mean_candidate_latency_ms']}`",
            "",
            "## Comparison Labels",
            "",
            *[f"- `{label}`: `{count}`" for label, count in sorted(summary["comparison_labels"].items())],
            "",
            "## Notes",
            "",
            "This is an offline dry run using deterministic fake generators. It validates shadow logging, correlation, and divergence reporting without GPU spend or user-visible candidate output.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline shadow comparison over retrieval gold prompts.")
    parser.add_argument("--gold", type=Path, default=Path("data/eval/retrieval_gold.jsonl"))
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--output-dir", type=Path, default=Path("data/eval/shadow"))
    args = parser.parse_args()
    json_path, md_path = run_shadow_eval(args.gold, limit=args.limit, output_dir=args.output_dir)
    print(f"Wrote shadow eval reports to {json_path} and {md_path}")


if __name__ == "__main__":
    main()
