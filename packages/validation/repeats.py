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


@dataclass(frozen=True)
class RepeatProfile:
    name: str
    direct_fail: int
    direct_warn: int
    homopolymer_fail: dict[str, int]
    homopolymer_warn: dict[str, int]
    idt_warn_repeats_only: bool = False


LEGACY_PROFILE = RepeatProfile(
    name="legacy_default",
    direct_fail=40,
    direct_warn=25,
    homopolymer_fail={base: 12 for base in "ACGT"},
    homopolymer_warn={base: 8 for base in "ACGT"},
)

PROVIDER_PROFILES = {
    "conservative_default": RepeatProfile(
        name="conservative_default",
        direct_fail=20,
        direct_warn=16,
        homopolymer_fail={"A": 10, "T": 10, "G": 6, "C": 6},
        homopolymer_warn={"A": 8, "T": 8, "G": 5, "C": 5},
    ),
    "twist_default": RepeatProfile(
        name="twist_default",
        direct_fail=20,
        direct_warn=16,
        homopolymer_fail={base: 14 for base in "ACGT"},
        homopolymer_warn={base: 10 for base in "ACGT"},
    ),
    "idt_gblocks": RepeatProfile(
        name="idt_gblocks",
        direct_fail=20,
        direct_warn=20,
        homopolymer_fail={"A": 10, "T": 10, "G": 6, "C": 6},
        homopolymer_warn={"A": 8, "T": 8, "G": 5, "C": 5},
        idt_warn_repeats_only=True,
    ),
    "genscript_default": RepeatProfile(
        name="genscript_default",
        direct_fail=20,
        direct_warn=16,
        homopolymer_fail={base: 14 for base in "ACGT"},
        homopolymer_warn={base: 8 for base in "ACGT"},
    ),
}

BIOLOGICAL_REPEAT_NOTE = (
    " Biological context note: annotated required viral repeats such as LTRs or ITRs may be intentional, "
    "but still need synthesis and stable-propagation review."
)


def run_repeat_instability_check(sequence: AnnotatedSequence, spec: DesignSpec) -> ValidationCheck:
    profile = repeat_profile_for(spec)
    dna = sequence.sequence
    homopolymer = first_profile_homopolymer(dna, thresholds=profile.homopolymer_fail)
    if homopolymer is not None:
        start, end, base, threshold = homopolymer
        message = "Homopolymer run of 12 or more bases may fail synthesis or sequencing."
        if profile.name != LEGACY_PROFILE.name:
            message = (
                f"{profile.name} homopolymer threshold exceeded: {base} run of {threshold} or more bases may fail "
                "synthesis or sequencing."
            )
        return fail_check(
            CHECK_NAME,
            message,
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

    repeat = first_exact_repeat(dna, k=profile.direct_fail)
    if repeat is not None:
        message = f"{repeat.kind} repeat of at least 40 bp may promote recombination or synthesis instability."
        if profile.name != LEGACY_PROFILE.name:
            message = (
                f"{profile.name} {repeat.kind} repeat of at least {profile.direct_fail} bp may promote recombination "
                "or synthesis instability."
            )
        if profile.idt_warn_repeats_only or is_required_viral_repeat(sequence, spec, repeat):
            return warn_check(CHECK_NAME, message + BIOLOGICAL_REPEAT_NOTE, region(repeat.start, repeat.end, len(dna)))
        return fail_check(
            CHECK_NAME,
            message,
            region(repeat.start, repeat.end, len(dna)),
        )

    warn_repeat = first_exact_repeat(dna, k=profile.direct_warn)
    if warn_repeat is not None:
        message = f"{warn_repeat.kind} repeat of at least 25 bp is below the blocking threshold but should be reviewed."
        if profile.name != LEGACY_PROFILE.name:
            message = (
                f"{profile.name} {warn_repeat.kind} repeat of at least {profile.direct_warn} bp is below the blocking threshold "
                "but should be reviewed."
            )
        return warn_check(
            CHECK_NAME,
            message + BIOLOGICAL_REPEAT_NOTE,
            region(warn_repeat.start, warn_repeat.end, len(dna)),
        )

    warn_homopolymer = first_profile_homopolymer(dna, thresholds=profile.homopolymer_warn)
    if warn_homopolymer is not None:
        start, end, base, threshold = warn_homopolymer
        message = "Homopolymer run of 8 or more bases should be reviewed."
        if profile.name != LEGACY_PROFILE.name:
            message = f"{profile.name} homopolymer review threshold reached: {base} run of {threshold} or more bases should be reviewed."
        return warn_check(
            CHECK_NAME,
            message,
            region(start, end, len(dna)),
        )

    return pass_check(CHECK_NAME, "No blocking repeat, homopolymer, or GC-instability pattern detected.")


def repeat_profile_for(spec: DesignSpec) -> RepeatProfile:
    text = " ".join([*(spec.constraints or []), str(spec.source or "")]).lower()
    if not text:
        return LEGACY_PROFILE
    if "idt" in text or "gblock" in text or "g-block" in text:
        return PROVIDER_PROFILES["idt_gblocks"]
    if "twist" in text:
        return PROVIDER_PROFILES["twist_default"]
    if "genscript" in text or "gen script" in text:
        return PROVIDER_PROFILES["genscript_default"]
    if "conservative" in text:
        return PROVIDER_PROFILES["conservative_default"]
    return LEGACY_PROFILE


def first_profile_homopolymer(sequence: str, *, thresholds: dict[str, int]) -> tuple[int, int, str, int] | None:
    run_start = 0
    for index in range(1, len(sequence) + 1):
        if index < len(sequence) and sequence[index] == sequence[run_start]:
            continue
        base = sequence[run_start]
        threshold = thresholds[base]
        if index - run_start >= threshold:
            return run_start, index, base, threshold
        run_start = index
    return None


def is_required_viral_repeat(sequence: AnnotatedSequence, spec: DesignSpec, repeat: RepeatHit) -> bool:
    context = " ".join(
        value
        for value in [sequence.vector_profile, spec.vector_type or "", spec.application or "", *(spec.tags or [])]
        if value
    ).lower()
    if not any(marker in context for marker in ("lentiviral", "retroviral", "aav", "adeno-associated")):
        return False

    first = (repeat.start, repeat.end)
    second = (repeat.other_start, repeat.other_start + (repeat.end - repeat.start))
    first_overlaps = any(repeat_overlaps_viral_feature(first, feature.name, feature.start, feature.end) for feature in sequence.features)
    second_overlaps = any(repeat_overlaps_viral_feature(second, feature.name, feature.start, feature.end) for feature in sequence.features)
    return first_overlaps and second_overlaps


def repeat_overlaps_viral_feature(repeat: tuple[int, int], feature_name: str, feature_start: int, feature_end: int) -> bool:
    return is_viral_repeat_feature(feature_name) and overlaps(repeat[0], repeat[1], feature_start, feature_end)


def is_viral_repeat_feature(name: str) -> bool:
    normalized = name.lower()
    return "ltr" in normalized or "itr" in normalized


def overlaps(start: int, end: int, other_start: int, other_end: int) -> bool:
    return start < other_end and other_start < end


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
