from __future__ import annotations

from packages.validation.eval import evaluate_gold
from packages.validation.gold import write_gold_set


def test_validation_gold_set_meets_gate(tmp_path) -> None:
    gold_path = tmp_path / "gold.jsonl"
    doc_path = tmp_path / "construction.md"
    write_gold_set(gold_path, doc_path)

    report = evaluate_gold(gold_path)

    assert report["total"] == 100
    assert report["accuracy"] >= 0.95
    assert report["phase3_gate_met"] is True
    assert doc_path.exists()
