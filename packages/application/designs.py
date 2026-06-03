from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb

from packages.core.schemas import AnnotatedSequence


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DesignRecord:
    design_id: str
    session_id: str
    job_id: str
    annotated_sequence: AnnotatedSequence
    created_at: datetime
    updated_at: datetime


class DesignStore(Protocol):
    def create(
        self,
        *,
        session_id: str,
        job_id: str,
        annotated_sequence: AnnotatedSequence,
        design_id: str | None = None,
    ) -> DesignRecord: ...

    def get(self, design_id: str) -> DesignRecord | None: ...


@dataclass
class InMemoryDesignStore:
    records: dict[str, DesignRecord] = field(default_factory=dict)

    def create(
        self,
        *,
        session_id: str,
        job_id: str,
        annotated_sequence: AnnotatedSequence,
        design_id: str | None = None,
    ) -> DesignRecord:
        now = utc_now()
        record = DesignRecord(
            design_id=design_id or f"design_{uuid4().hex}",
            session_id=session_id,
            job_id=job_id,
            annotated_sequence=annotated_sequence,
            created_at=now,
            updated_at=now,
        )
        self.records[record.design_id] = record
        return record

    def get(self, design_id: str) -> DesignRecord | None:
        return self.records.get(design_id)


@dataclass(frozen=True)
class PostgresDesignStore:
    database_url: str

    def create(
        self,
        *,
        session_id: str,
        job_id: str,
        annotated_sequence: AnnotatedSequence,
        design_id: str | None = None,
    ) -> DesignRecord:
        now = utc_now()
        record = DesignRecord(
            design_id=design_id or f"design_{uuid4().hex}",
            session_id=session_id,
            job_id=job_id,
            annotated_sequence=annotated_sequence,
            created_at=now,
            updated_at=now,
        )
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                """
                INSERT INTO designs (id, session_id, job_id, status, payload, result, created_at, updated_at)
                VALUES (%s, %s, %s, 'ready', %s, %s, %s, %s)
                """,
                (
                    record.design_id,
                    record.session_id,
                    record.job_id,
                    Jsonb({}),
                    Jsonb({"annotated_sequence": record.annotated_sequence.model_dump(mode="json")}),
                    record.created_at,
                    record.updated_at,
                ),
            )
        return record

    def get(self, design_id: str) -> DesignRecord | None:
        with psycopg.connect(self.database_url) as connection:
            row = connection.execute(
                """
                SELECT id, session_id, job_id, result->'annotated_sequence', created_at, updated_at
                FROM designs
                WHERE id = %s
                """,
                (design_id,),
            ).fetchone()
        if row is None:
            return None
        return DesignRecord(
            design_id=row[0],
            session_id=row[1],
            job_id=row[2],
            annotated_sequence=AnnotatedSequence.model_validate(row[3]),
            created_at=row[4],
            updated_at=row[5],
        )
