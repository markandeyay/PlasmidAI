from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from packages.core.schemas import AnnotatedSequence, DesignSpec, GeneratedSequence, RetrievedPlasmid
from packages.core.schemas.models import normalize_dna


FAKE_GENERATOR_VERSION = "fake-template-generator-v1"


class SequenceGenerator(Protocol):
    @property
    def model_version(self) -> str: ...

    def generate(
        self,
        spec: DesignSpec,
        templates: list[RetrievedPlasmid],
        n: int = 1,
    ) -> list[GeneratedSequence]: ...


@dataclass(frozen=True)
class MarkerSwap:
    """An explicit deterministic DNA replacement used only by the fake."""

    original_sequence: str
    replacement_sequence: str

    def apply(self, sequence: str) -> str:
        original = normalize_dna(self.original_sequence)
        replacement = normalize_dna(self.replacement_sequence)
        if sequence.count(original) != 1:
            raise ValueError("marker swap requires exactly one original-sequence match")
        return sequence.replace(original, replacement, 1)


@dataclass(frozen=True)
class FakeGenerator:
    marker_swap: MarkerSwap | None = None
    version: str = FAKE_GENERATOR_VERSION

    @property
    def model_version(self) -> str:
        return self.version

    def generate(
        self,
        spec: DesignSpec,
        templates: list[RetrievedPlasmid],
        n: int = 1,
    ) -> list[GeneratedSequence]:
        del spec
        if n <= 0:
            raise ValueError("n must be positive")
        if not templates:
            return []

        template = templates[0].plasmid
        sequence = template.sequence
        if self.marker_swap is not None:
            sequence = self.marker_swap.apply(sequence)

        # Downstream spike code must re-annotate the candidate with the Phase 0
        # parser. Do not carry trusted-template completeness across generation.
        annotated = AnnotatedSequence(
            sequence=sequence,
            topology="circular",
            features=[],
            vector_profile=template.vector_type or "unknown",
            annotation_complete=False,
        )
        generated = GeneratedSequence(
            annotated_sequence=annotated,
            model_version=self.model_version,
            parent_template_ids=[template.id],
        )
        return [generated.model_copy(deep=True) for _ in range(n)]
