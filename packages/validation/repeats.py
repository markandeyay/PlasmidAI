from __future__ import annotations

from dataclasses import dataclass

from packages.core.schemas import AnnotatedSequence, DesignSpec, ValidationCheck
from packages.validation.common import fail_check, gc_fraction, pass_check, region, reverse_complement, warn_check


CHECK_NAME = "repeat_and_instability"


@dataclass(frozen=True)
class RepeatHit:
    start: int
    end: int
    other_start: int
    kind: str


def run_repeat_instability_check(sequence: AnnotatedSequence, spec: DesignSpec) -> ValidationCheck:
    del spec
    dna = sequence.sequence
    homopolymer = first_homopolymer(dna, fail_threshold=12)
    if homopolymer is not None:
        start, end = homopolymer
        return fail_check(
            CHECK_NAME,
            "Homopolymer run of 12 or more bases may fail synthesis or sequencing.",
            region(start, end, len(dna)),
        )

    gc_failure = first_gc_extreme(dna, window=100, low=0.20, high=0.80)
    if gc_failure is not None:
        start, end, fraction = gc_failure
        return fail_check(
            CHECK_NAME,
            f"100 bp window has extreme GC content ({fraction:.0%}); redesign this region for synthesis.",
            region(start, end, len(dna)),
        )

    repeat = first_exact_repeat(dna, k=40)
    if repeat is not None:
        return fail_check(
            CHECK_NAME,
            f"{repeat.kind} repeat of at least 40 bp may promote recombination or synthesis instability.",
            region(repeat.start, repeat.end, len(dna)),
        )

    warn_repeat = first_exact_repeat(dna, k=25)
    if warn_repeat is not None:
        return warn_check(
            CHECK_NAME,
            f"{warn_repeat.kind} repeat of at least 25 bp is below the blocking threshold but should be reviewed.",
            region(warn_repeat.start, warn_repeat.end, len(dna)),
        )

    warn_homopolymer = first_homopolymer(dna, fail_threshold=8)
    if warn_homopolymer is not None:
        start, end = warn_homopolymer
        return warn_check(CHECK_NAME, "Homopolymer run of 8 or more bases should be reviewed.", region(start, end, len(dna)))

    return pass_check(CHECK_NAME, "No blocking repeat, homopolymer, or GC-instability pattern detected.")


def first_homopolymer(sequence: str, *, fail_threshold: int) -> tuple[int, int] | None:
    run_start = 0
    for index in range(1, len(sequence) + 1):
        if index < len(sequence) and sequence[index] == sequence[run_start]:
            continue
        if index - run_start >= fail_threshold:
            return run_start, index
        run_start = index
    return None


def first_gc_extreme(sequence: str, *, window: int, low: float, high: float) -> tuple[int, int, float] | None:
    if len(sequence) < window:
        fraction = gc_fraction(sequence)
        if fraction < low or fraction > high:
            return 0, len(sequence), fraction
        return None
    for start in range(0, len(sequence) - window + 1, max(1, window // 5)):
        segment = sequence[start : start + window]
        fraction = gc_fraction(segment)
        if fraction < low or fraction > high:
            return start, start + window, fraction
    return None


def first_exact_repeat(sequence: str, *, k: int) -> RepeatHit | None:
    seen: dict[str, int] = {}
    for start in range(0, len(sequence) - k + 1):
        kmer = sequence[start : start + k]
        previous = seen.get(kmer)
        if previous is not None and start - previous >= k:
            return RepeatHit(start=start, end=start + k, other_start=previous, kind="direct")
        seen.setdefault(kmer, start)

    rc_seen: dict[str, int] = {}
    for start in range(0, len(sequence) - k + 1):
        kmer = sequence[start : start + k]
        rc = reverse_complement(kmer)
        previous = rc_seen.get(rc)
        if previous is not None and abs(start - previous) >= k:
            return RepeatHit(start=start, end=start + k, other_start=previous, kind="inverted")
        rc_seen.setdefault(kmer, start)
    return None
