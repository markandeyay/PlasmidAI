from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from packages.core.schemas import Plasmid
from packages.data_pipeline.quality_report import build_quality_report, render_markdown, write_report_files


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "parser"
PUC19 = (FIXTURES / "puc19.gb").read_text(encoding="utf-8")
PUC19_SEQUENCE = "".join(
    character
    for line in PUC19.split("ORIGIN", 1)[1].split("//", 1)[0].splitlines()
    for character in line.upper()
    if character in "ACGT"
)


class FakeRepository:
    def __init__(self, plasmids: list[Plasmid]) -> None:
        self.plasmids = plasmids

    def list_plasmids(self) -> list[Plasmid]:
        return self.plasmids


class FakeObjectStore:
    def __init__(self, blobs: dict[str, str]) -> None:
        self.blobs = blobs

    def get_text(self, key: str) -> str:
        return self.blobs[key]


def plasmid(plasmid_id: str, raw_ref: str, *, sequence: str = PUC19_SEQUENCE) -> Plasmid:
    return Plasmid(
        id=plasmid_id,
        source="genbank",
        name=plasmid_id,
        sequence=sequence,
        length=len(sequence),
        organism="Escherichia coli",
        vector_type="plasmid",
        markers=["bla"],
        promoters=[],
        publication_doi=None,
        use_cases=[],
        annotation_complete=False,
        raw_ref=raw_ref,
    )


def test_quality_report_aggregates_profiles_nulls_and_exact_duplicates() -> None:
    repository = FakeRepository(
        [
            plasmid("curated:pUC19", "raw/curated/pUC19.gb"),
            plasmid("genbank:L09137.2", "raw/genbank/L09137.2.gb"),
            plasmid("genbank:broken", "raw/genbank/broken.gb", sequence="ACGT"),
        ]
    )
    store = FakeObjectStore(
        {
            "raw/curated/pUC19.gb": PUC19,
            "raw/genbank/L09137.2.gb": PUC19,
            "raw/genbank/broken.gb": "not a GenBank record",
        }
    )

    report = build_quality_report(repository, store, generated_at=datetime(2026, 5, 30, tzinfo=UTC))

    assert report["records_per_source"] == {"genbank": 2, "curated": 1}
    assert report["profiles"]["breakdown"] == {"bacterial_cloning_vector": 2, "unknown": 1}
    assert report["annotation_complete"]["count"] == 2
    assert report["annotation_complete"]["by_profile"]["bacterial_cloning_vector"]["rate"] == 1.0
    assert report["annotation_complete"]["by_profile"]["unknown"]["rate"] == 0.0
    assert report["null_rates"]["publication_doi"]["rate"] == 1.0
    assert report["duplicate_cluster_count"] == 1
    assert report["duplicate_clusters"][0]["record_ids"] == ["curated:pUC19", "genbank:L09137.2"]
    assert report["parse_errors"][0]["id"] == "genbank:broken"


def test_write_report_files_emits_json_and_readable_markdown(tmp_path: Path) -> None:
    report = build_quality_report(
        FakeRepository([plasmid("curated:pUC19", "raw/curated/pUC19.gb")]),
        FakeObjectStore({"raw/curated/pUC19.gb": PUC19}),
        generated_at=datetime(2026, 5, 30, 12, 34, 56, tzinfo=UTC),
    )

    json_path, markdown_path = write_report_files(report, tmp_path)
    markdown = markdown_path.read_text(encoding="utf-8")

    assert json_path.name == "2026-05-30-123456-quality-report.json"
    assert markdown_path.name == "2026-05-30-123456-quality-report.md"
    assert "# Plasmid Data Quality Report" in markdown
    assert "| bacterial_cloning_vector | 1 | 1 | 100.0% |" in markdown
    assert render_markdown(report) == markdown
