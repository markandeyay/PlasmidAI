from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Mapping, Protocol


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


class GeminiModelClient(Protocol):
    def generate_content(self, *, model: str, contents: Any, config: Any) -> Any: ...


@dataclass
class GeminiJsonClient:
    api_key: str
    model: str = DEFAULT_GEMINI_MODEL
    sdk_client: Any | None = None

    @classmethod
    def from_env(cls) -> GeminiJsonClient:
        api_key = (os.environ.get("GOOGLE_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY is required for GeminiJsonClient")
        return cls(api_key=api_key)

    def generate_json(
        self,
        *,
        prompt: str,
        schema: Mapping[str, Any],
        system_instruction: str | None = None,
    ) -> str:
        client = self._client()
        config = self._build_config(schema=schema, system_instruction=system_instruction)
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text
        parsed = getattr(response, "parsed", None)
        if parsed is not None:
            return json.dumps(parsed)
        raise ValueError("Gemini client returned no structured JSON payload")

    def _client(self) -> Any:
        if self.sdk_client is not None:
            return self.sdk_client
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover - exercised only when dependency is missing
            raise RuntimeError("google-genai is required for GeminiJsonClient") from exc
        self.sdk_client = genai.Client(api_key=self.api_key)
        return self.sdk_client

    def _build_config(self, *, schema: Mapping[str, Any], system_instruction: str | None) -> Any:
        try:
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - exercised only when dependency is missing
            raise RuntimeError("google-genai is required for GeminiJsonClient") from exc
        return types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_json_schema=dict(schema),
            system_instruction=system_instruction,
        )


@dataclass(frozen=True)
class GeminiIntentClient:
    client: GeminiJsonClient

    def __call__(self, messages: list[dict[str, str]], schema: Mapping[str, Any]) -> str:
        return self.client.generate_json(prompt=_render_messages(messages), schema=schema)


@dataclass(frozen=True)
class GeminiRecommendationClient:
    client: GeminiJsonClient

    def complete_json(self, *, system_prompt: str, user_prompt: str, schema: Mapping[str, Any]) -> str:
        return self.client.generate_json(
            prompt=user_prompt,
            schema=schema,
            system_instruction=system_prompt,
        )


def _render_messages(messages: list[dict[str, str]]) -> str:
    parts: list[str] = []
    for message in messages:
        role = str(message.get("role", "user")).strip() or "user"
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        parts.append(f"{role.upper()}:\n{content}")
    return "\n\n".join(parts)
