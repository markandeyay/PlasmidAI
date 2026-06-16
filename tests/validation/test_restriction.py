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


def test_golden_gate_bsa_i_goi_internal_site_fails() -> None:
    sequence = "A" * 20 + "GGTCTC" + "C" * 20 + "GAATTC" + "T" * 20
    report = run_restriction_site_check(
        annotated(sequence, [feature("GOI", 20, 46, "insert"), feature("MCS", 52, 58, "MCS")]),
        spec(cloning_method="Golden Gate with BsaI"),
    )

    assert report.status == "FAIL"
    assert "BsaI" in report.message
    assert "GOI" in report.message


def test_gibson_incidental_enzyme_mention_passes() -> None:
    sequence = "A" * 20 + "GAATTC" + "C" * 20
    report = run_restriction_site_check(
        annotated(sequence, [feature("GOI", 20, 46, "insert")]),
        spec(cloning_method="Gibson assembly with EcoRI scar in the insert"),
    )

    assert report.status == "PASS"


def test_avoid_acc65_i_catches_kpn_i_family_recognition_site() -> None:
    sequence = "A" * 20 + "GGTACC" + "C" * 20
    report = run_restriction_site_check(
        annotated(sequence, [feature("GOI", 20, 46, "insert")]),
        spec(cloning_method="Gibson assembly", constraints=["avoid Acc65I sites in the insert"]),
    )

    assert report.status == "FAIL"
    assert "Acc65I" in report.message
    assert "KpnI" in report.message
    assert "recognition-site family" in report.message


def test_restriction_failure_message_identifies_goi_context() -> None:
    sequence = "A" * 20 + "GAATTC" + "C" * 20 + "GGATCC" + "T" * 20
    report = run_restriction_site_check(
        annotated(sequence, [feature("GOI", 20, 46, "insert"), feature("MCS", 52, 58, "MCS")]),
        spec(cloning_method="EcoRI and BamHI cloning"),
    )

    assert report.status == "FAIL"
    assert "GOI" in report.message
