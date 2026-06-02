from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient


def _load_create_app() -> Callable[..., Any]:
    try:
        from services.api.app import create_app
    except ImportError as exc:  # pragma: no cover - exercised only when app code is missing locally
        pytest.skip(f"services.api.app is not available in this checkout: {exc}")
    return create_app


class AttrDict(dict[str, Any]):
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


class SessionHandle(str):
    @property
    def session_id(self) -> str:
        return str(self)

    @property
    def id(self) -> str:
        return str(self)


class JobHandle(str):
    @property
    def job_id(self) -> str:
        return str(self)

    @property
    def id(self) -> str:
        return str(self)


@dataclass
class InMemorySessionStore:
    sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
    counter: int = 0

    def create_session(self) -> str:
        self.counter += 1
        session_id = SessionHandle(f"session-{self.counter}")
        self.sessions[str(session_id)] = AttrDict(session_id=str(session_id), turns=[])
        return session_id

    def get_session(self, session_id: str) -> dict[str, Any]:
        if session_id not in self.sessions:
            raise KeyError(session_id)
        return self.sessions[session_id]

    def append_turn(self, session_id: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        session = self.get_session(session_id)
        turn = self._normalize_turn(*args, **kwargs)
        session["turns"].append(turn)
        return turn

    def _normalize_turn(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        turn: dict[str, Any] = {}
        if args:
            if len(args) == 1 and isinstance(args[0], dict):
                turn.update(args[0])
            elif len(args) >= 2:
                turn["role"] = args[0]
                turn["content"] = args[1]
                if len(args) > 2:
                    turn["extra_args"] = list(args[2:])
        turn.update(kwargs)

        if "content" not in turn:
            for key in ("goal", "instruction", "message", "text", "prompt"):
                if key in turn:
                    turn["content"] = turn[key]
                    break

        if "role" not in turn:
            turn["role"] = turn.get("speaker", "user")

        return turn

    def __getattr__(self, name: str) -> Any:
        aliases = {
            "new_session": self.create_session,
            "start_session": self.create_session,
            "create": self.create_session,
            "create_or_get_session": self.create_session,
            "get": self.get_session,
            "load_session": self.get_session,
            "fetch_session": self.get_session,
            "require_session": self.get_session,
            "append_message": self.append_turn,
            "add_turn": self.append_turn,
            "record_turn": self.append_turn,
            "push_turn": self.append_turn,
            "add_message": self.append_turn,
        }
        if name in aliases:
            return aliases[name]
        raise AttributeError(name)


class SynchronousJobQueue:
    def __init__(self, session_store: InMemorySessionStore) -> None:
        self.session_store = session_store
        self.jobs: dict[str, dict[str, Any]] = {}
        self.counter = 0

    def submit(self, *args: Any, **kwargs: Any) -> str:
        return self._enqueue("submit", *args, **kwargs)

    def get_job(self, job_id: str) -> dict[str, Any]:
        if job_id not in self.jobs:
            raise KeyError(job_id)
        return self.jobs[job_id]

    def _enqueue(self, job_type: str, *args: Any, **kwargs: Any) -> str:
        session_id = self._extract_session_id(*args, **kwargs)
        if session_id not in self.session_store.sessions:
            raise KeyError(session_id)

        self.counter += 1
        job_id = JobHandle(f"job-{self.counter}")
        session = self.session_store.sessions[session_id]
        latest_turn = session["turns"][-1] if session["turns"] else None
        payload = self._extract_payload(job_type, *args, **kwargs)
        result = AttrDict(
            job_id=str(job_id),
            job_type=job_type,
            session_id=session_id,
            turn_count=len(session["turns"]),
            latest_turn=latest_turn,
            payload=payload,
            result_text=f"fake result for {job_type}",
        )
        self.jobs[str(job_id)] = AttrDict(job_id=str(job_id), status="completed", result=result)
        return job_id

    def _extract_session_id(self, *args: Any, **kwargs: Any) -> str:
        for key in ("session_id", "session", "id"):
            value = kwargs.get(key)
            if isinstance(value, str):
                return value

        for value in args:
            if isinstance(value, str) and value.startswith("session-"):
                return value
            if isinstance(value, dict):
                nested = value.get("session_id") or value.get("session")
                if isinstance(nested, str):
                    return nested

        raise KeyError("session_id")

    def _extract_payload(self, job_type: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {"job_type": job_type}
        payload.update({k: v for k, v in kwargs.items() if k not in {"session_id", "session", "id"}})
        if args:
            for value in args:
                if isinstance(value, dict):
                    payload.update(value)
                elif isinstance(value, str) and value not in payload.values():
                    payload.setdefault("text", value)
        for key in ("goal", "instruction", "message", "text", "prompt"):
            if key in payload:
                payload.setdefault("text", payload[key])
                break
        return payload

    def __getattr__(self, name: str) -> Any:
        aliases = {
            "get": self.get_job,
            "load_job": self.get_job,
            "fetch_job": self.get_job,
            "job": self.get_job,
            "result": self.get_job,
        }
        if name in aliases:
            return aliases[name]

        def _submit(*args: Any, **kwargs: Any) -> str:
            return self._enqueue(name, *args, **kwargs)

        return _submit


@pytest.fixture()
def api_client() -> tuple[TestClient, InMemorySessionStore, SynchronousJobQueue]:
    create_app = _load_create_app()
    session_store = InMemorySessionStore()
    job_queue = SynchronousJobQueue(session_store)
    app = create_app(session_store=session_store, job_queue=job_queue)
    return TestClient(app), session_store, job_queue


def test_create_session_returns_session_id(api_client: tuple[TestClient, InMemorySessionStore, SynchronousJobQueue]) -> None:
    client, _, _ = api_client

    response = client.post("/v1/sessions")

    assert response.status_code in {200, 201}
    body = response.json()
    assert body["session_id"]


def test_design_dispatches_job_and_poll_returns_synchronous_result(
    api_client: tuple[TestClient, InMemorySessionStore, SynchronousJobQueue],
) -> None:
    client, _, _ = api_client
    session_id = client.post("/v1/sessions").json()["session_id"]

    design_response = client.post(f"/v1/sessions/{session_id}/design", json={"goal": "build a GFP reporter"})

    assert design_response.status_code in {200, 202}
    design_body = design_response.json()
    assert design_body["job_id"]

    job_response = client.get(f"/v1/jobs/{design_body['job_id']}")

    assert job_response.status_code == 200
    job_body = job_response.json()
    assert job_body["status"]
    assert job_body["result"]["session_id"] == session_id
    assert job_body["result"]["turn_count"] == 1
    assert job_body["result"]["latest_turn"]["content"] == "build a GFP reporter"
    assert "fake result" in job_body["result"]["result_text"]


def test_refine_appends_a_turn_and_reruns_with_updated_session_context(
    api_client: tuple[TestClient, InMemorySessionStore, SynchronousJobQueue],
) -> None:
    client, _, _ = api_client
    session_id = client.post("/v1/sessions").json()["session_id"]

    first_job_id = client.post(f"/v1/sessions/{session_id}/design", json={"goal": "build a GFP reporter"}).json()[
        "job_id"
    ]
    first_job = client.get(f"/v1/jobs/{first_job_id}").json()

    second_job_id = client.post(
        f"/v1/sessions/{session_id}/refine",
        json={"instruction": "switch the backbone to pLenti-CMV"},
    ).json()["job_id"]
    second_job = client.get(f"/v1/jobs/{second_job_id}").json()

    assert first_job["result"]["turn_count"] == 1
    assert second_job["result"]["turn_count"] == 2
    assert second_job["result"]["latest_turn"]["content"] == "switch the backbone to pLenti-CMV"
    assert second_job["result"]["turn_count"] > first_job["result"]["turn_count"]


@pytest.mark.parametrize(
    "path,payload",
    [
        ("/v1/sessions/{session_id}/design", {}),
        ("/v1/sessions/{session_id}/design", {"goal": []}),
        ("/v1/sessions/{session_id}/refine", {}),
        ("/v1/sessions/{session_id}/refine", {"instruction": []}),
    ],
)
def test_missing_or_malformed_fields_return_422(
    api_client: tuple[TestClient, InMemorySessionStore, SynchronousJobQueue],
    path: str,
    payload: dict[str, Any],
) -> None:
    client, _, _ = api_client
    session_id = client.post("/v1/sessions").json()["session_id"]

    response = client.post(path.format(session_id=session_id), json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize("path", ["/v1/sessions/does-not-exist/design", "/v1/sessions/does-not-exist/refine"])
def test_invalid_session_returns_404(
    api_client: tuple[TestClient, InMemorySessionStore, SynchronousJobQueue],
    path: str,
) -> None:
    client, _, _ = api_client

    payload = {"goal": "irrelevant"} if path.endswith("/design") else {"instruction": "irrelevant"}
    response = client.post(path, json=payload)

    assert response.status_code == 404


def test_missing_job_returns_404(api_client: tuple[TestClient, InMemorySessionStore, SynchronousJobQueue]) -> None:
    client, _, _ = api_client

    response = client.get("/v1/jobs/does-not-exist")

    assert response.status_code == 404
