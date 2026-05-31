from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from packages.core.schemas import Plasmid
from packages.data_pipeline.ingest.genbank import map_genbank_text_to_plasmid
from packages.data_pipeline.parse.sequence_parser import parse_genbank_text
from packages.data_pipeline.reprocess import (
    MissingCacheError,
    ReprocessConfig,
    ReprocessReport,
    run_reprocessing,
)


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "parser"
PUC19 = (FIXTURES / "puc19.gb").read_text(encoding="utf-8")


class FakeObjectStore:
    def __init__(self, blobs: dict[str, str]) -> None:
        self.blobs = blobs

    def get_text(self, key: str) -> str:
        try:
            return self.blobs[key]
        except KeyError as exc:
            raise MissingCacheError(f"cached blob is missing: {key}") from exc


class FakeDatabase:
    def __init__(self, plasmids: list[Plasmid], *, fail_updates: bool = False) -> None:
        self.plasmids = {plasmid.id: plasmid for plasmid in plasmids}
        self.fail_updates = fail_updates
        self.schema_ensured = False
        self.finished: tuple[int, ReprocessReport, str] | None = None
        self.batch_calls: list[list[str]] = []

    def ensure_schema(self) -> None:
        self.schema_ensured = True

    def start_run(self, config: ReprocessConfig, *, started_at: datetime) -> int:
        return 1

    def list_candidates(self, config: ReprocessConfig) -> list[Plasmid]:
        return list(self.plasmids.values())

    def update_batch(self, updates: list[Plasmid]) -> None:
        self.batch_calls.append([plasmid.id for plasmid in updates])
        if self.fail_updates:
            raise RuntimeError("simulated transaction rollback")
        for plasmid in updates:
            self.plasmids[plasmid.id] = plasmid

    def finish_run(self, run_id: int, report: ReprocessReport, *, finished_at: datetime, report_path: str) -> None:
        self.finished = (run_id, report, report_path)


def mapped_puc19(plasmid_id: str, raw_ref: str) -> Plasmid:
    mapped = map_genbank_text_to_plasmid(PUC19, raw_ref=raw_ref)
    annotated = parse_genbank_text(PUC19)
    return mapped.model_copy(
        update={
            "id": plasmid_id,
            "raw_ref": raw_ref,
            "annotation_complete": annotated.annotation_complete,
        }
    )


def stale_puc19(plasmid_id: str, raw_ref: str) -> Plasmid:
    return mapped_puc19(plasmid_id, raw_ref).model_copy(
        update={
            "markers": ["replication initiator protein A"],
            "annotation_complete": False,
        }
    )


def test_reprocess_updates_changed_metadata_and_second_run_is_noop() -> None:
    raw_ref = "raw/genbank/L09137.2.gb"
    database = FakeDatabase([stale_puc19("genbank:L09137.2", raw_ref)])
    store = FakeObjectStore({raw_ref: PUC19})

    first = run_reprocessing(ReprocessConfig(mode="all"), database=database, object_store=store)
    second = run_reprocessing(ReprocessConfig(mode="all"), database=database, object_store=store)

    assert first.records_updated == 1
    assert first.changes[0]["fields"]["markers"] == {
        "before": ["replication initiator protein A"],
        "after": ["bla"],
    }
    assert first.changes[0]["fields"]["annotation_complete"] == {"before": False, "after": True}
    assert second.records_updated == 0
    assert second.records_skipped == 1
    assert second.changes == []


def test_reprocess_skips_unchanged_record_without_writing() -> None:
    raw_ref = "raw/genbank/L09137.2.gb"
    database = FakeDatabase([mapped_puc19("genbank:L09137.2", raw_ref)])

    report = run_reprocessing(ReprocessConfig(mode="all"), database=database, object_store=FakeObjectStore({raw_ref: PUC19}))

    assert report.records_examined == 1
    assert report.records_updated == 0
    assert report.records_skipped == 1
    assert database.batch_calls == []


def test_reprocess_reports_missing_cache_without_deleting_record() -> None:
    raw_ref = "raw/genbank/L09137.2.gb"
    database = FakeDatabase([stale_puc19("genbank:L09137.2", raw_ref)])

    report = run_reprocessing(ReprocessConfig(mode="all"), database=database, object_store=FakeObjectStore({}))

    assert report.records_missing_cache == 1
    assert report.records_skipped == 1
    assert report.errors[0]["code"] == "missing_cache"
    assert "genbank:L09137.2" in database.plasmids


def test_reprocess_failed_batch_rolls_back_all_updates() -> None:
    first_ref = "raw/genbank/first.gb"
    second_ref = "raw/genbank/second.gb"
    database = FakeDatabase(
        [
            stale_puc19("genbank:first", first_ref),
            stale_puc19("genbank:second", second_ref),
        ],
        fail_updates=True,
    )
    store = FakeObjectStore({first_ref: PUC19, second_ref: PUC19})

    report = run_reprocessing(ReprocessConfig(mode="all", batch_size=2), database=database, object_store=store)

    assert report.records_updated == 0
    assert report.records_skipped == 2
    assert report.errors[0]["code"] == "batch_rollback"
    assert database.plasmids["genbank:first"].markers == ["replication initiator protein A"]
    assert database.plasmids["genbank:second"].markers == ["replication initiator protein A"]


@pytest.mark.parametrize(
    ("config", "message"),
    [
        (ReprocessConfig(mode="stale"), "requires --before"),
        (ReprocessConfig(mode="source"), "requires --source"),
        (ReprocessConfig(mode="filter"), "requires --pattern"),
        (ReprocessConfig(mode="all", batch_size=0), "must be positive"),
    ],
)
def test_reprocess_config_validates_required_mode_flags(config: ReprocessConfig, message: str) -> None:
    with pytest.raises(Exception, match=message):
        config.validate()


def test_reprocess_report_can_be_finished_by_adapter() -> None:
    database = FakeDatabase([])
    report = run_reprocessing(
        ReprocessConfig(mode="all"),
        database=database,
        object_store=FakeObjectStore({}),
        started_at=datetime(2026, 5, 30, tzinfo=UTC),
    )

    database.finish_run(report.run_id, report, finished_at=datetime(2026, 5, 30, 1, tzinfo=UTC), report_path="report.json")

    assert database.schema_ensured is True
    assert database.finished == (1, report, "report.json")
