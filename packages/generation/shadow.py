from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Literal, Mapping, Protocol
from uuid import uuid4

from packages.core.schemas import DesignSpec, GeneratedSequence, RetrievedPlasmid, ValidationReport
from packages.generation.generator import SequenceGenerator
from packages.generation.registry import ModelRegistryRecord


@dataclass(frozen=True)
class ShadowOutputSummary:
    index: int
    model_version: str
    sequence_sha256: str
    length_bp: int
    annotation_complete: bool
    vector_profile: str
    feature_counts: dict[str, int]
    parent_template_ids: list[str]
    validation_overall: str | None = None
    validation_fail_count: int | None = None
    validation_warn_count: int | None = None


@dataclass(frozen=True)
class ShadowComparisonRecord:
    request_id: str
    incumbent_model_version: str
    candidate_model_version: str
    served_model_version: str
    incumbent_count: int
    candidate_count: int
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    trace_id: str | None = None
    incumbent_latency_ms: float | None = None
    candidate_latency_ms: float | None = None
    total_latency_ms: float | None = None
    incumbent_outputs: list[ShadowOutputSummary] = field(default_factory=list)
    candidate_outputs: list[ShadowOutputSummary] = field(default_factory=list)
    sequence_identity: float | None = None
    length_delta_bp: int | None = None
    exact_sequence_match: bool | None = None
    parent_template_overlap: int | None = None
    comparison_label: str = "not_evaluable"
    reason_codes: list[str] = field(default_factory=list)
    payload_retention: str = "hash_only"
    incumbent_error: str | None = None
    incumbent_error_class: str | None = None
    candidate_error: str | None = None
    candidate_error_class: str | None = None
    candidate_timed_out: bool = False


class ShadowLogSink(Protocol):
    def record(self, comparison: ShadowComparisonRecord) -> None: ...


@dataclass
class InMemoryShadowLogSink:
    records: list[ShadowComparisonRecord] = field(default_factory=list)

    def record(self, comparison: ShadowComparisonRecord) -> None:
        self.records.append(comparison)


ShadowPayloadClass = Literal["raw", "redacted", "aggregate"]
PAYLOAD_CLASSES: tuple[ShadowPayloadClass, ...] = ("raw", "redacted", "aggregate")


@dataclass(frozen=True)
class ShadowRetentionPolicy:
    raw_payload_days: int = 7
    redacted_payload_days: int = 30
    aggregate_payload_days: int = 90
    raw_sample_rate: float = 1.0
    redacted_sample_rate: float = 1.0
    aggregate_sample_rate: float = 1.0

    def retention_days_for(self, payload_class: ShadowPayloadClass) -> int:
        if payload_class == "raw":
            return self.raw_payload_days
        if payload_class == "redacted":
            return self.redacted_payload_days
        if payload_class == "aggregate":
            return self.aggregate_payload_days
        raise ValueError(f"unsupported shadow payload class: {payload_class}")

    def sample_rate_for(self, payload_class: ShadowPayloadClass) -> float:
        if payload_class == "raw":
            return self.raw_sample_rate
        if payload_class == "redacted":
            return self.redacted_sample_rate
        if payload_class == "aggregate":
            return self.aggregate_sample_rate
        raise ValueError(f"unsupported shadow payload class: {payload_class}")


@dataclass(frozen=True)
class ShadowPayload:
    payload_id: str
    payload_class: ShadowPayloadClass
    payload: Mapping[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_record(self) -> dict[str, Any]:
        return {
            "payload_id": self.payload_id,
            "payload_class": self.payload_class,
            "created_at": _ensure_utc(self.created_at).isoformat(),
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class ShadowPruneResult:
    kept: int
    removed: int


@dataclass(frozen=True)
class JsonlShadowLogSink:
    root: Path
    policy: ShadowRetentionPolicy = field(default_factory=ShadowRetentionPolicy)

    def append(self, payload: ShadowPayload) -> bool:
        if not should_sample_payload(payload.payload_id, self.policy.sample_rate_for(payload.payload_class)):
            return False
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(payload.payload_class)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload.as_record(), sort_keys=True) + "\n")
        return True

    def prune(self, *, now: datetime | None = None) -> ShadowPruneResult:
        reference_time = _ensure_utc(now or datetime.now(timezone.utc))
        kept = 0
        removed = 0
        for payload_class in PAYLOAD_CLASSES:
            path = self._path(payload_class)
            if not path.exists():
                continue
            kept_lines: list[str] = []
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                if _line_is_expired(line, payload_class, policy=self.policy, now=reference_time):
                    removed += 1
                    continue
                kept += 1
                kept_lines.append(line)
            if kept_lines:
                path.write_text("\n".join(kept_lines) + "\n", encoding="utf-8")
            else:
                path.unlink()
        return ShadowPruneResult(kept=kept, removed=removed)

    def iter_records(self, payload_class: ShadowPayloadClass) -> list[dict[str, Any]]:
        path = self._path(payload_class)
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _path(self, payload_class: ShadowPayloadClass) -> Path:
        return self.root / f"{payload_class}.jsonl"


@dataclass(frozen=True)
class ShadowComparisonGenerator:
    """Run a candidate generator beside an incumbent without serving it."""

    incumbent: SequenceGenerator
    candidate: SequenceGenerator
    log_sink: ShadowLogSink
    request_id_factory: Callable[[], str] = lambda: str(uuid4())
    validator: Callable[[GeneratedSequence, DesignSpec], ValidationReport] | None = None
    candidate_timeout_seconds: float | None = None

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
        total_started = time.perf_counter()
        incumbent_started = time.perf_counter()
        try:
            incumbent_output = self.incumbent.generate(spec, templates, n=n)
            incumbent_latency_ms = elapsed_ms(incumbent_started)
        except Exception as exc:
            incumbent_latency_ms = elapsed_ms(incumbent_started)
            self._record_safely(
                ShadowComparisonRecord(
                    request_id=request_id,
                    incumbent_model_version=self.incumbent.model_version,
                    candidate_model_version=self.candidate.model_version,
                    served_model_version=self.incumbent.model_version,
                    incumbent_count=0,
                    candidate_count=0,
                    incumbent_latency_ms=incumbent_latency_ms,
                    total_latency_ms=elapsed_ms(total_started),
                    incumbent_error=str(exc),
                    incumbent_error_class=exc.__class__.__name__,
                    comparison_label="not_evaluable",
                    reason_codes=["incumbent_error"],
                )
            )
            raise
        candidate_count = 0
        candidate_error: str | None = None
        candidate_error_class: str | None = None
        candidate_timed_out = False
        candidate_output: list[GeneratedSequence] = []
        candidate_started = time.perf_counter()
        try:
            candidate_output = self.candidate.generate(spec, templates, n=n)
            candidate_latency_ms = elapsed_ms(candidate_started)
            if self.candidate_timeout_seconds is not None and candidate_latency_ms > self.candidate_timeout_seconds * 1000:
                candidate_timed_out = True
            candidate_count = len(candidate_output)
        except Exception as exc:
            candidate_latency_ms = elapsed_ms(candidate_started)
            candidate_error = str(exc)
            candidate_error_class = exc.__class__.__name__
        incumbent_summaries = summarize_outputs(incumbent_output, spec, validator=self.validator)
        candidate_summaries = summarize_outputs(candidate_output, spec, validator=self.validator)
        comparison = compare_outputs(incumbent_summaries, candidate_summaries, candidate_error=candidate_error, candidate_timed_out=candidate_timed_out)
        self._record_safely(
            ShadowComparisonRecord(
                request_id=request_id,
                incumbent_model_version=self.incumbent.model_version,
                candidate_model_version=self.candidate.model_version,
                served_model_version=self.incumbent.model_version,
                incumbent_count=len(incumbent_output),
                candidate_count=candidate_count,
                incumbent_latency_ms=incumbent_latency_ms,
                candidate_latency_ms=candidate_latency_ms,
                total_latency_ms=elapsed_ms(total_started),
                incumbent_outputs=incumbent_summaries,
                candidate_outputs=candidate_summaries,
                sequence_identity=comparison["sequence_identity"],
                length_delta_bp=comparison["length_delta_bp"],
                exact_sequence_match=comparison["exact_sequence_match"],
                parent_template_overlap=comparison["parent_template_overlap"],
                comparison_label=str(comparison["comparison_label"]),
                reason_codes=list(comparison["reason_codes"]),
                candidate_error=candidate_error,
                candidate_error_class=candidate_error_class,
                candidate_timed_out=candidate_timed_out,
            )
        )
        return incumbent_output

    def _record_safely(self, comparison: ShadowComparisonRecord) -> None:
        try:
            self.log_sink.record(comparison)
        except Exception:
            # Shadow observability must not break the user-visible incumbent path.
            return


def elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)


def sequence_hash(sequence: str) -> str:
    return hashlib.sha256(sequence.encode("ascii")).hexdigest()


def summarize_outputs(
    outputs: list[GeneratedSequence],
    spec: DesignSpec,
    *,
    validator: Callable[[GeneratedSequence, DesignSpec], ValidationReport] | None,
) -> list[ShadowOutputSummary]:
    summaries: list[ShadowOutputSummary] = []
    for index, output in enumerate(outputs):
        annotated = output.annotated_sequence
        feature_counts: dict[str, int] = {}
        for feature in annotated.features:
            feature_counts[feature.type] = feature_counts.get(feature.type, 0) + 1
        validation_overall: str | None = None
        validation_fail_count: int | None = None
        validation_warn_count: int | None = None
        if validator is not None:
            report = validator(output, spec)
            validation_overall = str(report.overall)
            validation_fail_count = sum(1 for check in report.checks if check.status == "FAIL")
            validation_warn_count = sum(1 for check in report.checks if check.status == "WARN")
        summaries.append(
            ShadowOutputSummary(
                index=index,
                model_version=output.model_version,
                sequence_sha256=sequence_hash(annotated.sequence),
                length_bp=len(annotated.sequence),
                annotation_complete=annotated.annotation_complete,
                vector_profile=annotated.vector_profile,
                feature_counts=feature_counts,
                parent_template_ids=list(output.parent_template_ids),
                validation_overall=validation_overall,
                validation_fail_count=validation_fail_count,
                validation_warn_count=validation_warn_count,
            )
        )
    return summaries


def compare_outputs(
    incumbent_outputs: list[ShadowOutputSummary],
    candidate_outputs: list[ShadowOutputSummary],
    *,
    candidate_error: str | None,
    candidate_timed_out: bool,
) -> dict[str, object]:
    if candidate_error:
        return {
            "sequence_identity": None,
            "length_delta_bp": None,
            "exact_sequence_match": None,
            "parent_template_overlap": None,
            "comparison_label": "not_evaluable",
            "reason_codes": ["candidate_error"],
        }
    if candidate_timed_out:
        return {
            "sequence_identity": None,
            "length_delta_bp": None,
            "exact_sequence_match": None,
            "parent_template_overlap": None,
            "comparison_label": "candidate_regressed",
            "reason_codes": ["candidate_timeout"],
        }
    if not incumbent_outputs or not candidate_outputs:
        return {
            "sequence_identity": None,
            "length_delta_bp": None,
            "exact_sequence_match": None,
            "parent_template_overlap": None,
            "comparison_label": "not_evaluable",
            "reason_codes": ["missing_output"],
        }
    incumbent = incumbent_outputs[0]
    candidate = candidate_outputs[0]
    exact_match = incumbent.sequence_sha256 == candidate.sequence_sha256
    identity = 1.0 if exact_match else 0.0
    length_delta = candidate.length_bp - incumbent.length_bp
    parent_overlap = len(set(incumbent.parent_template_ids).intersection(candidate.parent_template_ids))
    if exact_match:
        label = "candidate_equal"
        reason_codes = ["exact_sequence_match"]
    else:
        label = "candidate_diverged"
        reason_codes = ["sequence_hash_differs"]
    if incumbent.validation_overall and candidate.validation_overall and incumbent.validation_overall != candidate.validation_overall:
        reason_codes.append("validation_status_differs")
    return {
        "sequence_identity": identity,
        "length_delta_bp": length_delta,
        "exact_sequence_match": exact_match,
        "parent_template_overlap": parent_overlap,
        "comparison_label": label,
        "reason_codes": reason_codes,
    }


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


def should_sample_payload(payload_id: str, sample_rate: float) -> bool:
    if sample_rate <= 0:
        return False
    if sample_rate >= 1:
        return True
    digest = hashlib.sha256(payload_id.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) / 0xFFFFFFFF
    return bucket < sample_rate


def payload_is_expired(
    payload_class: ShadowPayloadClass,
    created_at: datetime,
    *,
    policy: ShadowRetentionPolicy | None = None,
    now: datetime | None = None,
) -> bool:
    active_policy = policy or ShadowRetentionPolicy()
    reference_time = _ensure_utc(now or datetime.now(timezone.utc))
    cutoff = reference_time - timedelta(days=active_policy.retention_days_for(payload_class))
    return _ensure_utc(created_at) < cutoff


def _line_is_expired(line: str, payload_class: ShadowPayloadClass, *, policy: ShadowRetentionPolicy, now: datetime) -> bool:
    try:
        record = json.loads(line)
        created_at = _parse_timestamp(str(record["created_at"]))
        record_class = record.get("payload_class", payload_class)
        if record_class not in PAYLOAD_CLASSES:
            return True
        return payload_is_expired(record_class, created_at, policy=policy, now=now)
    except Exception:
        return True


def _parse_timestamp(value: str) -> datetime:
    normalized = value.removesuffix("Z") + "+00:00" if value.endswith("Z") else value
    return _ensure_utc(datetime.fromisoformat(normalized))


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
