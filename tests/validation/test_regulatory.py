from __future__ import annotations

from packages.validation.regulatory import run_regulatory_check
from tests.validation.helpers import annotated, feature, spec


BASE = "ATGC" * 200


def test_regulatory_passes_compatible_bacterial_construct() -> None:
    seq = annotated(
        BASE,
        [
            feature("ORI", 0, 50, "pUC origin"),
            feature("marker", 60, 120, "AmpR"),
            feature("promoter", 130, 150, "lac promoter"),
            feature("GOI", 160, 260, "protein"),
            feature("terminator", 270, 300, "T7 terminator"),
        ],
    )

    report = run_regulatory_check(seq, spec())

    assert report.status == "PASS"


def test_regulatory_fails_mammalian_promoter_in_bacterial_context() -> None:
    seq = annotated(
        BASE,
        [
            feature("ORI", 0, 50, "pUC origin"),
            feature("marker", 60, 120, "AmpR"),
            feature("promoter", 130, 180, "CMV promoter"),
        ],
    )

    report = run_regulatory_check(seq, spec())

    assert report.status == "FAIL"
    assert "Promoter" in report.message


def test_regulatory_fails_missing_marker() -> None:
    seq = annotated(BASE, [feature("ORI", 0, 50, "pUC origin")])

    report = run_regulatory_check(seq, spec())

    assert report.status == "FAIL"
    assert "selectable marker" in report.message
