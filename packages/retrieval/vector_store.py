from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Protocol, Sequence


DEFAULT_VECTOR_DIMENSION = 1536


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def compute_document_sha256(document: str) -> str:
    return hashlib.sha256(document.encode("utf-8")).hexdigest()


def _normalize_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    if metadata is None:
        return {}
    return dict(metadata)


def _validate_dimension(dimension: int) -> int:
    if not isinstance(dimension, int) or isinstance(dimension, bool) or dimension <= 0:
        raise ValueError("dimension must be a positive integer")
    return dimension


def _validate_vector(vector: Sequence[float], *, dimension: int) -> list[float]:
    values = [float(value) for value in vector]
    if len(values) != dimension:
        raise ValueError(f"expected vector of dimension {dimension}, got {len(values)}")
    return values


def _vector_literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(format(value, ".17g") for value in vector) + "]"


def _metadata_contains(candidate: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    for key, value in expected.items():
        if key not in candidate:
            return False
        current = candidate[key]
        if isinstance(value, Mapping) and isinstance(current, Mapping):
            if not _metadata_contains(current, value):
                return False
            continue
        if current != value:
            return False
    return True


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


@dataclass(frozen=True)
class EmbeddingRowState:
    document_sha256: str
    model_name: str
    embedding_dim: int


@dataclass(frozen=True)
class UpsertDecision:
    document_sha256: str
    should_skip: bool
    reason: str


@dataclass(frozen=True)
class EmbeddingRecord:
    plasmid_id: str
    composed_document: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VectorMatch:
    plasmid_id: str
    score: float
    metadata: dict[str, Any]
    document_sha256: str


@dataclass(frozen=True)
class UpsertResult:
    inserted: int
    updated: int
    skipped: int


def decide_embedding_upsert(
    existing: EmbeddingRowState | None,
    *,
    composed_document: str,
    model_name: str,
    embedding_dim: int,
) -> UpsertDecision:
    document_sha256 = compute_document_sha256(composed_document)
    if existing is None:
        return UpsertDecision(document_sha256=document_sha256, should_skip=False, reason="missing")
    if (
        existing.document_sha256 == document_sha256
        and existing.model_name == model_name
        and existing.embedding_dim == embedding_dim
    ):
        return UpsertDecision(document_sha256=document_sha256, should_skip=True, reason="unchanged")
    return UpsertDecision(document_sha256=document_sha256, should_skip=False, reason="changed")


class CursorLike(Protocol):
    def execute(self, query: str, params: Sequence[Any] | None = None) -> Any:
        ...

    def fetchone(self) -> Any:
        ...

    def fetchall(self) -> Any:
        ...

    def __enter__(self) -> CursorLike:
        ...

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        ...


class ConnectionLike(Protocol):
    def __enter__(self) -> ConnectionLike:
        ...

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        ...

    def cursor(self) -> CursorLike:
        ...

    def commit(self) -> None:
        ...


class VectorIndex(Protocol):
    dimension: int
    model_name: str

    def ensure_schema(self) -> None:
        ...

    def filter_changed(self, documents: Mapping[str, str]) -> set[str]:
        ...

    def upsert(self, records: Sequence[EmbeddingRecord]) -> UpsertResult:
        ...

    def query(
        self,
        query_vector: Sequence[float],
        *,
        limit: int = 10,
        metadata_filter: Mapping[str, Any] | None = None,
    ) -> list[VectorMatch]:
        ...


class PgVectorStore:
    def __init__(
        self,
        connection_factory: Callable[[], ConnectionLike],
        *,
        model_name: str,
        dimension: int = DEFAULT_VECTOR_DIMENSION,
        table_name: str = "plasmid_embeddings",
    ) -> None:
        self._connection_factory = connection_factory
        self.model_name = model_name
        self.dimension = _validate_dimension(dimension)
        self.table_name = table_name

    def ensure_schema(self) -> None:
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        plasmid_id TEXT PRIMARY KEY,
                        composed_document TEXT NOT NULL,
                        document_sha256 TEXT NOT NULL,
                        model_name TEXT NOT NULL,
                        embedding_dim INTEGER NOT NULL,
                        embedding VECTOR({self.dimension}) NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cursor.execute(
                    f"""
                    CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_hnsw_cosine_idx
                    ON {self.table_name}
                    USING hnsw (embedding vector_cosine_ops)
                    """
                )
            connection.commit()

    def upsert(self, records: Sequence[EmbeddingRecord]) -> UpsertResult:
        inserted = 0
        updated = 0
        skipped = 0
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                for record in records:
                    vector = _validate_vector(record.embedding, dimension=self.dimension)
                    existing = self._fetch_existing_state(cursor, record.plasmid_id)
                    decision = decide_embedding_upsert(
                        existing,
                        composed_document=record.composed_document,
                        model_name=self.model_name,
                        embedding_dim=self.dimension,
                    )
                    if decision.should_skip:
                        skipped += 1
                        continue
                    cursor.execute(
                        f"""
                        INSERT INTO {self.table_name} (
                            plasmid_id,
                            composed_document,
                            document_sha256,
                            model_name,
                            embedding_dim,
                            embedding,
                            metadata
                        )
                        VALUES (%s, %s, %s, %s, %s, %s::vector, %s::jsonb)
                        ON CONFLICT (plasmid_id) DO UPDATE SET
                            composed_document = EXCLUDED.composed_document,
                            document_sha256 = EXCLUDED.document_sha256,
                            model_name = EXCLUDED.model_name,
                            embedding_dim = EXCLUDED.embedding_dim,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata,
                            updated_at = CURRENT_TIMESTAMP
                        """
                        ,
                        (
                            record.plasmid_id,
                            record.composed_document,
                            decision.document_sha256,
                            self.model_name,
                            self.dimension,
                            _vector_literal(vector),
                            json.dumps(_normalize_metadata(record.metadata), sort_keys=True),
                        ),
                    )
                    if existing is None:
                        inserted += 1
                    else:
                        updated += 1
            connection.commit()
        return UpsertResult(inserted=inserted, updated=updated, skipped=skipped)

    def filter_changed(self, documents: Mapping[str, str]) -> set[str]:
        if not documents:
            return set()
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT plasmid_id, document_sha256, model_name, embedding_dim
                    FROM {self.table_name}
                    WHERE plasmid_id = ANY(%s)
                    """,
                    (list(documents),),
                )
                rows = cursor.fetchall()
        existing = {
            row[0]: EmbeddingRowState(
                document_sha256=row[1],
                model_name=row[2],
                embedding_dim=int(row[3]),
            )
            for row in rows
        }
        return {
            plasmid_id
            for plasmid_id, document in documents.items()
            if not decide_embedding_upsert(
                existing.get(plasmid_id),
                composed_document=document,
                model_name=self.model_name,
                embedding_dim=self.dimension,
            ).should_skip
        }

    def query(
        self,
        query_vector: Sequence[float],
        *,
        limit: int = 10,
        metadata_filter: Mapping[str, Any] | None = None,
    ) -> list[VectorMatch]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        vector = _validate_vector(query_vector, dimension=self.dimension)
        params: list[Any] = [
            _vector_literal(vector),
            self.model_name,
            self.dimension,
        ]
        filter_sql = ""
        if metadata_filter:
            filter_sql = " AND metadata @> %s::jsonb"
            params.append(json.dumps(_normalize_metadata(metadata_filter), sort_keys=True))
        order_params = list(params)
        order_params.append(params[0])
        order_params.append(limit)
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT
                        plasmid_id,
                        1 - (embedding <=> %s::vector) AS score,
                        metadata,
                        document_sha256
                    FROM {self.table_name}
                    WHERE model_name = %s
                      AND embedding_dim = %s
                      {filter_sql}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    tuple(order_params),
                )
                rows = cursor.fetchall()
        return [
            VectorMatch(
                plasmid_id=row[0],
                score=float(row[1]),
                metadata=dict(row[2] or {}),
                document_sha256=row[3],
            )
            for row in rows
        ]

    def _fetch_existing_state(self, cursor: CursorLike, plasmid_id: str) -> EmbeddingRowState | None:
        cursor.execute(
            f"""
            SELECT document_sha256, model_name, embedding_dim
            FROM {self.table_name}
            WHERE plasmid_id = %s
            """,
            (plasmid_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return EmbeddingRowState(
            document_sha256=row[0],
            model_name=row[1],
            embedding_dim=int(row[2]),
        )


class InMemoryVectorStore:
    def __init__(
        self,
        *,
        model_name: str,
        dimension: int = DEFAULT_VECTOR_DIMENSION,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.model_name = model_name
        self.dimension = _validate_dimension(dimension)
        self._clock = clock or self._deterministic_clock
        self._tick = 0
        self._rows: dict[str, dict[str, Any]] = {}
        self.schema_ready = False

    def ensure_schema(self) -> None:
        self.schema_ready = True

    def upsert(self, records: Sequence[EmbeddingRecord]) -> UpsertResult:
        inserted = 0
        updated = 0
        skipped = 0
        for record in records:
            vector = _validate_vector(record.embedding, dimension=self.dimension)
            existing = self._rows.get(record.plasmid_id)
            existing_state = None
            if existing is not None:
                existing_state = EmbeddingRowState(
                    document_sha256=existing["document_sha256"],
                    model_name=existing["model_name"],
                    embedding_dim=existing["embedding_dim"],
                )
            decision = decide_embedding_upsert(
                existing_state,
                composed_document=record.composed_document,
                model_name=self.model_name,
                embedding_dim=self.dimension,
            )
            if decision.should_skip:
                skipped += 1
                continue
            now = self._clock()
            created_at = existing["created_at"] if existing is not None else now
            self._rows[record.plasmid_id] = {
                "plasmid_id": record.plasmid_id,
                "composed_document": record.composed_document,
                "document_sha256": decision.document_sha256,
                "model_name": self.model_name,
                "embedding_dim": self.dimension,
                "embedding": vector,
                "metadata": _normalize_metadata(record.metadata),
                "created_at": created_at,
                "updated_at": now,
            }
            if existing is None:
                inserted += 1
            else:
                updated += 1
        return UpsertResult(inserted=inserted, updated=updated, skipped=skipped)

    def filter_changed(self, documents: Mapping[str, str]) -> set[str]:
        changed: set[str] = set()
        for plasmid_id, document in documents.items():
            row = self._rows.get(plasmid_id)
            existing = None
            if row is not None:
                existing = EmbeddingRowState(
                    document_sha256=row["document_sha256"],
                    model_name=row["model_name"],
                    embedding_dim=row["embedding_dim"],
                )
            if not decide_embedding_upsert(
                existing,
                composed_document=document,
                model_name=self.model_name,
                embedding_dim=self.dimension,
            ).should_skip:
                changed.add(plasmid_id)
        return changed

    def query(
        self,
        query_vector: Sequence[float],
        *,
        limit: int = 10,
        metadata_filter: Mapping[str, Any] | None = None,
    ) -> list[VectorMatch]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        vector = _validate_vector(query_vector, dimension=self.dimension)
        normalized_filter = _normalize_metadata(metadata_filter)
        matches: list[VectorMatch] = []
        for row in self._rows.values():
            if row["model_name"] != self.model_name or row["embedding_dim"] != self.dimension:
                continue
            if normalized_filter and not _metadata_contains(row["metadata"], normalized_filter):
                continue
            matches.append(
                VectorMatch(
                    plasmid_id=row["plasmid_id"],
                    score=_cosine_similarity(vector, row["embedding"]),
                    metadata=dict(row["metadata"]),
                    document_sha256=row["document_sha256"],
                )
            )
        matches.sort(key=lambda match: (-match.score, match.plasmid_id))
        return matches[:limit]

    def get_row(self, plasmid_id: str) -> dict[str, Any] | None:
        row = self._rows.get(plasmid_id)
        if row is None:
            return None
        return dict(row)

    def _deterministic_clock(self) -> datetime:
        value = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=self._tick)
        self._tick += 1
        return value
