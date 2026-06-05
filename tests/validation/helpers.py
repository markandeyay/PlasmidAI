from __future__ import annotations

from packages.core.schemas import AnnotatedFeature, AnnotatedSequence, DesignSpec


def feature(kind: str, start: int, end: int, name: str, strand: int = 1) -> AnnotatedFeature:
    return AnnotatedFeature(type=kind, start=start, end=end, strand=strand, name=name, confidence=0.99)


def annotated(sequence: str, features: list[AnnotatedFeature] | None = None, profile: str = "bacterial_expression_vector") -> AnnotatedSequence:
    return AnnotatedSequence(
        sequence=sequence,
        topology="circular",
        features=features or [],
        vector_profile=profile,
        annotation_complete=True,
    )


def spec(organism: str = "Escherichia coli", **kwargs: object) -> DesignSpec:
    return DesignSpec(organism=organism, **kwargs)


def stable_dna(length: int) -> str:
    seed = 17
    bases = "ACGT"
    out: list[str] = []
    while len(out) < length:
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        candidate = bases[(seed >> 8) % 4]
        if len(out) >= 3 and out[-1] == out[-2] == out[-3] == candidate:
            candidate = bases[(bases.index(candidate) + 1) % 4]
        out.append(candidate)
    return "".join(out)
