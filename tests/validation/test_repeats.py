from __future__ import annotations

from packages.validation.common import reverse_complement
from packages.validation.repeats import first_exact_repeat, run_repeat_instability_check
from tests.validation.helpers import annotated, spec, stable_dna


def seeded_dna(length: int, seed: int) -> str:
    bases = "ACGT"
    out: list[str] = []
    while len(out) < length:
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        candidate = bases[(seed >> 8) % 4]
        if len(out) >= 3 and out[-1] == out[-2] == out[-3] == candidate:
            candidate = bases[(bases.index(candidate) + 1) % 4]
        out.append(candidate)
    return "".join(out)


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


def test_inverted_repeat_failure() -> None:
    repeat = seeded_dna(45, 17)
    spacer = seeded_dna(80, 91)
    report = run_repeat_instability_check(annotated(repeat + spacer + reverse_complement(repeat)), spec())

    assert report.status == "FAIL"
    assert "inverted repeat" in report.message


def test_ambiguous_base_repeat_is_detected() -> None:
    repeat = "ACGTN" * 8
    spacer = stable_dna(80)
    hit = first_exact_repeat(repeat + spacer + repeat, k=40)

    assert hit is not None
    assert hit.kind == "direct"


def test_stable_sequence_passes() -> None:
    sequence = stable_dna(180)
    report = run_repeat_instability_check(annotated(sequence), spec())

    assert report.status == "PASS"
