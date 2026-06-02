from __future__ import annotations

"""FastAPI application scaffold for session-driven design workflows."""

from pydantic import BaseModel, ConfigDict, Field

from fastapi import FastAPI, HTTPException, status

from packages.application import (
    InMemoryJobQueue,
    InMemorySessionStore,
    JobQueue,
    SessionJobResult,
    SessionStore,
)


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
    result: SessionJobResult | None = None
    error: str | None = None


def create_app(
    *,
    session_store: SessionStore | None = None,
    job_queue: JobQueue | None = None,
) -> FastAPI:
    """Build the FastAPI app with injectable collaborators for tests."""

    store = session_store or InMemorySessionStore()
    queue = job_queue or InMemoryJobQueue()

    app = FastAPI(title="PMR API", version="0.1.0")
    app.state.session_store = store
    app.state.job_queue = queue

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
        session = store.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
        job_id = queue.enqueue_design(session=session, goal=request.goal)
        store.add_turn(session_id, turn_type="design", user_text=request.goal, job_id=job_id)
        return JobAcceptedResponse(job_id=job_id)

    @app.post(
        "/v1/sessions/{session_id}/refine",
        response_model=JobAcceptedResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def refine_session(session_id: str, request: RefineRequest) -> JobAcceptedResponse:
        """Queue a refinement job for the session without blocking on model work."""

        # TODO: enforce bearer auth, per-account rate limits, and usage metering.
        session = store.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
        job_id = queue.enqueue_refinement(session=session, instruction=request.instruction)
        store.add_turn(session_id, turn_type="refine", user_text=request.instruction, job_id=job_id)
        return JobAcceptedResponse(job_id=job_id)

    @app.get("/v1/jobs/{job_id}", response_model=JobStatusResponse)
    def get_job(job_id: str) -> JobStatusResponse:
        """Poll async job state and any available result payload."""

        # TODO: enforce bearer auth, per-account rate limits, and usage metering.
        job = queue.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
        return JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            result=job.result,
            error=job.error,
        )

    return app
