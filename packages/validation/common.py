from __future__ import annotations

from dataclasses import dataclass
from math import prod
from typing import Iterable

from packages.core.schemas import AnnotatedFeature, AnnotatedSequence, DesignSpec, FeatureRegion, ValidationCheck


CHECK_VERSION = "phase3-validation-v1"


@dataclass(frozen=True)
class HostContext:
    organism: str
    host_class: str


def pass_check(name: str, message: str, region: FeatureRegion | None = None) -> ValidationCheck:
    return ValidationCheck(name=name, status="PASS", message=message, region=region)


def warn_check(name: str, message: str, region: FeatureRegion | None = None) -> ValidationCheck:
    return ValidationCheck(name=name, status="WARN", message=message, region=region)


def fail_check(name: str, message: str, region: FeatureRegion | None = None) -> ValidationCheck:
    return ValidationCheck(name=name, status="FAIL", message=message, region=region)


def region(start: int, end: int, sequence_length: int) -> FeatureRegion:
    start = max(0, min(start, sequence_length - 1))
    end = max(start + 1, min(end, sequence_length))
    return FeatureRegion(start=start, end=end)


def features_of(sequence: AnnotatedSequence, *types: str) -> list[AnnotatedFeature]:
    wanted = {feature_type.lower() for feature_type in types}
    return [feature for feature in sequence.features if str(feature.type).lower() in wanted]


def text_for_feature(feature: AnnotatedFeature) -> str:
    return feature.name.lower().replace("_", " ").replace("-", " ")


def host_context(spec: DesignSpec) -> HostContext:
    organism = (spec.organism or "").strip()
    text = organism.lower()
    if any(token in text for token in ["human", "homo sapiens", "hek", "hela", "cho", "mammal", "mouse", "mus musculus"]):
        return HostContext(organism=organism, host_class="mammalian")
    if any(token in text for token in ["saccharomyces", "yeast", "cerevisiae"]):
        return HostContext(organism=organism, host_class="yeast")
    if any(token in text for token in ["escherichia", "e. coli", "ecoli", "bacteria", "bacterial"]):
        return HostContext(organism=organism, host_class="bacterial")
    return HostContext(organism=organism, host_class="unknown")


def circular_between(start: int, end: int, point: int, length: int) -> bool:
    if start <= end:
        return start <= point < end
    return point >= start or point < end


def overlaps_any(start: int, end: int, features: Iterable[AnnotatedFeature], *, padding: int = 0) -> bool:
    for feature in features:
        if start < feature.end + padding and end > feature.start - padding:
            return True
    return False


def reverse_complement(sequence: str) -> str:
    return sequence.translate(str.maketrans("ACGT", "TGCA"))[::-1]


def gc_fraction(sequence: str) -> float:
    if not sequence:
        return 0.0
    return (sequence.count("G") + sequence.count("C")) / len(sequence)


def geometric_mean(values: Iterable[float]) -> float:
    vals = [max(value, 1e-6) for value in values]
    if not vals:
        return 0.0
    return prod(vals) ** (1.0 / len(vals))
