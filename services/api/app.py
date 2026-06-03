from __future__ import annotations

"""FastAPI application scaffold for session-driven design workflows."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from fastapi import FastAPI, HTTPException, Response, status

from packages.application import (
    InMemoryJobQueue,
    InMemorySessionStore,
    JobQueue,
    SessionJobResult,
    SessionStore,
)
from packages.application.designs import DesignStore, InMemoryDesignStore
from packages.application.exports import export_annotated_sequence


class ApiModel(BaseModel):
    """Base model for API-layer envelopes."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )


class CreateSessionResponse(ApiModel):
    """Response returned when a session is created."""

    session_id: str = Field(min_length=1)


class DesignRequest(ApiModel):
    """Initial free-text design request."""

    goal: str = Field(min_length=1)


class RefineRequest(ApiModel):
    """Follow-up refinement instruction."""

    instruction: str = Field(min_length=1)


class JobAcceptedResponse(ApiModel):
    """Async job handle returned from design/refinement requests."""

    job_id: str = Field(min_length=1)


class JobStatusResponse(ApiModel):
    """Status payload returned when polling an async job."""

    job_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    result: SessionJobResult | dict[str, Any] | None = None
    error: str | None = None


def create_app(
    *,
    session_store: SessionStore | None = None,
    job_queue: Any | None = None,
    design_store: DesignStore | None = None,
) -> FastAPI:
    """Build the FastAPI app with injectable collaborators for tests."""

    store = session_store or InMemorySessionStore()
    queue = job_queue or InMemoryJobQueue()
    designs = design_store or InMemoryDesignStore()

    app = FastAPI(title="PMR API", version="0.1.0")
    app.state.session_store = store
    app.state.job_queue = queue
    app.state.design_store = designs

    @app.post(
        "/v1/sessions",
        response_model=CreateSessionResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_session() -> CreateSessionResponse:
        # TODO: enforce bearer auth, per-account rate limits, and usage metering.
        session = store.create_session()
        return CreateSessionResponse(session_id=session.session_id)

    @app.post(
        "/v1/sessions/{session_id}/design",
        response_model=JobAcceptedResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def design_session(session_id: str, request: DesignRequest) -> JobAcceptedResponse:
        """Queue a design job for the session without blocking on model work."""

        # TODO: enforce bearer auth, per-account rate limits, and usage metering.
        session = _get_session(store, session_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
        turn = _add_turn(store, session_id=session_id, action="design", text=request.goal)
        job_id = _enqueue(queue, session=store.get_session(session_id) or session, action="design", text=request.goal)
        _attach_job_id(store, session_id=session_id, turn=turn, job_id=job_id)
        return JobAcceptedResponse(job_id=job_id)

    @app.post(
        "/v1/sessions/{session_id}/refine",
        response_model=JobAcceptedResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def refine_session(session_id: str, request: RefineRequest) -> JobAcceptedResponse:
        """Queue a refinement job for the session without blocking on model work."""

        # TODO: enforce bearer auth, per-account rate limits, and usage metering.
        session = _get_session(store, session_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
        turn = _add_turn(store, session_id=session_id, action="refine", text=request.instruction)
        job_id = _enqueue(queue, session=store.get_session(session_id) or session, action="refine", text=request.instruction)
        _attach_job_id(store, session_id=session_id, turn=turn, job_id=job_id)
        return JobAcceptedResponse(job_id=job_id)

    @app.get("/v1/jobs/{job_id}", response_model=JobStatusResponse)
    def get_job(job_id: str) -> JobStatusResponse:
        """Poll async job state and any available result payload."""

        # TODO: enforce bearer auth, per-account rate limits, and usage metering.
        job = _get_job(queue, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
        return JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            result=job.result,
            error=getattr(job, "error", None),
        )

    @app.get("/v1/designs/{design_id}/export")
    def export_design(design_id: str, format: Literal["genbank", "fasta"]) -> Response:
        """Export a persisted annotated design as GenBank or FASTA."""

        # TODO: enforce bearer auth, per-account rate limits, and usage metering.
        design = designs.get(design_id)
        if design is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="design not found")
        payload = export_annotated_sequence(design.annotated_sequence, format=format)
        media_type = "text/plain" if format == "fasta" else "application/genbank"
        suffix = "fasta" if format == "fasta" else "gb"
        return Response(
            content=payload,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{design_id}.{suffix}"'},
        )

    return app


def _enqueue(queue: Any, *, session: Any, action: str, text: str) -> str:
    if hasattr(queue, "enqueue"):
        context = [turn.user_text if hasattr(turn, "user_text") else turn.get("content", "") for turn in session.turns]
        record = queue.enqueue(
            session_id=session.session_id,
            action=action,
            payload={action: text, "text": text, "context": context},
        )
        return getattr(record, "job_id", str(record))
    if action == "design" and hasattr(queue, "enqueue_design"):
        return queue.enqueue_design(session=session, goal=text)
    if action == "refine" and hasattr(queue, "enqueue_refinement"):
        return queue.enqueue_refinement(session=session, instruction=text)
    submit = getattr(queue, "submit")
    return submit(session_id=session.session_id, action=action, text=text)


def _get_job(queue: Any, job_id: str) -> Any | None:
    try:
        if hasattr(queue, "get_job"):
            return queue.get_job(job_id)
        return queue.store.get(job_id)
    except KeyError:
        return None


def _get_session(store: Any, session_id: str) -> Any | None:
    try:
        return store.get_session(session_id)
    except KeyError:
        return None


def _add_turn(store: Any, *, session_id: str, action: str, text: str) -> Any:
    turn = store.add_turn(session_id, turn_type=action, user_text=text)
    if isinstance(turn, dict):
        turn.setdefault("role", "user")
        turn.setdefault("content", text)
    return turn


def _attach_job_id(store: Any, *, session_id: str, turn: Any, job_id: str) -> None:
    if isinstance(turn, dict):
        turn["job_id"] = job_id
        return
    setter = getattr(store, "set_turn_job_id", None)
    if callable(setter):
        setter(session_id, turn_id=turn.turn_id, job_id=job_id)


app = create_app()
