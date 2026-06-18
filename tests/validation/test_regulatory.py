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
    assert report.failure_context == "design_construct_failure"


def test_missing_origin_on_source_record_is_labeled_uncertainty() -> None:
    seq = annotated(BASE, [feature("marker", 60, 120, "AmpR")])

    report = run_regulatory_check(seq, spec(source="genbank"))

    assert report.status == "FAIL"
    assert "No origin" in report.message
    assert report.failure_context == "source_record_uncertainty"


def test_missing_origin_on_generated_design_is_labeled_construct_failure() -> None:
    seq = annotated(BASE, [feature("marker", 60, 120, "AmpR")])

    report = run_regulatory_check(seq, spec(source="generated"))

    assert report.status == "FAIL"
    assert "No origin" in report.message
    assert report.failure_context == "design_construct_failure"


def test_auxiliary_t7_promoter_outside_source_expression_cassette_passes_mammalian_context() -> None:
    seq = annotated(
        BASE,
        [
            feature("ORI", 0, 50, "pUC origin"),
            feature("marker", 60, 120, "AmpR"),
            feature("promoter", 130, 150, "T7 promoter"),
            feature("promoter", 220, 260, "SV40 promoter"),
        ],
        profile="mammalian_expression_vector",
    )

    report = run_regulatory_check(seq, spec(organism="human cells", source="genbank", vector_type="mammalian_expression_vector"))

    assert report.status == "PASS"


def test_auxiliary_t7_promoter_near_source_goi_warns_mammalian_context() -> None:
    seq = annotated(
        BASE,
        [
            feature("ORI", 0, 50, "pUC origin"),
            feature("marker", 60, 120, "AmpR"),
            feature("promoter", 130, 150, "T7 promoter"),
            feature("GOI", 180, 280, "payload candidate"),
        ],
        profile="mammalian_expression_vector",
    )

    report = run_regulatory_check(seq, spec(organism="human cells", source="genbank", vector_type="mammalian_expression_vector"))

    assert report.status == "WARN"
    assert "Auxiliary promoter" in report.message


def test_auxiliary_t7_promoter_fails_generated_mammalian_expression_design() -> None:
    seq = annotated(
        BASE,
        [
            feature("ORI", 0, 50, "pUC origin"),
            feature("marker", 60, 120, "AmpR"),
            feature("promoter", 130, 150, "T7 promoter"),
            feature("GOI", 180, 280, "payload candidate"),
        ],
        profile="mammalian_expression_vector",
    )

    report = run_regulatory_check(seq, spec(organism="human cells", source="generated", vector_type="mammalian_expression_vector"))

    assert report.status == "FAIL"
    assert "Auxiliary promoter" in report.message
