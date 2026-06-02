from __future__ import annotations

import os
from typing import Any, Callable, Mapping

from packages.application.jobs import JobHandler, JobRecord, JobStore


DEFAULT_JOB_TASK_NAME = "pmr.jobs.run"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"


def build_celery_app(*, redis_url: str | None = None, celery_factory: Callable[..., Any] | None = None) -> Any:
    factory = celery_factory or _import_celery_factory()
    broker_url = redis_url or os.environ.get("REDIS_URL", DEFAULT_REDIS_URL)
    return factory(
        "pmr-worker",
        broker=broker_url,
        backend=broker_url,
        include=("services.worker.celery_app",),
    )


class CeleryJobQueue:
    def __init__(self, *, store: JobStore, celery_app: Any, task_name: str = DEFAULT_JOB_TASK_NAME) -> None:
        self.store = store
        self.celery_app = celery_app
        self.task_name = task_name

    def enqueue(self, *, session_id: str, action: str, payload: Mapping[str, Any]) -> JobRecord:
        record = self.store.create(session_id=session_id, action=action, payload=payload)
        self.celery_app.send_task(
            self.task_name,
            kwargs={
                "job_id": record.job_id,
                "session_id": session_id,
                "action": action,
                "payload": dict(payload),
            },
        )
        return record


def create_job_task(*, store: JobStore, handler: JobHandler) -> Callable[..., JobRecord]:
    def run_job(*, job_id: str, session_id: str, action: str, payload: Mapping[str, Any]) -> JobRecord:
        store.mark_running(job_id)
        try:
            result = handler(session_id=session_id, action=action, payload=payload)
        except Exception as exc:
            return store.mark_failed(job_id, error=str(exc))
        return store.mark_succeeded(job_id, result=result)

    return run_job


def register_job_task(
    celery_app: Any,
    *,
    store: JobStore,
    handler: JobHandler,
    task_name: str = DEFAULT_JOB_TASK_NAME,
) -> Callable[..., JobRecord]:
    task = create_job_task(store=store, handler=handler)
    decorator = getattr(celery_app, "task", None)
    if callable(decorator):
        return decorator(name=task_name)(task)
    return task


def _import_celery_factory() -> Callable[..., Any]:
    try:
        from celery import Celery
    except ImportError as exc:
        raise RuntimeError("Celery is not installed; worker queue adapter cannot build a Celery app") from exc
    return Celery
