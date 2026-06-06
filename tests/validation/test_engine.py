from __future__ import annotations

from packages.validation.engine import ConstraintEngine
from tests.validation.helpers import annotated, feature, spec, stable_dna


def test_constraint_engine_aggregates_failures() -> None:
    seq = annotated("ATGC" * 30 + "A" * 12 + "CGTA" * 30, [feature("ORI", 0, 20, "pUC origin")])

    report = ConstraintEngine().validate(seq, spec(cloning_method="Gibson assembly"))

    assert report.overall == "FAIL"
    assert {check.name for check in report.checks} == {
        "restriction_site_conflicts",
        "repeat_and_instability",
        "codon_usage",
        "regulatory_compatibility",
    }


def test_constraint_engine_passes_clean_construct() -> None:
    sequence = stable_dna(420)
    seq = annotated(
        sequence,
        [
            feature("ORI", 0, 50, "pUC origin"),
            feature("marker", 60, 120, "AmpR"),
            feature("MCS", 130, 170, "multiple cloning site"),
        ],
        profile="bacterial_cloning_vector",
    )

    report = ConstraintEngine().validate(seq, spec(cloning_method="Gibson assembly"))

    assert report.overall == "PASS"
