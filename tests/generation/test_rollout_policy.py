from __future__ import annotations

from packages.generation.rollout_policy import RolloutObservation, RolloutPolicy, evaluate_rollout, next_canary_wave


def test_rollout_evaluator_promotes_clean_shadow_to_first_canary_wave() -> None:
    evaluation = evaluate_rollout(
        RolloutObservation(
            shadow_hours=24.5,
            shadow_requests=100,
            human_signoff=True,
            baseline_service_error_rate=0.01,
            candidate_service_error_rate=0.011,
        )
    )

    assert evaluation.decision == "promote"
    assert evaluation.reasons == ("all_promotion_criteria_met",)
    assert evaluation.current_traffic_percent == 0
    assert evaluation.next_traffic_percent == 1


def test_rollout_evaluator_holds_until_observation_and_signoff_are_complete() -> None:
    evaluation = evaluate_rollout(
        RolloutObservation(
            shadow_hours=6,
            shadow_requests=0,
            human_signoff=False,
        )
    )

    assert evaluation.decision == "hold"
    assert evaluation.next_traffic_percent == 0
    assert evaluation.reasons == (
        "shadow_observation_incomplete",
        "shadow_sample_too_small",
        "human_signoff_missing",
    )


def test_rollout_evaluator_rejects_contract_or_safety_violations() -> None:
    evaluation = evaluate_rollout(
        RolloutObservation(
            shadow_hours=25,
            shadow_requests=100,
            human_signoff=True,
            contract_violations=1,
            safety_violations=1,
        )
    )

    assert evaluation.decision == "reject"
    assert evaluation.next_traffic_percent is None
    assert evaluation.reasons == ("contract_violations_present", "safety_violations_present")


def test_rollout_evaluator_holds_material_service_error_increase() -> None:
    policy = RolloutPolicy(max_absolute_service_error_increase=0.005, max_relative_service_error_increase=0.25)
    evaluation = evaluate_rollout(
        RolloutObservation(
            shadow_hours=25,
            shadow_requests=100,
            human_signoff=True,
            baseline_service_error_rate=0.02,
            candidate_service_error_rate=0.04,
        ),
        policy=policy,
    )

    assert evaluation.decision == "hold"
    assert evaluation.reasons == ("service_error_rate_increased",)


def test_next_canary_wave_advances_through_policy_waves() -> None:
    assert next_canary_wave(0) == 1
    assert next_canary_wave(1) == 5
    assert next_canary_wave(25) == 50
    assert next_canary_wave(100) is None
