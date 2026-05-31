from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import boto3
import psycopg
from botocore.exceptions import ClientError

from packages.core.schemas import AnnotatedSequence, Plasmid
from packages.data_pipeline.ingest.genbank import env, load_dotenv
from packages.data_pipeline.parse.sequence_parser import parse_genbank_text
from packages.retrieval.document_composer import ComposedDocument, compose_plasmid_document
from packages.retrieval.embedder import (
    PHASE1_MODEL_NAME,
    PHASE1_MODEL_REVISION,
    Embedder,
    FakeEmbedder,
    TransformersEmbedder,
)
from packages.retrieval.vector_store import EmbeddingRecord, PgVectorStore, UpsertResult


DEFAULT_BATCH_SIZE = 32


class PlasmidRepository(Protocol):
    def list_plasmids(self, *, limit: int | None = None) -> list[Plasmid]: ...


class TextObjectStore(Protocol):
    def get_text(self, key: str) -> str | None: ...


class VectorIndex(Protocol):
    model_name: str
    dimension: int

    def ensure_schema(self) -> None: ...

    def filter_changed(self, documents: dict[str, str]) -> set[str]: ...

    def upsert(self, records: list[EmbeddingRecord]) -> UpsertResult: ...


@dataclass(frozen=True)
class EmbedCorpusConfig:
    database_url: str = "postgresql://plasmid:plasmid@localhost:5432/plasmid_design"
    object_store_endpoint: str = "http://localhost:9000"
    object_store_bucket: str = "plasmid-design-local"
    object_store_access_key: str = "minioadmin"
    object_store_secret_key: str = "minioadmin"
    batch_size: int = DEFAULT_BATCH_SIZE
    limit: int | None = None
    use_fake: bool = False
    local_files_only: bool = False
    hf_cache_dir: str | None = None
    model_name: str = PHASE1_MODEL_NAME
    model_revision: str = PHASE1_MODEL_REVISION

    @classmethod
    def from_env(
        cls,
        *,
        batch_size: int,
        limit: int | None,
        use_fake: bool,
        local_files_only: bool,
        hf_cache_dir: str | None,
    ) -> EmbedCorpusConfig:
        dotenv = load_dotenv(Path(".env"))
        return cls(
            database_url=env("DATABASE_URL", cls.database_url, dotenv),
            object_store_endpoint=env("OBJECT_STORE_ENDPOINT", cls.object_store_endpoint, dotenv),
            object_store_bucket=env("OBJECT_STORE_BUCKET", cls.object_store_bucket, dotenv),
            object_store_access_key=env("OBJECT_STORE_ACCESS_KEY", cls.object_store_access_key, dotenv),
            object_store_secret_key=env("OBJECT_STORE_SECRET_KEY", cls.object_store_secret_key, dotenv),
            batch_size=batch_size,
            limit=limit,
            use_fake=use_fake or env("EMBEDDING_FAKE", "false", dotenv).lower() == "true",
            local_files_only=local_files_only or env("EMBEDDING_LOCAL_FILES_ONLY", "false", dotenv).lower() == "true",
            hf_cache_dir=hf_cache_dir or env("EMBEDDING_HF_CACHE_DIR", "", dotenv) or None,
            model_name=env("EMBEDDING_MODEL_NAME", PHASE1_MODEL_NAME, dotenv) or PHASE1_MODEL_NAME,
            model_revision=env("EMBEDDING_MODEL_REVISION", PHASE1_MODEL_REVISION, dotenv) or PHASE1_MODEL_REVISION,
        )


@dataclass
class EmbedCorpusReport:
    total_plasmids: int = 0
    attempted_embeddings: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    annotated_from_cache: int = 0
    missing_cache: int = 0
    parse_failures: int = 0
    errors: list[dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_plasmids": self.total_plasmids,
            "attempted_embeddings": self.attempted_embeddings,
            "inserted": self.inserted,
            "updated": self.updated,
            "skipped": self.skipped,
            "annotated_from_cache": self.annotated_from_cache,
            "missing_cache": self.missing_cache,
            "parse_failures": self.parse_failures,
            "errors": self.errors,
        }


class PostgresPlasmidRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def list_plasmids(self, *, limit: int | None = None) -> list[Plasmid]:
        sql = "SELECT payload FROM plasmids ORDER BY id"
        params: tuple[object, ...] = ()
        if limit is not None:
            sql += " LIMIT %s"
            params = (limit,)
        with psycopg.connect(self.database_url) as connection:
            rows = connection.execute(sql, params).fetchall()
        return [Plasmid.model_validate(row[0]) for row in rows]


class S3TextObjectStore:
    def __init__(self, config: EmbedCorpusConfig) -> None:
        self.bucket = config.object_store_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=config.object_store_endpoint,
            aws_access_key_id=config.object_store_access_key,
            aws_secret_access_key=config.object_store_secret_key,
            region_name="us-east-1",
        )

    def get_text(self, key: str) -> str | None:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise
        return response["Body"].read().decode("utf-8")


def build_embedder(config: EmbedCorpusConfig) -> Embedder:
    if config.use_fake:
        return FakeEmbedder()
    return TransformersEmbedder(
        model_name=config.model_name,
        revision=config.model_revision,
        cache_dir=config.hf_cache_dir,
        local_files_only=config.local_files_only,
    )


def build_vector_store(config: EmbedCorpusConfig, embedder: Embedder) -> PgVectorStore:
    return PgVectorStore(
        lambda: psycopg.connect(config.database_url),
        model_name=embedder.model_name,
        dimension=embedder.dim,
    )


def embed_corpus(
    repository: PlasmidRepository,
    object_store: TextObjectStore,
    vector_index: VectorIndex,
    embedder: Embedder,
    *,
    limit: int | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> EmbedCorpusReport:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    vector_index.ensure_schema()
    plasmids = repository.list_plasmids(limit=limit)
    report = EmbedCorpusReport(total_plasmids=len(plasmids))

    for start in range(0, len(plasmids), batch_size):
        batch = plasmids[start : start + batch_size]
        composed: list[tuple[Plasmid, ComposedDocument]] = []
        for plasmid in batch:
            annotated_sequence = _load_annotation(plasmid, object_store, report)
            composed.append((plasmid, compose_plasmid_document(plasmid, annotated_sequence)))

        changed_ids = vector_index.filter_changed({plasmid.id: item.text for plasmid, item in composed})
        pending = [(plasmid, item) for plasmid, item in composed if plasmid.id in changed_ids]
        report.skipped += len(composed) - len(pending)
        report.attempted_embeddings += len(pending)
        vectors = embedder.embed([item.text for _, item in pending])
        records = [
            EmbeddingRecord(
                plasmid_id=plasmid.id,
                composed_document=document.text,
                embedding=vector,
                metadata=document.metadata,
            )
            for (plasmid, document), vector in zip(pending, vectors, strict=True)
        ]
        result = vector_index.upsert(records)
        report.inserted += result.inserted
        report.updated += result.updated
        report.skipped += result.skipped
        print(json.dumps({"batch": {"offset": start, "size": len(batch), "result": result.__dict__}}))
    return report


def _load_annotation(
    plasmid: Plasmid,
    object_store: TextObjectStore,
    report: EmbedCorpusReport,
) -> AnnotatedSequence | None:
    if not plasmid.raw_ref.endswith(".gb"):
        return None
    cached = object_store.get_text(plasmid.raw_ref)
    if cached is None:
        report.missing_cache += 1
        return None
    try:
        annotated = parse_genbank_text(cached)
    except Exception as exc:
        report.parse_failures += 1
        report.errors.append({"id": plasmid.id, "raw_ref": plasmid.raw_ref, "error": str(exc)})
        return None
    report.annotated_from_cache += 1
    return annotated


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compose and embed the current plasmid corpus into pgvector.")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--fake", action="store_true")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--hf-cache-dir")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = EmbedCorpusConfig.from_env(
        batch_size=args.batch_size,
        limit=args.limit,
        use_fake=args.fake,
        local_files_only=args.local_files_only,
        hf_cache_dir=args.hf_cache_dir,
    )
    embedder = build_embedder(config)
    vector_index = build_vector_store(config, embedder)
    report = embed_corpus(
        PostgresPlasmidRepository(config.database_url),
        S3TextObjectStore(config),
        vector_index,
        embedder,
        limit=config.limit,
        batch_size=config.batch_size,
    )
    print(json.dumps(report.as_dict(), indent=2))
    return 0 if not report.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
