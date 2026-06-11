from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from packages.core.schemas import Plasmid
from packages.data_pipeline.ingest.genbank import map_genbank_text_to_plasmid
from packages.data_pipeline.refresh_corpus import CorpusRefreshConfig, accession_from_plasmid, run_corpus_refresh


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "genbank"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeClient:
    def __init__(self, records: dict[str, str]) -> None:
        self.records = records
        self.fetches: list[str] = []

    def fetch_genbank(self, accession: str) -> str:
        self.fetches.append(accession)
        return self.records[accession]


class FakeStore:
    def __init__(self, blobs: dict[str, str]) -> None:
        self.blobs = blobs
        self.puts: list[str] = []

    def get_text(self, key: str) -> str:
        return self.blobs[key]

    def put_text(self, key: str, payload: str) -> None:
        self.blobs[key] = payload
        self.puts.append(key)


class FakeDatabase:
    def __init__(self, records: list[Plasmid]) -> None:
        self.records = records
        self.upserts: list[Plasmid] = []

    def list_stale_genbank_records(self, config: CorpusRefreshConfig, *, stale_before: datetime) -> list[Plasmid]:
        stale = [record for record in self.records if record.updated_at < stale_before]
        return stale[: config.limit]

    def upsert_plasmid(self, plasmid: Plasmid) -> None:
        self.upserts.append(plasmid)


def plasmid(*, updated_at: datetime) -> Plasmid:
    mapped = map_genbank_text_to_plasmid(load_fixture("minimal.gb"), raw_ref="raw/genbank/MIN0001.1.gb")
    return mapped.model_copy(update={"created_at": updated_at, "updated_at": updated_at})


def test_refresh_skips_records_newer_than_staleness_threshold() -> None:
    now = datetime(2026, 6, 7, tzinfo=UTC)
    database = FakeDatabase([plasmid(updated_at=now - timedelta(days=1))])
    client = FakeClient({"MIN0001.1": load_fixture("minimal.gb")})

    report = run_corpus_refresh(
        CorpusRefreshConfig(stale_after=timedelta(days=60)),
        database=database,
        object_store=FakeStore({}),
        client=client,
        started_at=now,
    )

    assert report.records_examined == 0
    assert client.fetches == []
    assert database.upserts == []


def test_refresh_touches_unchanged_cached_record_without_reporting_change() -> None:
    now = datetime(2026, 6, 7, tzinfo=UTC)
    raw = load_fixture("minimal.gb")
    database = FakeDatabase([plasmid(updated_at=now - timedelta(days=90))])
    store = FakeStore({"raw/genbank/MIN0001.1.gb": raw})

    report = run_corpus_refresh(
        CorpusRefreshConfig(stale_after=timedelta(days=60)),
        database=database,
        object_store=store,
        client=FakeClient({"MIN0001.1": raw}),
        started_at=now,
    )

    assert report.records_refetched == 1
    assert report.records_unchanged == 1
    assert report.records_updated == 0
    assert report.changes == []
    assert store.puts == ["raw/genbank/MIN0001.1.gb"]
    assert database.upserts[0].updated_at > database.records[0].updated_at


def test_refresh_reports_meaningful_changes_and_keeps_existing_raw_ref() -> None:
    now = datetime(2026, 6, 7, tzinfo=UTC)
    cached = load_fixture("minimal.gb")
    fetched = cached.replace("Minimal plasmid complete sequence", "Minimal refreshed plasmid complete sequence")
    database = FakeDatabase([plasmid(updated_at=now - timedelta(days=90))])
    store = FakeStore({"raw/genbank/MIN0001.1.gb": cached})

    report = run_corpus_refresh(
        CorpusRefreshConfig(stale_after=timedelta(days=60)),
        database=database,
        object_store=store,
        client=FakeClient({"MIN0001.1": fetched}),
        started_at=now,
    )

    assert report.records_updated == 1
    assert report.records_skipped == 0
    assert report.changes[0]["id"] == "genbank:MIN0001.1"
    assert set(report.changes[0]["fields"]) == {"name", "use_cases"}
    assert database.upserts[0].raw_ref == "raw/genbank/MIN0001.1.gb"
    assert store.blobs["raw/genbank/MIN0001.1.gb"] == fetched


def test_refresh_error_does_not_delete_or_upsert_record() -> None:
    now = datetime(2026, 6, 7, tzinfo=UTC)
    database = FakeDatabase([plasmid(updated_at=now - timedelta(days=90))])

    report = run_corpus_refresh(
        CorpusRefreshConfig(stale_after=timedelta(days=60)),
        database=database,
        object_store=FakeStore({}),
        client=FakeClient({"MIN0001.1": load_fixture("minimal.gb")}),
        started_at=now,
    )

    assert report.records_skipped == 1
    assert report.errors[0]["code"] == "refresh_error"
    assert database.upserts == []


def test_accession_from_plasmid_uses_genbank_id() -> None:
    assert accession_from_plasmid(plasmid(updated_at=datetime(2026, 1, 1, tzinfo=UTC))) == "MIN0001.1"
