from __future__ import annotations

from packages.validation.repeats import run_repeat_instability_check
from tests.validation.helpers import annotated, spec, stable_dna


def test_homopolymer_failure() -> None:
    report = run_repeat_instability_check(annotated("ATGC" * 20 + "A" * 12 + "CGTA" * 20), spec())

    assert report.status == "FAIL"
    assert "Homopolymer" in report.message


def test_gc_extreme_failure() -> None:
    report = run_repeat_instability_check(annotated(stable_dna(80) + "GC" * 50 + stable_dna(80)), spec())

    assert report.status == "FAIL"
    assert "GC" in report.message


def test_direct_repeat_failure() -> None:
    repeat = "ATGCGTACGATCGTACGATCGTACGATCGTACGATCGTAA"
    spacer = "GATTACA" * 10
    report = run_repeat_instability_check(annotated(repeat + spacer + repeat), spec())

    assert report.status == "FAIL"
    assert "repeat" in report.message


def test_stable_sequence_passes() -> None:
    sequence = stable_dna(180)
    report = run_repeat_instability_check(annotated(sequence), spec())

    assert report.status == "PASS"
