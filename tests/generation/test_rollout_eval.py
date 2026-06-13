from __future__ import annotations

import json
from pathlib import Path

from packages.generation.rollout_eval import run_shadow_eval


def test_shadow_eval_writes_json_and_markdown_reports(tmp_path: Path) -> None:
    gold = tmp_path / "gold.jsonl"
    gold.write_text(
        "\n".join(
            [
                json.dumps({"query": "Need a cloning plasmid", "acceptable_target_ids": ["pUC19"]}),
                json.dumps({"query": "Need a reporter plasmid", "acceptable_target_ids": ["pEGFP-N1"]}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    json_path, md_path = run_shadow_eval(gold, limit=2, output_dir=tmp_path)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["records"] == 2
    assert payload["summary"]["candidate_errors"] == 0
    assert payload["summary"]["output_divergence_rate"] == 1.0
    assert payload["summary"]["comparison_labels"] == {"candidate_diverged": 2}
    assert "Shadow Evaluation Baseline" in md_path.read_text(encoding="utf-8")
