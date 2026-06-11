from __future__ import annotations

from datetime import UTC, datetime, timedelta

from packages.application.outcomes import InMemoryOutcomeStore
from packages.core.schemas import OutcomeReport


def outcome(design_id: str = "design-1") -> OutcomeReport:
    return OutcomeReport(
        design_id=design_id,
        model_version="fake-generator-0",
        construct_validated=True,
        sequencing_result="Sanger sequencing matched expected insert.",
        expression_result="Reporter signal observed.",
        training_consent=True,
        outcome_label="positive",
        provenance={"source": "unit-test"},
    )


def test_in_memory_outcome_store_returns_latest_and_tracks_derived_state() -> None:
    store = InMemoryOutcomeStore()
    first = store.create(report=outcome(), user_id="user-1", outcome_id="outcome-1")
    second = store.create(report=outcome(), user_id="user-1", outcome_id="outcome-2")

    assert store.latest_for_design("design-1") == second
    assert [record.outcome_id for record in store.list_underived()] == ["outcome-1", "outcome-2"]

    store.mark_derived([first.outcome_id])

    assert [record.outcome_id for record in store.list_underived()] == ["outcome-2"]


def test_pending_prompts_exclude_designs_with_outcomes_and_recent_designs() -> None:
    store = InMemoryOutcomeStore()
    old = datetime.now(UTC) - timedelta(days=30)
    recent = datetime.now(UTC) - timedelta(days=2)
    store.design_index = {
        "design-old": ("session-1", old),
        "design-recent": ("session-1", recent),
        "design-reported": ("session-1", old),
    }
    store.create(report=outcome("design-reported"), user_id="user-1")

    prompts = store.list_pending_prompts(user_id="user-1", min_age_days=14)

    assert [prompt.design_id for prompt in prompts] == ["design-old"]
