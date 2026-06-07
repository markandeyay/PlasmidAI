from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb

from packages.core.schemas import OutcomeReport


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class OutcomeRecord:
    outcome_id: str
    design_id: str
    user_id: str
    report: OutcomeReport
    created_at: datetime
    updated_at: datetime
    derived_at: datetime | None = None


@dataclass(frozen=True)
class PendingOutcomePrompt:
    design_id: str
    session_id: str
    created_at: datetime
    days_since_created: int


class OutcomeStore(Protocol):
    def create(self, *, report: OutcomeReport, user_id: str, outcome_id: str | None = None) -> OutcomeRecord: ...

    def latest_for_design(self, design_id: str) -> OutcomeRecord | None: ...

    def list_pending_prompts(self, *, user_id: str, min_age_days: int = 14) -> list[PendingOutcomePrompt]: ...

    def list_underived(self, *, limit: int = 100) -> list[OutcomeRecord]: ...

    def mark_derived(self, outcome_ids: list[str], *, derived_at: datetime | None = None) -> None: ...


@dataclass
class InMemoryOutcomeStore:
    records: dict[str, OutcomeRecord] = field(default_factory=dict)
    design_index: dict[str, tuple[str, datetime]] = field(default_factory=dict)

    def create(self, *, report: OutcomeReport, user_id: str, outcome_id: str | None = None) -> OutcomeRecord:
        now = utc_now()
        record = OutcomeRecord(
            outcome_id=outcome_id or f"outcome_{uuid4().hex}",
            design_id=report.design_id,
            user_id=user_id,
            report=report,
            created_at=now,
            updated_at=now,
        )
        self.records[record.outcome_id] = record
        return record

    def latest_for_design(self, design_id: str) -> OutcomeRecord | None:
        matches = [record for record in self.records.values() if record.design_id == design_id]
        return max(matches, key=lambda record: record.created_at) if matches else None

    def list_pending_prompts(self, *, user_id: str, min_age_days: int = 14) -> list[PendingOutcomePrompt]:
        cutoff = utc_now() - timedelta(days=min_age_days)
        prompted: list[PendingOutcomePrompt] = []
        outcomes_by_design = {record.design_id for record in self.records.values() if record.user_id == user_id}
        for design_id, (session_id, created_at) in self.design_index.items():
            if design_id in outcomes_by_design or created_at > cutoff:
                continue
            prompted.append(
                PendingOutcomePrompt(
                    design_id=design_id,
                    session_id=session_id,
                    created_at=created_at,
                    days_since_created=(utc_now() - created_at).days,
                )
            )
        return sorted(prompted, key=lambda prompt: prompt.created_at)

    def list_underived(self, *, limit: int = 100) -> list[OutcomeRecord]:
        records = [record for record in self.records.values() if record.derived_at is None]
        return sorted(records, key=lambda record: record.created_at)[:limit]

    def mark_derived(self, outcome_ids: list[str], *, derived_at: datetime | None = None) -> None:
        timestamp = derived_at or utc_now()
        for outcome_id in outcome_ids:
            record = self.records[outcome_id]
            self.records[outcome_id] = OutcomeRecord(
                outcome_id=record.outcome_id,
                design_id=record.design_id,
                user_id=record.user_id,
                report=record.report,
                created_at=record.created_at,
                updated_at=timestamp,
                derived_at=timestamp,
            )


@dataclass(frozen=True)
class PostgresOutcomeStore:
    database_url: str

    def create(self, *, report: OutcomeReport, user_id: str, outcome_id: str | None = None) -> OutcomeRecord:
        now = utc_now()
        record = OutcomeRecord(
            outcome_id=outcome_id or f"outcome_{uuid4().hex}",
            design_id=report.design_id,
            user_id=user_id,
            report=report,
            created_at=now,
            updated_at=now,
        )
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                """
                INSERT INTO outcomes (
                    id, design_id, user_id, model_version, outcome_label,
                    construct_validated, sequencing_result, expression_result,
                    functional_result, training_consent, provenance, report,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    record.outcome_id,
                    record.design_id,
                    record.user_id,
                    report.model_version,
                    report.outcome_label,
                    report.construct_validated,
                    report.sequencing_result,
                    report.expression_result,
                    report.functional_result,
                    report.training_consent,
                    Jsonb(report.provenance),
                    Jsonb(report.model_dump(mode="json")),
                    record.created_at,
                    record.updated_at,
                ),
            )
        return record

    def latest_for_design(self, design_id: str) -> OutcomeRecord | None:
        with psycopg.connect(self.database_url) as connection:
            row = connection.execute(
                """
                SELECT id, design_id, user_id, report, created_at, updated_at, derived_at
                FROM outcomes
                WHERE design_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (design_id,),
            ).fetchone()
        return None if row is None else _record_from_row(row)

    def list_pending_prompts(self, *, user_id: str, min_age_days: int = 14) -> list[PendingOutcomePrompt]:
        with psycopg.connect(self.database_url) as connection:
            rows = connection.execute(
                """
                SELECT d.id, d.session_id, d.created_at
                FROM designs d
                JOIN sessions s ON s.id = d.session_id
                LEFT JOIN outcomes o ON o.design_id = d.id
                WHERE s.user_id = %s
                  AND d.created_at <= now() - (%s::text || ' days')::interval
                  AND o.id IS NULL
                ORDER BY d.created_at ASC
                """,
                (user_id, min_age_days),
            ).fetchall()
        now = utc_now()
        return [
            PendingOutcomePrompt(design_id=row[0], session_id=row[1], created_at=row[2], days_since_created=(now - row[2]).days)
            for row in rows
        ]

    def list_underived(self, *, limit: int = 100) -> list[OutcomeRecord]:
        with psycopg.connect(self.database_url) as connection:
            rows = connection.execute(
                """
                SELECT id, design_id, user_id, report, created_at, updated_at, derived_at
                FROM outcomes
                WHERE derived_at IS NULL
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
        return [_record_from_row(row) for row in rows]

    def mark_derived(self, outcome_ids: list[str], *, derived_at: datetime | None = None) -> None:
        if not outcome_ids:
            return
        timestamp = derived_at or utc_now()
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                "UPDATE outcomes SET derived_at = %s, updated_at = %s WHERE id = ANY(%s)",
                (timestamp, timestamp, outcome_ids),
            )


def _record_from_row(row: Any) -> OutcomeRecord:
    return OutcomeRecord(
        outcome_id=row[0],
        design_id=row[1],
        user_id=row[2],
        report=OutcomeReport.model_validate(row[3]),
        created_at=row[4],
        updated_at=row[5],
        derived_at=row[6],
    )
