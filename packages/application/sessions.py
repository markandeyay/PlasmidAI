from __future__ import annotations

"""Session persistence and async job contracts for the application layer."""

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Literal, Protocol
from uuid import uuid4

import psycopg
from pydantic import BaseModel, ConfigDict, Field
from psycopg.types.json import Jsonb

from packages.core.schemas import (
    AnnotatedSequence,
    DesignSpec,
    PlasmidRecommendation,
    RetrievedPlasmid,
    ValidationReport,
)


SessionTurnType = Literal["design", "refine"]
JobStatus = Literal["queued", "running", "succeeded", "failed"]


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


class ApplicationModel(BaseModel):
    """Small envelope model base for application-layer API responses."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )


class SessionJobResult(ApplicationModel):
    """Result envelope returned by async design jobs."""

    design_spec: DesignSpec | None = None
    clarification_question: str | None = None
    annotated_sequence: AnnotatedSequence | None = None
    validation_report: ValidationReport | None = None
    retrieved_templates: list[RetrievedPlasmid] = Field(default_factory=list)
    recommendations: list[PlasmidRecommendation] = Field(default_factory=list)
    recommendation_text: str | None = None


@dataclass(frozen=True)
class SessionTurn:
    """One user turn captured inside a design session."""

    turn_id: str
    session_id: str
    turn_index: int
    turn_type: SessionTurnType
    user_text: str
    design_spec: DesignSpec | None
    job_id: str | None
    created_at: datetime


@dataclass(frozen=True)
class DesignSession:
    """Persisted session state with ordered user turns."""

    session_id: str
    user_id: str | None
    created_at: datetime
    updated_at: datetime
    turns: list[SessionTurn]


@dataclass(frozen=True)
class JobRecord:
    """Queued job state returned by the job queue."""

    job_id: str
    status: JobStatus
    session_id: str
    turn_type: SessionTurnType
    created_at: datetime
    result: SessionJobResult | None = None
    error: str | None = None


class SessionStore(Protocol):
    """Persistence boundary for session and turn state."""

    def create_session(self, *, session_id: str | None = None, user_id: str | None = None) -> DesignSession: ...

    def get_session(self, session_id: str) -> DesignSession | None: ...

    def add_turn(
        self,
        session_id: str,
        *,
        turn_type: SessionTurnType,
        user_text: str,
        job_id: str | None = None,
        design_spec: DesignSpec | None = None,
        turn_id: str | None = None,
    ) -> SessionTurn: ...

    def set_turn_job_id(self, session_id: str, *, turn_id: str, job_id: str) -> None: ...


class JobQueue(Protocol):
    """Async execution boundary for design and refinement jobs."""

    def enqueue_design(self, *, session: DesignSession, goal: str) -> str: ...

    def enqueue_refinement(self, *, session: DesignSession, instruction: str) -> str: ...

    def get_job(self, job_id: str) -> JobRecord | None: ...


@dataclass
class InMemorySessionStore:
    """Deterministic session store used by tests and local scaffolding."""

    sessions: dict[str, DesignSession] = field(default_factory=dict)

    def create_session(self, *, session_id: str | None = None, user_id: str | None = None) -> DesignSession:
        now = utc_now()
        resolved_session_id = session_id or f"session_{uuid4().hex}"
        session = DesignSession(
            session_id=resolved_session_id,
            user_id=user_id,
            created_at=now,
            updated_at=now,
            turns=[],
        )
        self.sessions[resolved_session_id] = session
        return session

    def get_session(self, session_id: str) -> DesignSession | None:
        return self.sessions.get(session_id)

    def add_turn(
        self,
        session_id: str,
        *,
        turn_type: SessionTurnType,
        user_text: str,
        job_id: str | None = None,
        design_spec: DesignSpec | None = None,
        turn_id: str | None = None,
    ) -> SessionTurn:
        session = self.sessions.get(session_id)
        if session is None:
            raise KeyError(session_id)
        turn = SessionTurn(
            turn_id=turn_id or f"turn_{uuid4().hex}",
            session_id=session_id,
            turn_index=len(session.turns) + 1,
            turn_type=turn_type,
            user_text=user_text,
            design_spec=design_spec,
            job_id=job_id,
            created_at=utc_now(),
        )
        updated_session = DesignSession(
            session_id=session.session_id,
            user_id=session.user_id,
            created_at=session.created_at,
            updated_at=turn.created_at,
            turns=[*session.turns, turn],
        )
        self.sessions[session_id] = updated_session
        return turn

    def set_turn_job_id(self, session_id: str, *, turn_id: str, job_id: str) -> None:
        session = self.sessions.get(session_id)
        if session is None:
            raise KeyError(session_id)
        updated_turns = [
            replace(turn, job_id=job_id) if turn.turn_id == turn_id else turn
            for turn in session.turns
        ]
        self.sessions[session_id] = replace(session, updated_at=utc_now(), turns=updated_turns)


@dataclass(frozen=True)
class PostgresSessionStore:
    """Postgres-backed session store for API session and turn persistence."""

    database_url: str

    def create_session(self, *, session_id: str | None = None, user_id: str | None = None) -> DesignSession:
        now = utc_now()
        resolved_session_id = session_id or f"session_{uuid4().hex}"
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                """
                INSERT INTO sessions (id, user_id, status, created_at, updated_at)
                VALUES (%s, %s, 'active', %s, %s)
                """,
                (resolved_session_id, user_id, now, now),
            )
        return DesignSession(
            session_id=resolved_session_id,
            user_id=user_id,
            created_at=now,
            updated_at=now,
            turns=[],
        )

    def get_session(self, session_id: str) -> DesignSession | None:
        with psycopg.connect(self.database_url) as connection:
            session_row = connection.execute(
                """
                SELECT id, user_id, created_at, updated_at
                FROM sessions
                WHERE id = %s
                """,
                (session_id,),
            ).fetchone()
            if session_row is None:
                return None
            turn_rows = connection.execute(
                """
                SELECT id,
                       session_id,
                       turn_index,
                       payload->>'turn_type',
                       content,
                       payload->'design_spec',
                       payload->>'job_id',
                       created_at
                FROM session_turns
                WHERE session_id = %s
                ORDER BY turn_index ASC
                """,
                (session_id,),
            ).fetchall()
        turns = [
            SessionTurn(
                turn_id=row[0],
                session_id=row[1],
                turn_index=row[2],
                turn_type=row[3],
                user_text=row[4],
                design_spec=DesignSpec.model_validate(row[5]) if row[5] is not None else None,
                job_id=row[6],
                created_at=row[7],
            )
            for row in turn_rows
        ]
        return DesignSession(
            session_id=session_row[0],
            user_id=session_row[1],
            created_at=session_row[2],
            updated_at=session_row[3],
            turns=turns,
        )

    def add_turn(
        self,
        session_id: str,
        *,
        turn_type: SessionTurnType,
        user_text: str,
        job_id: str | None = None,
        design_spec: DesignSpec | None = None,
        turn_id: str | None = None,
    ) -> SessionTurn:
        created_at = utc_now()
        resolved_turn_id = turn_id or f"turn_{uuid4().hex}"
        with psycopg.connect(self.database_url) as connection:
            session_exists = connection.execute(
                "SELECT 1 FROM sessions WHERE id = %s",
                (session_id,),
            ).fetchone()
            if session_exists is None:
                raise KeyError(session_id)
            next_turn_index = connection.execute(
                "SELECT COALESCE(MAX(turn_index), 0) + 1 FROM session_turns WHERE session_id = %s",
                (session_id,),
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO session_turns (
                    id,
                    session_id,
                    turn_index,
                    role,
                    content,
                    payload,
                    created_at
                )
                VALUES (%s, %s, %s, 'user', %s, %s, %s)
                """,
                (
                    resolved_turn_id,
                    session_id,
                    next_turn_index,
                    user_text,
                    Jsonb(
                        {
                            "turn_type": turn_type,
                            "design_spec": design_spec.model_dump(mode="json") if design_spec is not None else None,
                            "job_id": job_id,
                        }
                    ),
                    created_at,
                ),
            )
            connection.execute(
                "UPDATE sessions SET updated_at = %s WHERE id = %s",
                (created_at, session_id),
            )
        return SessionTurn(
            turn_id=resolved_turn_id,
            session_id=session_id,
            turn_index=next_turn_index,
            turn_type=turn_type,
            user_text=user_text,
            design_spec=design_spec,
            job_id=job_id,
            created_at=created_at,
        )

    def set_turn_job_id(self, session_id: str, *, turn_id: str, job_id: str) -> None:
        with psycopg.connect(self.database_url) as connection:
            updated = connection.execute(
                """
                UPDATE session_turns
                SET payload = payload || %s
                WHERE id = %s AND session_id = %s
                """,
                (Jsonb({"job_id": job_id}), turn_id, session_id),
            )
            if updated.rowcount != 1:
                raise KeyError(turn_id)
            connection.execute(
                "UPDATE sessions SET updated_at = %s WHERE id = %s",
                (utc_now(), session_id),
            )

@dataclass
class InMemoryJobQueue:
    """Simple async job queue fake for tests and local API scaffolding."""

    jobs: dict[str, JobRecord] = field(default_factory=dict)

    def enqueue_design(self, *, session: DesignSession, goal: str) -> str:
        return self._enqueue(session_id=session.session_id, turn_type="design")

    def enqueue_refinement(self, *, session: DesignSession, instruction: str) -> str:
        return self._enqueue(session_id=session.session_id, turn_type="refine")

    def get_job(self, job_id: str) -> JobRecord | None:
        return self.jobs.get(job_id)

    def mark_running(self, job_id: str) -> None:
        job = self.jobs[job_id]
        self.jobs[job_id] = JobRecord(
            job_id=job.job_id,
            status="running",
            session_id=job.session_id,
            turn_type=job.turn_type,
            created_at=job.created_at,
            result=job.result,
            error=job.error,
        )

    def complete(self, job_id: str, *, result: SessionJobResult | None = None) -> None:
        job = self.jobs[job_id]
        self.jobs[job_id] = JobRecord(
            job_id=job.job_id,
            status="succeeded",
            session_id=job.session_id,
            turn_type=job.turn_type,
            created_at=job.created_at,
            result=result,
            error=None,
        )

    def fail(self, job_id: str, *, error: str) -> None:
        job = self.jobs[job_id]
        self.jobs[job_id] = JobRecord(
            job_id=job.job_id,
            status="failed",
            session_id=job.session_id,
            turn_type=job.turn_type,
            created_at=job.created_at,
            result=None,
            error=error,
        )

    def _enqueue(self, *, session_id: str, turn_type: SessionTurnType) -> str:
        job_id = f"job_{uuid4().hex}"
        self.jobs[job_id] = JobRecord(
            job_id=job_id,
            status="queued",
            session_id=session_id,
            turn_type=turn_type,
            created_at=utc_now(),
        )
        return job_id
