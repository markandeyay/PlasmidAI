from __future__ import annotations

"""Evaluate Phase 2 generator rollout observations against promotion policy gates."""

from dataclasses import dataclass
from typing import Literal


RolloutDecision = Literal["promote", "hold", "reject"]


@dataclass(frozen=True)
class RolloutPolicy:
    min_shadow_hours: float = 24.0
    min_shadow_requests: int = 1
    max_critical_violations: int = 0
    max_contract_violations: int = 0
    max_safety_violations: int = 0
    max_absolute_service_error_increase: float = 0.005
    max_relative_service_error_increase: float = 0.25
    require_human_signoff: bool = True
    canary_waves: tuple[int, ...] = (1, 5, 25, 50, 100)
    min_strict_success_rate: float | None = None
    min_novel_rate: float | None = None


@dataclass(frozen=True)
class RolloutObservation:
    shadow_hours: float
    shadow_requests: int
    human_signoff: bool
    current_traffic_percent: int = 0
    critical_violations: int = 0
    contract_violations: int = 0
    safety_violations: int = 0
    candidate_service_error_rate: float = 0.0
    baseline_service_error_rate: float = 0.0
    strict_success_rate: float | None = None
    novel_rate: float | None = None


@dataclass(frozen=True)
class RolloutEvaluation:
    decision: RolloutDecision
    reasons: tuple[str, ...]
    current_traffic_percent: int
    next_traffic_percent: int | None


def evaluate_rollout(
    observation: RolloutObservation,
    policy: RolloutPolicy | None = None,
) -> RolloutEvaluation:
    active_policy = policy or RolloutPolicy()
    reject_reasons = _reject_reasons(observation, active_policy)
    if reject_reasons:
        return RolloutEvaluation(
            decision="reject",
            reasons=tuple(reject_reasons),
            current_traffic_percent=observation.current_traffic_percent,
            next_traffic_percent=None,
        )

    hold_reasons = _hold_reasons(observation, active_policy)
    if hold_reasons:
        return RolloutEvaluation(
            decision="hold",
            reasons=tuple(hold_reasons),
            current_traffic_percent=observation.current_traffic_percent,
            next_traffic_percent=observation.current_traffic_percent,
        )

    return RolloutEvaluation(
        decision="promote",
        reasons=("all_promotion_criteria_met",),
        current_traffic_percent=observation.current_traffic_percent,
        next_traffic_percent=next_canary_wave(observation.current_traffic_percent, active_policy.canary_waves),
    )


def next_canary_wave(current_traffic_percent: int, waves: tuple[int, ...] = RolloutPolicy().canary_waves) -> int | None:
    for wave in sorted(waves):
        if current_traffic_percent < wave:
            return wave
    return None


def _reject_reasons(observation: RolloutObservation, policy: RolloutPolicy) -> list[str]:
    reasons: list[str] = []
    if observation.critical_violations > policy.max_critical_violations:
        reasons.append("critical_violations_present")
    if observation.contract_violations > policy.max_contract_violations:
        reasons.append("contract_violations_present")
    if observation.safety_violations > policy.max_safety_violations:
        reasons.append("safety_violations_present")
    return reasons


def _hold_reasons(observation: RolloutObservation, policy: RolloutPolicy) -> list[str]:
    reasons: list[str] = []
    if observation.shadow_hours < policy.min_shadow_hours:
        reasons.append("shadow_observation_incomplete")
    if observation.shadow_requests < policy.min_shadow_requests:
        reasons.append("shadow_sample_too_small")
    if policy.require_human_signoff and not observation.human_signoff:
        reasons.append("human_signoff_missing")
    if _service_error_increase_is_material(observation, policy):
        reasons.append("service_error_rate_increased")
    if policy.min_strict_success_rate is not None and not _metric_meets_threshold(
        observation.strict_success_rate,
        policy.min_strict_success_rate,
    ):
        reasons.append("strict_success_rate_below_policy")
    if policy.min_novel_rate is not None and not _metric_meets_threshold(observation.novel_rate, policy.min_novel_rate):
        reasons.append("novel_rate_below_policy")
    return reasons


def _service_error_increase_is_material(observation: RolloutObservation, policy: RolloutPolicy) -> bool:
    increase = observation.candidate_service_error_rate - observation.baseline_service_error_rate
    if increase <= policy.max_absolute_service_error_increase:
        return False
    if observation.baseline_service_error_rate <= 0:
        return True
    relative_increase = increase / observation.baseline_service_error_rate
    return relative_increase > policy.max_relative_service_error_increase


def _metric_meets_threshold(value: float | None, threshold: float) -> bool:
    return value is not None and value >= threshold
