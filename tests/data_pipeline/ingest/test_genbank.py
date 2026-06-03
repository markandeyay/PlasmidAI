from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Iterable

from packages.core.schemas import Plasmid
from packages.data_pipeline.ingest.genbank import (
    EXPANSION_QUERY,
    GenbankMappingError,
    GenbankIngestionConfig,
    IngestionResult,
    REFSEQ_PLASMID_BROAD_QUERY,
    build_parser,
    fetch_rettype_for_mode,
    genbank_query_for_mode,
    map_genbank_text_to_plasmid,
    raw_cache_key,
    run_genbank_ingestion,
    should_fetch_cache,
)


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "genbank"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeNCBIClient:
    def __init__(self, records: dict[str, str]) -> None:
        self.records = records
        self.fetches: list[str] = []

    def iter_accessions(self, *, limit: int | None = None) -> Iterable[str]:
        accessions = list(self.records)
        for accession in accessions[:limit]:
            yield accession

    def fetch_genbank(self, accession: str) -> str:
        self.fetches.append(accession)
        return self.records[accession]


class FakeObjectStore:
    def __init__(self, blobs: dict[str, str] | None = None, fresh: bool = True) -> None:
        self.blobs = blobs or {}
        self.fresh = fresh
        self.puts: list[str] = []

    def exists(self, key: str) -> bool:
        return key in self.blobs

    def is_fresh(self, key: str, max_age: timedelta) -> bool:
        return key in self.blobs and self.fresh

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
        assert source == "genbank"
        assert mode in {"dev", "bulk", "refresh", "expansion", "refseq_plasmid_broad"}
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


def test_map_minimal_genbank_record() -> None:
    plasmid = map_genbank_text_to_plasmid(load_fixture("minimal.gb"), raw_ref="raw/genbank/MIN0001.1.gb")

    assert plasmid.id == "genbank:MIN0001.1"
    assert plasmid.source == "genbank"
    assert plasmid.organism == "synthetic DNA construct"
    assert plasmid.vector_type == "plasmid"
    assert plasmid.markers == []
    assert plasmid.promoters == []
    assert plasmid.annotation_complete is False


def test_map_rich_annotations_extracts_promoter_marker_and_doi() -> None:
    plasmid = map_genbank_text_to_plasmid(load_fixture("rich_annotations.gb"), raw_ref="raw/genbank/RICH0001.1.gb")

    assert plasmid.promoters == ["CMV promoter"]
    assert plasmid.markers == ["bla"]
    assert plasmid.publication_doi == "10.1000/rich"
    assert any("expression vector" in use_case.lower() for use_case in plasmid.use_cases)


def test_map_multiple_feature_types() -> None:
    plasmid = map_genbank_text_to_plasmid(load_fixture("multiple_features.gb"), raw_ref="raw/genbank/MULT0001.1.gb")

    assert plasmid.promoters == ["T7 promoter", "lac promoter"]
    assert plasmid.markers == ["neo", "cat marker"]
    assert plasmid.vector_type == "plasmid"


def test_map_unusual_organism() -> None:
    plasmid = map_genbank_text_to_plasmid(load_fixture("unusual_organism.gb"), raw_ref="raw/genbank/UNUS0001.1.gb")

    assert plasmid.organism == "Chlamydomonas reinhardtii"
    assert plasmid.promoters == ["HSP70A-RBCS2 promoter"]


def test_map_very_short_and_long_fixtures() -> None:
    short = map_genbank_text_to_plasmid(load_fixture("very_short.gb"), raw_ref="raw/genbank/SHRT0001.1.gb")
    long = map_genbank_text_to_plasmid(load_fixture("very_long.gb"), raw_ref="raw/genbank/LONG0001.1.gb")

    assert short.length == 8
    assert long.length == 200
    assert long.promoters == ["EF1a promoter"]
    assert long.markers == ["puro"]


def test_map_con_record_without_origin_raises_structured_error() -> None:
    try:
        map_genbank_text_to_plasmid(load_fixture("con_no_origin.gb"), raw_ref="raw/genbank/NZ_CP191780.1.gb")
    except GenbankMappingError as exc:
        assert "no ORIGIN" in str(exc)
    else:
        raise AssertionError("CON record without concrete sequence should not map to Plasmid")


def test_map_record_with_ambiguous_bases_raises_structured_error() -> None:
    raw = load_fixture("minimal.gb").replace("atgcgt", "ntgcgt", 1)

    try:
        map_genbank_text_to_plasmid(raw, raw_ref="raw/genbank/MIN0001.1.gb")
    except GenbankMappingError as exc:
        assert "ambiguous bases" in str(exc)
        assert exc.details == {"invalid_characters": "N"}
    else:
        raise AssertionError("ambiguous GenBank sequence should not reach Plasmid validation")


def test_ingestion_uses_fresh_cache_before_network_and_upserts_idempotently() -> None:
    raw = load_fixture("minimal.gb")
    key = raw_cache_key("MIN0001.1")
    client = FakeNCBIClient({"MIN0001.1": raw})
    store = FakeObjectStore({key: raw}, fresh=True)
    repository = FakeRepository()
    config = GenbankIngestionConfig(mode="dev", limit=1)

    first = run_genbank_ingestion(config, client=client, object_store=store, repository=repository)
    second = run_genbank_ingestion(config, client=client, object_store=store, repository=repository)

    assert client.fetches == []
    assert store.puts == []
    assert first.records_upserted == 1
    assert second.records_upserted == 1
    assert list(repository.plasmids) == ["genbank:MIN0001.1"]
    assert repository.finished is not None
    assert repository.finished.errors == []


def test_ingestion_fetches_stale_or_missing_cache_before_parsing() -> None:
    raw = load_fixture("minimal.gb")
    key = raw_cache_key("MIN0001.1")
    client = FakeNCBIClient({"MIN0001.1": raw})
    store = FakeObjectStore(fresh=False)
    repository = FakeRepository()
    config = GenbankIngestionConfig(mode="refresh", limit=1)

    result = run_genbank_ingestion(config, client=client, object_store=store, repository=repository)

    assert client.fetches == ["MIN0001.1"]
    assert store.puts == [key]
    assert result.records_seen == 1
    assert result.records_upserted == 1
    assert repository.plasmids["genbank:MIN0001.1"].raw_ref == key


def test_expansion_mode_uses_component_gated_query() -> None:
    query = genbank_query_for_mode("expansion", {})

    assert query == EXPANSION_QUERY
    assert '"expression vector"[Title]' in query
    assert "srcdb_genbank[PROP]" in query
    assert "chromosome[Title]" in query


def test_expansion_mode_uses_bulk_cache_policy() -> None:
    key = raw_cache_key("MIN0001.1")
    config = GenbankIngestionConfig(mode="expansion", limit=1)

    assert should_fetch_cache(config, FakeObjectStore({key: "cached"}, fresh=False), key) is False
    assert should_fetch_cache(config, FakeObjectStore({}, fresh=True), key) is True


def test_refseq_plasmid_broad_mode_uses_complete_refseq_plasmid_query() -> None:
    query = genbank_query_for_mode("refseq_plasmid_broad", {})

    assert query == REFSEQ_PLASMID_BROAD_QUERY
    assert "plasmid[Title]" in query
    assert "srcdb_refseq[PROP]" in query
    assert '"complete sequence"[Title]' in query
    assert '"complete genome"[Title]' in query
    assert "1000:50000[SLEN]" in query
    assert "chromosome[Title]" in query
    assert "scaffold[Title]" in query
    assert "contig[Title]" in query


def test_refseq_plasmid_broad_mode_uses_bulk_cache_policy() -> None:
    key = raw_cache_key("MIN0001.1", mode="refseq_plasmid_broad")
    config = GenbankIngestionConfig(mode="refseq_plasmid_broad", limit=1)

    assert should_fetch_cache(config, FakeObjectStore({key: "cached"}, fresh=False), key) is False
    assert should_fetch_cache(config, FakeObjectStore({}, fresh=True), key) is True
    assert key == "raw/genbank/refseq_plasmid_broad/MIN0001.1.gb"


def test_refseq_plasmid_broad_mode_fetches_genbank_with_parts() -> None:
    config = GenbankIngestionConfig.from_env(mode="refseq_plasmid_broad", limit=1, stale_days=60)

    assert fetch_rettype_for_mode("refseq_plasmid_broad") == "gbwithparts"
    assert fetch_rettype_for_mode("expansion") == "gb"
    assert config.fetch_rettype == "gbwithparts"


def test_refseq_plasmid_broad_mode_is_accepted_by_config_and_cli_parser() -> None:
    config = GenbankIngestionConfig(mode="refseq_plasmid_broad", email="research@example.org")
    parsed = build_parser().parse_args(["--mode", "refseq_plasmid_broad", "--limit", "50"])

    config.validate_for_real_network()
    assert parsed.mode == "refseq_plasmid_broad"
    assert parsed.limit == 50
