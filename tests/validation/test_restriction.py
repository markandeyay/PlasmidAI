from __future__ import annotations

from packages.validation.restriction import run_restriction_site_check
from tests.validation.helpers import annotated, feature, spec


def test_restriction_conflict_fails_for_internal_site_outside_mcs() -> None:
    sequence = "A" * 30 + "GAATTC" + "C" * 30 + "GGATCC" + "T" * 30
    report = run_restriction_site_check(
        annotated(sequence, [feature("MCS", 64, 70, "MCS")]),
        spec(cloning_method="EcoRI and BamHI cloning"),
    )

    assert report.status == "FAIL"
    assert report.region is not None
    assert report.region.start < 40


def test_restriction_sites_only_in_mcs_pass() -> None:
    sequence = "A" * 30 + "GAATTCGGATCC" + "C" * 30
    report = run_restriction_site_check(
        annotated(sequence, [feature("MCS", 30, 42, "MCS")]),
        spec(cloning_method="EcoRI/BamHI cloning"),
    )

    assert report.status == "PASS"


def test_restriction_check_passes_without_relevant_enzyme_context() -> None:
    report = run_restriction_site_check(annotated("ATGC" * 20), spec(cloning_method="Gibson assembly"))

    assert report.status == "PASS"
