from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = ROOT / "data" / "eval" / "retrieval_gold.jsonl"
MANIFEST_PATH = ROOT / "packages" / "data_pipeline" / "ingest" / "curated_seed_manifest.yaml"


def _load_curated_ids() -> set[str]:
    ids: set[str] = set()
    in_records = False
    current_id = None
    for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == "records:":
            in_records = True
            continue
        if not in_records:
            continue
        if stripped.startswith("- id: "):
            current_id = stripped.split(": ", 1)[1].strip().strip('"')
            ids.add(current_id)
        elif stripped.startswith("id: ") and current_id is None:
            ids.add(stripped.split(": ", 1)[1].strip().strip('"'))
    return ids


def test_retrieval_gold_jsonl_structure_and_targets():
    curated_ids = _load_curated_ids()
    records = []
    for raw_line in GOLD_PATH.read_text(encoding="utf-8").splitlines():
        assert raw_line.strip(), "retrieval_gold.jsonl contains an empty line"
        record = json.loads(raw_line)
        records.append(record)
        assert set(record) >= {"query", "acceptable_target_ids", "rationale", "source"}
        assert isinstance(record["query"], str) and record["query"].strip()
        assert isinstance(record["rationale"], str) and record["rationale"].strip()
        assert isinstance(record["source"], str) and record["source"].strip()
        assert isinstance(record["acceptable_target_ids"], list)
        assert record["acceptable_target_ids"], "each query needs at least one target"
        for target_id in record["acceptable_target_ids"]:
            assert target_id in curated_ids, f"unknown curated target id: {target_id}"

    assert len(records) >= 5
