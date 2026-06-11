from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from packages.core.schemas import DesignSpec, GeneratedSequence, RetrievedPlasmid
from packages.generation.generator import SequenceGenerator


AssignmentMode = str


@dataclass(frozen=True)
class CanaryPolicy:
    policy_id: str
    candidate_model_version: str
    incumbent_model_version: str
    traffic_percent: float
    enabled: bool = True
    assignment_mode: AssignmentMode = "sticky_session"
    assignment_salt: str = "phase2-canary"
    fallback_to_incumbent_on_candidate_failure: bool = True
    max_consecutive_candidate_failures: int = 3

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise ValueError("policy_id is required")
        if not 0 <= self.traffic_percent <= 100:
            raise ValueError("traffic_percent must be between 0 and 100")
        if self.assignment_mode not in {"sticky_session", "per_request"}:
            raise ValueError("unsupported assignment_mode")
        if self.max_consecutive_candidate_failures < 1:
            raise ValueError("max_consecutive_candidate_failures must be positive")


@dataclass(frozen=True)
class CanaryAssignmentRecord:
    request_id: str
    policy_id: str
    timestamp: str
    assignment_key_hash: str
    bucket: int
    assigned_model_version: str
    served_model_version: str
    incumbent_model_version: str
    candidate_model_version: str
    eligible: bool
    reason_codes: list[str]
    fallback_served: bool
    latency_ms: float
    candidate_error: str | None = None
    candidate_error_class: str | None = None
    rollback_active: bool = False


class CanaryMetricsSink(Protocol):
    def record(self, assignment: CanaryAssignmentRecord) -> None: ...


@dataclass
class InMemoryCanaryMetricsSink:
    records: list[CanaryAssignmentRecord] = field(default_factory=list)

    def record(self, assignment: CanaryAssignmentRecord) -> None:
        self.records.append(assignment)


@dataclass
class CanaryGenerator:
    incumbent: SequenceGenerator
    candidate: SequenceGenerator
    policy: CanaryPolicy
    metrics_sink: CanaryMetricsSink
    rollback_active: bool = False
    consecutive_candidate_failures: int = 0

    @property
    def model_version(self) -> str:
        return f"{self.incumbent.model_version}+canary:{self.candidate.model_version}"

    def generate(
        self,
        spec: DesignSpec,
        templates: list[RetrievedPlasmid],
        n: int = 1,
    ) -> list[GeneratedSequence]:
        request_id = str(uuid4())
        return self.generate_for_request(spec, templates, n=n, assignment_key=request_id, request_id=request_id)

    def generate_for_request(
        self,
        spec: DesignSpec,
        templates: list[RetrievedPlasmid],
        *,
        n: int = 1,
        assignment_key: str,
        request_id: str | None = None,
    ) -> list[GeneratedSequence]:
        started = time.perf_counter()
        request_id = request_id or str(uuid4())
        assignment_key_hash = stable_hash(assignment_key)
        bucket = assignment_bucket(self.policy, assignment_key)
        reason_codes: list[str] = []
        eligible = self.policy.enabled and not self.rollback_active
        if not self.policy.enabled:
            reason_codes.append("policy_disabled")
        if self.rollback_active:
            reason_codes.append("rollback_active")
        assigned_to_candidate = eligible and bucket < int(self.policy.traffic_percent * 100)
        assigned_model_version = self.candidate.model_version if assigned_to_candidate else self.incumbent.model_version
        fallback_served = False
        candidate_error: str | None = None
        candidate_error_class: str | None = None
        try:
            if assigned_to_candidate:
                generated = self.candidate.generate(spec, templates, n=n)
                if not generated:
                    raise ValueError("candidate returned no sequences")
                self.consecutive_candidate_failures = 0
                served_model_version = self.candidate.model_version
                reason_codes.append("candidate_assigned")
            else:
                generated = self.incumbent.generate(spec, templates, n=n)
                served_model_version = self.incumbent.model_version
                reason_codes.append("incumbent_assigned")
        except Exception as exc:
            candidate_error = str(exc)
            candidate_error_class = exc.__class__.__name__
            self.consecutive_candidate_failures += 1
            if self.consecutive_candidate_failures >= self.policy.max_consecutive_candidate_failures:
                self.rollback_active = True
                reason_codes.append("rollback_triggered")
            if not self.policy.fallback_to_incumbent_on_candidate_failure:
                self._record(
                    request_id=request_id,
                    policy_id=self.policy.policy_id,
                    assignment_key_hash=assignment_key_hash,
                    bucket=bucket,
                    assigned_model_version=assigned_model_version,
                    served_model_version=self.candidate.model_version,
                    eligible=eligible,
                    reason_codes=reason_codes + ["candidate_error"],
                    fallback_served=False,
                    started=started,
                    candidate_error=candidate_error,
                    candidate_error_class=candidate_error_class,
                )
                raise
            generated = self.incumbent.generate(spec, templates, n=n)
            served_model_version = self.incumbent.model_version
            fallback_served = True
            reason_codes.extend(["candidate_error", "fallback_served"])
        self._record(
            request_id=request_id,
            policy_id=self.policy.policy_id,
            assignment_key_hash=assignment_key_hash,
            bucket=bucket,
            assigned_model_version=assigned_model_version,
            served_model_version=served_model_version,
            eligible=eligible,
            reason_codes=reason_codes,
            fallback_served=fallback_served,
            started=started,
            candidate_error=candidate_error,
            candidate_error_class=candidate_error_class,
        )
        return generated

    def _record(
        self,
        *,
        request_id: str,
        policy_id: str,
        assignment_key_hash: str,
        bucket: int,
        assigned_model_version: str,
        served_model_version: str,
        eligible: bool,
        reason_codes: list[str],
        fallback_served: bool,
        started: float,
        candidate_error: str | None = None,
        candidate_error_class: str | None = None,
    ) -> None:
        record = CanaryAssignmentRecord(
            request_id=request_id,
            policy_id=policy_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            assignment_key_hash=assignment_key_hash,
            bucket=bucket,
            assigned_model_version=assigned_model_version,
            served_model_version=served_model_version,
            incumbent_model_version=self.incumbent.model_version,
            candidate_model_version=self.candidate.model_version,
            eligible=eligible,
            reason_codes=reason_codes,
            fallback_served=fallback_served,
            latency_ms=round((time.perf_counter() - started) * 1000, 3),
            candidate_error=candidate_error,
            candidate_error_class=candidate_error_class,
            rollback_active=self.rollback_active,
        )
        try:
            self.metrics_sink.record(record)
        except Exception:
            return


def assignment_bucket(policy: CanaryPolicy, assignment_key: str) -> int:
    digest = hashlib.sha256(f"{policy.policy_id}:{policy.assignment_salt}:{assignment_key}".encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % 10000


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
