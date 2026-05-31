from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = ROOT / "data" / "eval" / "retrieval_gold.jsonl"
MANIFEST_PATH = ROOT / "packages" / "data_pipeline" / "ingest" / "curated_seed_manifest.yaml"


def _load_curated_ids() -> set[str]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {record["id"] for record in manifest["records"]}


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
        expected_clarification = record.get("expected_clarification", False)
        assert isinstance(expected_clarification, bool)
        if expected_clarification:
            assert not record["acceptable_target_ids"], "clarification-only queries must not claim a retrieval target"
            continue
        assert record["acceptable_target_ids"], "retrieval queries need at least one target"
        for target_id in record["acceptable_target_ids"]:
            assert target_id in curated_ids or _looks_like_genbank_accession(target_id), f"unrecognized target id: {target_id}"

    assert len(records) >= 5


def _looks_like_genbank_accession(target_id: str) -> bool:
    accession = target_id.split(":", 1)[-1]
    return re.fullmatch(r"[A-Z]{1,4}\d{5,}(?:\.\d+)?", accession) is not None
