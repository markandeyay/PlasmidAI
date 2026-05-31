from __future__ import annotations

import json

import pytest

from packages.retrieval.vector_store import (
    EmbeddingRecord,
    EmbeddingRowState,
    InMemoryVectorStore,
    PgVectorStore,
    compute_document_sha256,
    decide_embedding_upsert,
)


class RecordingCursor:
    def __init__(self, existing_rows: dict[str, tuple[str, str, int]] | None = None) -> None:
        self.existing_rows = existing_rows or {}
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []
        self._last_fetchone: tuple[str, str, int] | None = None
        self._fetchall_rows: list[tuple[object, ...]] = []

    def __enter__(self) -> RecordingCursor:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> None:
        normalized = " ".join(query.split())
        self.executed.append((normalized, params))
        if normalized.startswith("SELECT document_sha256, model_name, embedding_dim"):
            plasmid_id = params[0]
            self._last_fetchone = self.existing_rows.get(plasmid_id)
        elif normalized.startswith("INSERT INTO"):
            plasmid_id = params[0]
            self.existing_rows[plasmid_id] = (params[2], params[3], params[4])
        elif normalized.startswith("SELECT plasmid_id, 1 - (embedding <=>"):
            self._fetchall_rows = [
                ("p2", 0.92, {"source": "genbank"}, "sha-two"),
                ("p1", 0.81, {"source": "addgene"}, "sha-one"),
            ]

    def fetchone(self) -> tuple[str, str, int] | None:
        return self._last_fetchone

    def fetchall(self) -> list[tuple[object, ...]]:
        return list(self._fetchall_rows)


class RecordingConnection:
    def __init__(self, cursor: RecordingCursor) -> None:
        self._cursor = cursor
        self.commit_count = 0

    def __enter__(self) -> RecordingConnection:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def cursor(self) -> RecordingCursor:
        return self._cursor

    def commit(self) -> None:
        self.commit_count += 1


def test_decide_embedding_upsert_skips_only_when_hash_model_and_dimension_match() -> None:
    document = "CMV promoter GFP marker"
    existing = EmbeddingRowState(
        document_sha256=compute_document_sha256(document),
        model_name="test-model",
        embedding_dim=3,
    )

    decision = decide_embedding_upsert(
        existing,
        composed_document=document,
        model_name="test-model",
        embedding_dim=3,
    )

    assert decision.should_skip is True
    assert decision.reason == "unchanged"

    changed_model = decide_embedding_upsert(
        existing,
        composed_document=document,
        model_name="other-model",
        embedding_dim=3,
    )
    changed_dimension = decide_embedding_upsert(
        existing,
        composed_document=document,
        model_name="test-model",
        embedding_dim=4,
    )
    changed_document = decide_embedding_upsert(
        existing,
        composed_document=document + " v2",
        model_name="test-model",
        embedding_dim=3,
    )

    assert changed_model.should_skip is False
    assert changed_dimension.should_skip is False
    assert changed_document.should_skip is False


def test_in_memory_vector_store_is_deterministic_and_applies_metadata_filter() -> None:
    store = InMemoryVectorStore(model_name="test-model", dimension=3)
    store.ensure_schema()

    first = store.upsert(
        [
            EmbeddingRecord(
                plasmid_id="p1",
                composed_document="CMV GFP human expression",
                embedding=[1.0, 0.0, 0.0],
                metadata={"source": "addgene", "tags": {"host": "human"}},
            ),
            EmbeddingRecord(
                plasmid_id="p2",
                composed_document="AmpR bacterial backbone",
                embedding=[0.0, 1.0, 0.0],
                metadata={"source": "genbank", "tags": {"host": "bacteria"}},
            ),
        ]
    )
    second = store.upsert(
        [
            EmbeddingRecord(
                plasmid_id="p1",
                composed_document="CMV GFP human expression",
                embedding=[1.0, 0.0, 0.0],
                metadata={"source": "addgene", "tags": {"host": "human"}},
            )
        ]
    )
    third = store.upsert(
        [
            EmbeddingRecord(
                plasmid_id="p1",
                composed_document="CMV GFP inducible expression",
                embedding=[0.8, 0.2, 0.0],
                metadata={"source": "addgene", "tags": {"host": "human"}},
            )
        ]
    )

    assert first.inserted == 2
    assert first.updated == 0
    assert first.skipped == 0
    assert second.skipped == 1
    assert third.updated == 1

    row = store.get_row("p1")
    assert row is not None
    assert row["created_at"] < row["updated_at"]

    matches = store.query([1.0, 0.0, 0.0], metadata_filter={"source": "addgene"})
    assert [match.plasmid_id for match in matches] == ["p1"]
    assert matches[0].score == pytest.approx(0.9701425, rel=1e-6)

    nested = store.query([0.0, 1.0, 0.0], metadata_filter={"tags": {"host": "bacteria"}})
    assert [match.plasmid_id for match in nested] == ["p2"]


def test_pgvector_store_ensure_schema_and_upsert_emit_expected_sql() -> None:
    cursor = RecordingCursor()
    connection = RecordingConnection(cursor)
    store = PgVectorStore(lambda: connection, model_name="test-model", dimension=3)

    store.ensure_schema()
    result = store.upsert(
        [
            EmbeddingRecord(
                plasmid_id="p1",
                composed_document="CMV GFP human expression",
                embedding=[1.0, 0.0, 0.0],
                metadata={"source": "addgene"},
            )
        ]
    )

    assert connection.commit_count == 2
    assert result.inserted == 1
    assert result.updated == 0
    assert result.skipped == 0

    create_table_sql = cursor.executed[1][0]
    assert "CREATE TABLE IF NOT EXISTS plasmid_embeddings" in create_table_sql
    assert "embedding VECTOR(3) NOT NULL" in create_table_sql

    create_index_sql = cursor.executed[2][0]
    assert "USING hnsw (embedding vector_cosine_ops)" in create_index_sql

    insert_sql, insert_params = next(
        (query, params) for query, params in cursor.executed if query.startswith("INSERT INTO")
    )
    assert "%s::vector" in insert_sql
    assert insert_params[5] == "[1,0,0]"
    assert json.loads(insert_params[6]) == {"source": "addgene"}


def test_pgvector_store_skips_unchanged_and_queries_with_metadata_filter() -> None:
    existing_rows = {
        "p1": (
            compute_document_sha256("CMV GFP human expression"),
            "test-model",
            3,
        )
    }
    cursor = RecordingCursor(existing_rows=existing_rows)
    connection = RecordingConnection(cursor)
    store = PgVectorStore(lambda: connection, model_name="test-model", dimension=3)

    result = store.upsert(
        [
            EmbeddingRecord(
                plasmid_id="p1",
                composed_document="CMV GFP human expression",
                embedding=[1.0, 0.0, 0.0],
                metadata={"source": "addgene"},
            )
        ]
    )
    matches = store.query([1.0, 0.0, 0.0], limit=2, metadata_filter={"source": "genbank"})

    assert result.skipped == 1
    assert result.inserted == 0
    assert result.updated == 0
    assert [match.plasmid_id for match in matches] == ["p2", "p1"]

    query_sql, query_params = cursor.executed[-1]
    assert "metadata @> %s::jsonb" in query_sql
    assert query_params == ("[1,0,0]", "test-model", 3, '{"source": "genbank"}', "[1,0,0]", 2)
