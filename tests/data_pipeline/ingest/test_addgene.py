from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any, Iterable

import pytest

from packages.core.schemas import Plasmid
from packages.data_pipeline.ingest.addgene import (
    AddgeneIngestionConfig,
    AddgeneMappingError,
    IngestionResult,
    map_addgene_raw_to_plasmid,
    raw_cache_key,
    run_addgene_ingestion,
)


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "addgene"


def load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeAddgeneClient:
    def __init__(self, payloads: dict[int, dict[str, Any]]) -> None:
        self.payloads = payloads
        self.fetches: list[int] = []

    def iter_plasmid_ids(self, *, limit: int | None = None) -> Iterable[int]:
        ids = list(self.payloads)
        for plasmid_id in ids[:limit]:
            yield plasmid_id

    def fetch_plasmid_with_sequences(self, plasmid_id: int) -> dict[str, Any]:
        self.fetches.append(plasmid_id)
        return self.payloads[plasmid_id]


class FakeObjectStore:
    def __init__(self, blobs: dict[str, dict[str, Any]] | None = None, fresh: bool = True) -> None:
        self.blobs = blobs or {}
        self.fresh = fresh
        self.puts: list[str] = []

    def exists(self, key: str) -> bool:
        return key in self.blobs

    def is_fresh(self, key: str, max_age: timedelta) -> bool:
        return key in self.blobs and self.fresh

    def put_json(self, key: str, payload: dict[str, Any]) -> None:
        self.blobs[key] = payload
        self.puts.append(key)

    def get_json(self, key: str) -> dict[str, Any]:
        return self.blobs[key]


class FakeRepository:
    def __init__(self) -> None:
        self.plasmids: dict[str, Plasmid] = {}
        self.finished: IngestionResult | None = None
        self.schema_ensured = False

    def ensure_schema(self) -> None:
        self.schema_ensured = True

    def start_run(self, *, source: str, mode: str, started_at) -> int:  # type: ignore[no-untyped-def]
        assert source == "addgene"
        assert mode in {"dev", "bulk", "refresh"}
        return 1

    def finish_run(
        self,
        run_id: int,
        *,
        finished_at,
        records_seen: int,
        records_upserted: int,
        errors: list[dict[str, Any]],
    ) -> None:
        self.finished = IngestionResult(run_id, records_seen, records_upserted, errors)

    def upsert_plasmid(self, plasmid: Plasmid) -> None:
        self.plasmids[plasmid.id] = plasmid


def test_map_minimal_metadata_fixture_to_plasmid() -> None:
    plasmid = map_addgene_raw_to_plasmid(load_fixture("minimal_metadata.json"), raw_ref="raw/addgene/1001.json")

    assert plasmid.id == "addgene:1001"
    assert plasmid.name == "Minimal GFP reporter"
    assert plasmid.sequence == "ATGCGTACGTAGCTAA"
    assert plasmid.markers == ["Ampicillin"]
    assert plasmid.promoters == []
    assert plasmid.annotation_complete is False


def test_map_multiple_markers_promoters_and_use_cases() -> None:
    plasmid = map_addgene_raw_to_plasmid(
        load_fixture("multiple_markers_promoters.json"),
        raw_ref="raw/addgene/1003.json",
    )

    assert plasmid.organism == "Homo sapiens"
    assert plasmid.vector_type == "Lentiviral"
    assert plasmid.markers == ["Ampicillin", "Puromycin"]
    assert plasmid.promoters == ["CMV", "TRE3G"]
    assert plasmid.publication_doi == "10.1000/multi"
    assert "Expression" in plasmid.use_cases


def test_map_unusual_organism_partial_sequence() -> None:
    plasmid = map_addgene_raw_to_plasmid(load_fixture("unusual_organism.json"), raw_ref="raw/addgene/1004.json")

    assert plasmid.organism == "Chlamydomonas reinhardtii"
    assert plasmid.vector_type == "shRNA"
    assert plasmid.promoters == ["U6"]
    assert plasmid.length == 24


def test_map_missing_sequence_raises_structured_error() -> None:
    with pytest.raises(AddgeneMappingError, match="missing a sequence"):
        map_addgene_raw_to_plasmid(load_fixture("missing_sequence.json"), raw_ref="raw/addgene/1002.json")


def test_ingestion_uses_fresh_cache_before_network_and_upserts_idempotently() -> None:
    raw = load_fixture("minimal_metadata.json")
    key = raw_cache_key(1001)
    client = FakeAddgeneClient({1001: raw})
    store = FakeObjectStore({key: raw}, fresh=True)
    repository = FakeRepository()
    config = AddgeneIngestionConfig(mode="dev", limit=1)

    first = run_addgene_ingestion(config, client=client, object_store=store, repository=repository)
    second = run_addgene_ingestion(config, client=client, object_store=store, repository=repository)

    assert client.fetches == []
    assert store.puts == []
    assert first.records_upserted == 1
    assert second.records_upserted == 1
    assert list(repository.plasmids) == ["addgene:1001"]
    assert repository.finished is not None
    assert repository.finished.errors == []


def test_ingestion_fetches_stale_or_missing_cache_before_parsing() -> None:
    raw = load_fixture("minimal_metadata.json")
    key = raw_cache_key(1001)
    client = FakeAddgeneClient({1001: raw})
    store = FakeObjectStore(fresh=False)
    repository = FakeRepository()
    config = AddgeneIngestionConfig(mode="refresh", limit=1)

    result = run_addgene_ingestion(config, client=client, object_store=store, repository=repository)

    assert client.fetches == [1001]
    assert store.puts == [key]
    assert result.records_seen == 1
    assert result.records_upserted == 1
    assert repository.plasmids["addgene:1001"].raw_ref == key


def test_ingestion_logs_mapping_errors_in_run_record() -> None:
    raw = load_fixture("missing_sequence.json")
    client = FakeAddgeneClient({1002: raw})
    store = FakeObjectStore(fresh=False)
    repository = FakeRepository()
    config = AddgeneIngestionConfig(mode="dev", limit=1)

    result = run_addgene_ingestion(config, client=client, object_store=store, repository=repository)

    assert result.records_seen == 1
    assert result.records_upserted == 0
    assert result.errors[0]["code"] == "mapping_error"
    assert result.errors[0]["plasmid_id"] == "1002"
    assert repository.finished is not None
    assert repository.finished.errors == result.errors
