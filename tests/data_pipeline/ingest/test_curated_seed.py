from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from packages.core.schemas import Plasmid
from packages.data_pipeline.ingest.curated_seed import (
    CuratedSeedConfig,
    IngestionResult,
    load_manifest,
    raw_cache_key,
    run_curated_seed_ingestion,
)


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "genbank"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeCuratedClient:
    def __init__(self, records: dict[str, str]) -> None:
        self.records = records
        self.fetches: list[str] = []

    def fetch_genbank(self, accession: str) -> str:
        self.fetches.append(accession)
        return self.records[accession]


class FakeObjectStore:
    def __init__(self, blobs: dict[str, str] | None = None) -> None:
        self.blobs = blobs or {}
        self.puts: list[str] = []

    def exists(self, key: str) -> bool:
        return key in self.blobs

    def is_fresh(self, key: str, max_age: timedelta) -> bool:
        return key in self.blobs

    def put_text(self, key: str, payload: str) -> None:
        self.blobs[key] = payload
        self.puts.append(key)

    def get_text(self, key: str) -> str:
        return self.blobs[key]


class FakeRepository:
    def __init__(self) -> None:
        self.plasmids: dict[str, Plasmid] = {}
        self.finished: IngestionResult | None = None
        self.schema_ensured = False

    def ensure_schema(self) -> None:
        self.schema_ensured = True

    def start_run(self, *, source: str, mode: str, started_at) -> int:  # type: ignore[no-untyped-def]
        assert source == "curated"
        assert mode == "seed"
        return 1

    def finish_run(
        self,
        run_id: int,
        *,
        finished_at,
        records_seen: int,
        records_upserted: int,
        errors: list[dict[str, str]],
    ) -> None:
        self.finished = IngestionResult(run_id, records_seen, records_upserted, errors)

    def upsert_plasmid(self, plasmid: Plasmid) -> None:
        self.plasmids[plasmid.id] = plasmid


def write_manifest(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "id": "minimal-seed",
                        "name": "Minimal Seed",
                        "category": "test_seed",
                        "source": "ncbi",
                        "accession": "MIN0001.1",
                        "expected_length_bp": 120,
                        "expected_topology": "circular",
                        "curation_notes": "fixture record",
                        "citations": ["https://www.ncbi.nlm.nih.gov/nuccore/MIN0001.1"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def test_manifest_loads_json_compatible_yaml(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    write_manifest(manifest)

    records = load_manifest(manifest)

    assert len(records) == 1
    assert records[0].id == "minimal-seed"
    assert records[0].accession == "MIN0001.1"


def test_curated_seed_ingestion_is_cache_first_and_idempotent(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    write_manifest(manifest)
    raw = load_fixture("minimal.gb")
    config = CuratedSeedConfig(manifest_path=manifest)
    client = FakeCuratedClient({"MIN0001.1": raw})
    store = FakeObjectStore()
    repository = FakeRepository()

    first = run_curated_seed_ingestion(config, client=client, object_store=store, repository=repository)
    second = run_curated_seed_ingestion(config, client=client, object_store=store, repository=repository)

    assert first.records_upserted == 1
    assert second.records_upserted == 1
    assert client.fetches == ["MIN0001.1"]
    assert store.puts == [raw_cache_key(load_manifest(manifest)[0])]
    assert list(repository.plasmids) == ["curated:minimal-seed"]
    assert repository.plasmids["curated:minimal-seed"].source == "curated"
    assert repository.plasmids["curated:minimal-seed"].raw_ref == "raw/curated/minimal-seed.gb"
    assert repository.finished is not None
    assert repository.finished.errors == []
