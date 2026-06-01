from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from packages.core.schemas import AnnotatedSequence, DesignSpec, GeneratedSequence, RetrievedPlasmid


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
class FakeGenerator:
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
        annotated = AnnotatedSequence(
            sequence=template.sequence,
            topology="circular",
            features=[],
            vector_profile=template.vector_type or "unknown",
            annotation_complete=template.annotation_complete,
        )
        return [
            GeneratedSequence(
                annotated_sequence=annotated,
                model_version=self.model_version,
                parent_template_ids=[template.id],
            )
            for _ in range(n)
        ]


def ensure_generated_sequence_count(generated: Sequence[GeneratedSequence], *, minimum: int = 1) -> None:
    if len(generated) < minimum:
        raise ValueError(f"expected at least {minimum} generated sequence(s), got {len(generated)}")
