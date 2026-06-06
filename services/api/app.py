from __future__ import annotations

"""FastAPI application scaffold for session-driven design workflows."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from packages.application import (
    InMemoryJobQueue,
    InMemorySessionStore,
    JobQueue,
    SessionJobResult,
    SessionStore,
)
from packages.application.designs import DesignStore, InMemoryDesignStore
from packages.application.exports import export_annotated_sequence


MAX_PROMPT_LENGTH = 2_000
JOB_RETRY_AFTER_MS = 750


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

    goal: str = Field(min_length=1, max_length=MAX_PROMPT_LENGTH)

    @field_validator("goal")
    @classmethod
    def require_non_blank_goal(cls, value: str) -> str:
        return _require_non_blank(value)


class RefineRequest(ApiModel):
    """Follow-up refinement instruction."""

    instruction: str = Field(min_length=1, max_length=MAX_PROMPT_LENGTH)

    @field_validator("instruction")
    @classmethod
    def require_non_blank_instruction(cls, value: str) -> str:
        return _require_non_blank(value)


class ApiFieldError(ApiModel):
    """One frontend-renderable request validation issue."""

    field: str
    message: str
    type: str


class ApiErrorDetail(ApiModel):
    """Stable frontend-renderable error detail."""

    code: str
    message: str
    retryable: bool = False
    field_errors: list[ApiFieldError] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class ApiErrorResponse(ApiModel):
    """Standard API error envelope."""

    error: ApiErrorDetail


class JobAcceptedResponse(ApiModel):
    """Async job handle returned from design/refinement requests."""

    job_id: str = Field(min_length=1)


class JobStatusResponse(ApiModel):
    """Status payload returned when polling an async job."""

    job_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    result: SessionJobResult | dict[str, Any] | None = None
    error: str | None = None
    error_detail: ApiErrorDetail | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    retry_after_ms: int | None = None


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

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        del request
        detail = exc.detail
        if isinstance(detail, dict):
            code = str(detail.get("code") or _default_error_code(exc.status_code))
            message = str(detail.get("message") or detail.get("detail") or "Request failed.")
            retryable = bool(detail.get("retryable", False))
            details = {key: value for key, value in detail.items() if key not in {"code", "message", "detail", "retryable"}}
        else:
            code = _code_from_message(str(detail), exc.status_code)
            message = _friendly_message(str(detail), exc.status_code)
            retryable = False
            details = {}
        return _error_response(
            status_code=exc.status_code,
            code=code,
            message=message,
            retryable=retryable,
            details=details,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        del request
        field_errors = [
            ApiFieldError(
                field=".".join(str(part) for part in error.get("loc", []) if part != "body"),
                message=str(error.get("msg", "Invalid value.")),
                type=str(error.get("type", "value_error")),
            )
            for error in exc.errors()
        ]
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="validation_error",
            message="Please fix the highlighted fields and try again.",
            field_errors=field_errors,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        del request, exc
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="internal_error",
            message="The server hit an unexpected error while handling the request.",
            retryable=True,
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
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
            raise _http_error(status.HTTP_404_NOT_FOUND, "session_not_found", "Session not found.")
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
            raise _http_error(status.HTTP_404_NOT_FOUND, "session_not_found", "Session not found.")
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
            raise _http_error(status.HTTP_404_NOT_FOUND, "job_not_found", "Job not found.")
        job_status = str(job.status)
        error_text = getattr(job, "error", None)
        return JobStatusResponse(
            job_id=job.job_id,
            status=job_status,
            result=job.result,
            error=error_text,
            error_detail=_job_error_detail(error_text),
            created_at=getattr(job, "created_at", None),
            updated_at=getattr(job, "updated_at", None),
            retry_after_ms=JOB_RETRY_AFTER_MS if job_status.lower() in {"queued", "running"} else None,
        )

    @app.get("/v1/designs/{design_id}/export")
    def export_design(design_id: str, format: Literal["genbank", "fasta"]) -> Response:
        """Export a persisted annotated design as GenBank or FASTA."""

        # TODO: enforce bearer auth, per-account rate limits, and usage metering.
        design = designs.get(design_id)
        if design is None:
            raise _http_error(status.HTTP_404_NOT_FOUND, "design_not_found", "Design not found.")
        try:
            payload = export_annotated_sequence(design.annotated_sequence, format=format)
        except Exception as exc:
            raise _http_error(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "export_failed",
                "The design export could not be prepared.",
                retryable=True,
            ) from exc
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


def _require_non_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("Input must contain at least one non-whitespace character.")
    return value


def _http_error(status_code: int, code: str, message: str, *, retryable: bool = False) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message, "retryable": retryable},
    )


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    retryable: bool = False,
    field_errors: list[ApiFieldError] | None = None,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    payload = ApiErrorResponse(
        error=ApiErrorDetail(
            code=code,
            message=message,
            retryable=retryable,
            field_errors=field_errors or [],
            details=details or {},
        )
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def _default_error_code(status_code: int) -> str:
    if status_code == status.HTTP_404_NOT_FOUND:
        return "not_found"
    if status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        return "validation_error"
    return "request_failed"


def _code_from_message(message: str, status_code: int) -> str:
    normalized = message.lower().replace(" ", "_")
    if normalized in {"session_not_found", "job_not_found", "design_not_found"}:
        return normalized
    return _default_error_code(status_code)


def _friendly_message(message: str, status_code: int) -> str:
    normalized = message.lower()
    if normalized == "session not found":
        return "Session not found."
    if normalized == "job not found":
        return "Job not found."
    if normalized == "design not found":
        return "Design not found."
    if status_code >= 500:
        return "The server hit an unexpected error while handling the request."
    return message or "Request failed."


def _job_error_detail(error_text: str | None) -> ApiErrorDetail | None:
    if not error_text:
        return None
    return ApiErrorDetail(
        code="job_failed",
        message="The design job failed before producing a result.",
        retryable=True,
        details={"raw_error": error_text},
    )


app = create_app()
