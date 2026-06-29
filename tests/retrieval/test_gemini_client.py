from __future__ import annotations

import json
from types import SimpleNamespace

from packages.retrieval.gemini_client import GeminiJsonClient, GeminiRecommendationClient


class FakeModels:
    def __init__(self, response) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def generate_content(self, *, model: str, contents: object, config: object) -> object:
        self.calls.append({"model": model, "contents": contents, "config": config})
        return self.response


def test_gemini_json_client_uses_injected_sdk_text_response(monkeypatch) -> None:
    models = FakeModels(SimpleNamespace(text='{"ok": true}', parsed=None))
    sdk_client = SimpleNamespace(models=models)
    monkeypatch.setattr(
        GeminiJsonClient,
        "_build_config",
        lambda self, *, schema, system_instruction: {
            "schema": schema,
            "system_instruction": system_instruction,
        },
    )

    payload = GeminiJsonClient(api_key="test-key", sdk_client=sdk_client).generate_json(
        prompt="hello",
        schema={"type": "object"},
        system_instruction="system",
    )

    assert json.loads(payload) == {"ok": True}
    assert models.calls[0]["model"] == "gemini-2.5-flash"
    assert models.calls[0]["contents"] == "hello"


def test_gemini_recommendation_client_falls_back_to_parsed_payload(monkeypatch) -> None:
    models = FakeModels(SimpleNamespace(text=None, parsed={"recommendations": []}))
    sdk_client = SimpleNamespace(models=models)
    monkeypatch.setattr(
        GeminiJsonClient,
        "_build_config",
        lambda self, *, schema, system_instruction: {
            "schema": schema,
            "system_instruction": system_instruction,
        },
    )

    client = GeminiRecommendationClient(GeminiJsonClient(api_key="test-key", sdk_client=sdk_client))
    payload = client.complete_json(system_prompt="grounding", user_prompt="{}", schema={"type": "object"})

    assert json.loads(payload) == {"recommendations": []}
    assert models.calls[0]["config"]["system_instruction"] == "grounding"
