from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import importlib

import pytest
from starlette.testclient import TestClient

from packages.application import InMemoryJobStore, InMemoryOutcomeStore, InMemorySessionStore
from packages.application.designs import InMemoryDesignStore
from packages.core.schemas import AnnotatedSequence
from packages.retrieval.gemini_client import GeminiIntentClient, GeminiRecommendationClient
from packages.retrieval.intent_parser import FakeIntentParser, LLMIntentParser
from packages.retrieval.recommender import LLMRecommendationGenerator, TemplateRecommendationGenerator


local_app = importlib.import_module("services.api.local_app")


def _annotated_sequence() -> AnnotatedSequence:
    return AnnotatedSequence(
        sequence="ACGT" * 12,
        topology="circular",
        vector_profile="bacterial_cloning_vector",
        annotation_complete=True,
        features=[],
    )


def test_load_env_defaults_only_fills_missing_values(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("GOOGLE_API_KEY=file-key\nDATABASE_URL=postgresql://from-dotenv\n", encoding="utf-8")
    monkeypatch.setenv("GOOGLE_API_KEY", "process-key")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    local_app._load_env_defaults(dotenv)

    assert local_app.os.environ["GOOGLE_API_KEY"] == "process-key"
    assert local_app.os.environ["DATABASE_URL"] == "postgresql://from-dotenv"


def test_build_application_stores_prefers_postgres_only_when_tables_exist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(local_app, "_tables_available", lambda database_url, tables, require_vector_extension=False: True)
    postgres = local_app._build_application_stores("postgresql://example")
    assert type(postgres["session_store"]).__name__ == "PostgresSessionStore"
    assert type(postgres["job_store"]).__name__ == "PostgresJobStore"

    monkeypatch.setattr(local_app, "_tables_available", lambda database_url, tables, require_vector_extension=False: False)
    memory = local_app._build_application_stores("postgresql://example")
    assert isinstance(memory["session_store"], InMemorySessionStore)
    assert isinstance(memory["job_store"], InMemoryJobStore)
    assert isinstance(memory["design_store"], InMemoryDesignStore)
    assert isinstance(memory["outcome_store"], InMemoryOutcomeStore)


def test_build_local_pipeline_selects_gemini_or_offline_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    config = local_app.EmbedCorpusConfig(database_url="postgresql://example", use_fake=False)
    monkeypatch.setattr(local_app, "build_embedder", lambda config: object())
    monkeypatch.setattr(local_app, "build_vector_store", lambda config, embedder: object())
    monkeypatch.setattr(local_app, "HybridRetriever", lambda **kwargs: kwargs)

    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    live = local_app._build_local_pipeline(config)
    assert isinstance(live.parser, LLMIntentParser)
    assert isinstance(live.parser._call_llm, GeminiIntentClient)
    assert isinstance(live.recommendation_generator, LLMRecommendationGenerator)
    assert isinstance(live.recommendation_generator.client, GeminiRecommendationClient)

    monkeypatch.setenv("GOOGLE_API_KEY", "")
    offline = local_app._build_local_pipeline(config)
    assert isinstance(offline.parser, FakeIntentParser)
    assert isinstance(offline.recommendation_generator, TemplateRecommendationGenerator)


def test_build_local_app_runs_design_synchronously(monkeypatch: pytest.MonkeyPatch) -> None:
    stores = {
        "session_store": InMemorySessionStore(),
        "job_store": InMemoryJobStore(),
        "design_store": InMemoryDesignStore(),
        "outcome_store": InMemoryOutcomeStore(),
    }
    pipeline = SimpleNamespace(run=lambda free_text: SimpleNamespace(reannotated_sequence=_annotated_sequence()))
    monkeypatch.setattr(local_app, "_load_env_defaults", lambda path: None)
    monkeypatch.setattr(local_app, "_assert_corpus_ready", lambda database_url: None)
    migration_calls: list[bool] = []
    monkeypatch.setattr(local_app, "_run_app_migrations", lambda: migration_calls.append(True))
    monkeypatch.setattr(local_app, "_build_application_stores", lambda database_url: stores)
    monkeypatch.setattr(local_app, "_build_local_pipeline", lambda config: pipeline)
    monkeypatch.setattr(
        local_app.EmbedCorpusConfig,
        "from_env",
        classmethod(
            lambda cls, **kwargs: cls(
                database_url="postgresql://example",
                use_fake=False,
                local_files_only=False,
                batch_size=1,
                limit=None,
                hf_cache_dir=None,
            )
        ),
    )
    monkeypatch.setattr(
        "packages.application.design_jobs.spike_result_as_dict",
        lambda result: {
            "design_spec": {"organism": "Escherichia coli", "vector_type": "bacterial_cloning_vector"},
            "annotated_sequence": result.reannotated_sequence.model_dump(mode="json"),
            "validation_report": {"overall": "PASS"},
            "retrieved_templates": [],
            "recommendations": [{"why_relevant": "Stored design is relevant."}],
        },
    )

    client = TestClient(local_app.build_local_app())
    session_id = client.post("/v1/sessions").json()["session_id"]

    accepted = client.post(f"/v1/sessions/{session_id}/design", json={"goal": "build a cloning vector"})
    job_id = accepted.json()["job_id"]
    polled = client.get(f"/v1/jobs/{job_id}")

    assert accepted.status_code == 202
    assert polled.status_code == 200
    result = polled.json()["result"]
    assert result["design_id"]
    assert result["recommendation_text"] == "Stored design is relevant."
    design = client.get(f"/v1/designs/{result['design_id']}").json()
    assert design["job_id"] == job_id
    assert design["annotated_sequence"]["vector_profile"] == "bacterial_cloning_vector"
    assert migration_calls == [True]
