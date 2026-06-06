from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol
from uuid import uuid4

from packages.core.schemas import DesignSpec, GeneratedSequence, RetrievedPlasmid
from packages.generation.generator import SequenceGenerator
from packages.generation.registry import ModelRegistryRecord


@dataclass(frozen=True)
class ShadowComparisonRecord:
    request_id: str
    incumbent_model_version: str
    candidate_model_version: str
    served_model_version: str
    incumbent_count: int
    candidate_count: int
    candidate_error: str | None = None


class ShadowLogSink(Protocol):
    def record(self, comparison: ShadowComparisonRecord) -> None: ...


@dataclass
class InMemoryShadowLogSink:
    records: list[ShadowComparisonRecord] = field(default_factory=list)

    def record(self, comparison: ShadowComparisonRecord) -> None:
        self.records.append(comparison)


@dataclass(frozen=True)
class ShadowComparisonGenerator:
    """Run a candidate generator beside an incumbent without serving it."""

    incumbent: SequenceGenerator
    candidate: SequenceGenerator
    log_sink: ShadowLogSink
    request_id_factory: Callable[[], str] = lambda: str(uuid4())

    @property
    def model_version(self) -> str:
        return f"{self.incumbent.model_version}+shadow:{self.candidate.model_version}"

    def generate(
        self,
        spec: DesignSpec,
        templates: list[RetrievedPlasmid],
        n: int = 1,
    ) -> list[GeneratedSequence]:
        request_id = self.request_id_factory()
        incumbent_output = self.incumbent.generate(spec, templates, n=n)
        candidate_count = 0
        candidate_error: str | None = None
        try:
            candidate_output = self.candidate.generate(spec, templates, n=n)
            candidate_count = len(candidate_output)
        except Exception as exc:
            candidate_error = str(exc)
        self.log_sink.record(
            ShadowComparisonRecord(
                request_id=request_id,
                incumbent_model_version=self.incumbent.model_version,
                candidate_model_version=self.candidate.model_version,
                served_model_version=self.incumbent.model_version,
                incumbent_count=len(incumbent_output),
                candidate_count=candidate_count,
                candidate_error=candidate_error,
            )
        )
        return incumbent_output


def should_serve_model(record: ModelRegistryRecord) -> bool:
    return record.rollout_state in {"canary", "full"}


def should_shadow_model(record: ModelRegistryRecord) -> bool:
    return record.rollout_state == "shadow"


def incumbent_record(records: list[ModelRegistryRecord]) -> ModelRegistryRecord | None:
    full_records = [record for record in records if record.rollout_state == "full"]
    if full_records:
        return full_records[-1]
    canary_records = [record for record in records if record.rollout_state == "canary"]
    return canary_records[-1] if canary_records else None


def shadow_candidate_records(records: list[ModelRegistryRecord]) -> list[ModelRegistryRecord]:
    return [record for record in records if should_shadow_model(record)]
