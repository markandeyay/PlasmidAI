from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

import boto3
import psycopg
from botocore.exceptions import ClientError
from psycopg.types.json import Jsonb

from packages.core.schemas import Plasmid
from packages.data_pipeline.ingest.genbank import (
    EntrezNcbiClient,
    GenbankIngestionConfig,
    GenbankIngestionError,
    env,
    load_dotenv,
    map_genbank_text_to_plasmid,
)


DEFAULT_STALE_DAYS = 60
DEFAULT_BATCH_SIZE = 100
DEFAULT_OUTPUT_DIR = Path("data/eval/corpus_refresh")
COMPARE_FIELDS = (
    "name",
    "sequence",
    "length",
    "organism",
    "vector_type",
    "markers",
    "promoters",
    "publication_doi",
    "use_cases",
)


class RefreshError(Exception):
    pass


class TextObjectStore(Protocol):
    def get_text(self, key: str) -> str: ...

    def put_text(self, key: str, payload: str) -> None: ...


class NcbiFetchClient(Protocol):
    def fetch_genbank(self, accession: str) -> str: ...


class RefreshDatabase(Protocol):
    def list_stale_genbank_records(self, config: CorpusRefreshConfig, *, stale_before: datetime) -> list[Plasmid]: ...

    def upsert_plasmid(self, plasmid: Plasmid) -> None: ...


@dataclass(frozen=True)
class CorpusRefreshConfig:
    stale_after: timedelta = timedelta(days=DEFAULT_STALE_DAYS)
    limit: int | None = None
    batch_size: int = DEFAULT_BATCH_SIZE
    database_url: str = "postgresql://plasmid:plasmid@localhost:5432/plasmid_design"
    object_store_endpoint: str = "http://localhost:9000"
    object_store_bucket: str = "plasmid-design-local"
    object_store_access_key: str = "minioadmin"
    object_store_secret_key: str = "minioadmin"
    output_dir: Path = DEFAULT_OUTPUT_DIR
    genbank: GenbankIngestionConfig = field(default_factory=lambda: GenbankIngestionConfig(mode="refresh"))

    @classmethod
    def from_env(cls, *, stale_days: int, limit: int | None, batch_size: int, output_dir: Path) -> CorpusRefreshConfig:
        dotenv = load_dotenv(Path(".env"))
        genbank = GenbankIngestionConfig.from_env(mode="refresh", limit=limit, stale_days=stale_days)
        return cls(
            stale_after=timedelta(days=stale_days),
            limit=limit,
            batch_size=batch_size,
            database_url=env("DATABASE_URL", cls.database_url, dotenv),
            object_store_endpoint=env("OBJECT_STORE_ENDPOINT", cls.object_store_endpoint, dotenv),
            object_store_bucket=env("OBJECT_STORE_BUCKET", cls.object_store_bucket, dotenv),
            object_store_access_key=env("OBJECT_STORE_ACCESS_KEY", cls.object_store_access_key, dotenv),
            object_store_secret_key=env("OBJECT_STORE_SECRET_KEY", cls.object_store_secret_key, dotenv),
            output_dir=output_dir,
            genbank=genbank,
        )

    def validate(self) -> None:
        if self.stale_after <= timedelta(0):
            raise RefreshError("stale-days must be positive")
        if self.batch_size <= 0:
            raise RefreshError("batch size must be positive")


@dataclass
class CorpusRefreshReport:
    started_at: datetime
    stale_before: datetime
    records_examined: int = 0
    records_refetched: int = 0
    records_unchanged: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    changes: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self, *, finished_at: datetime | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "started_at": self.started_at.astimezone(UTC).isoformat(),
            "stale_before": self.stale_before.astimezone(UTC).isoformat(),
            "records_examined": self.records_examined,
            "records_refetched": self.records_refetched,
            "records_unchanged": self.records_unchanged,
            "records_updated": self.records_updated,
            "records_skipped": self.records_skipped,
            "errors": self.errors,
            "changes": self.changes,
        }
        if finished_at is not None:
            payload["finished_at"] = finished_at.astimezone(UTC).isoformat()
        return payload


class S3TextObjectStore:
    def __init__(self, config: CorpusRefreshConfig) -> None:
        self.bucket = config.object_store_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=config.object_store_endpoint,
            aws_access_key_id=config.object_store_access_key,
            aws_secret_access_key=config.object_store_secret_key,
            region_name="us-east-1",
        )

    def get_text(self, key: str) -> str:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read().decode("utf-8")

    def put_text(self, key: str, payload: str) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=payload.encode("utf-8"),
            ContentType="chemical/seq-na-genbank",
        )


class PostgresRefreshDatabase:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def list_stale_genbank_records(self, config: CorpusRefreshConfig, *, stale_before: datetime) -> list[Plasmid]:
        limit_clause = "LIMIT %s" if config.limit is not None else ""
        params: tuple[Any, ...] = (stale_before, config.limit) if config.limit is not None else (stale_before,)
        with psycopg.connect(self.database_url) as connection:
            rows = connection.execute(
                f"""
                SELECT payload
                FROM plasmids
                WHERE source = 'genbank' AND updated_at < %s
                ORDER BY updated_at ASC, id ASC
                {limit_clause}
                """,
                params,
            ).fetchall()
        return [Plasmid.model_validate(row[0]) for row in rows]

    def upsert_plasmid(self, plasmid: Plasmid) -> None:
        payload = plasmid.model_dump(mode="json")
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                """
                UPDATE plasmids
                SET name = %(name)s,
                    sequence = %(sequence)s,
                    length = %(length)s,
                    organism = %(organism)s,
                    vector_type = %(vector_type)s,
                    markers = %(markers)s,
                    promoters = %(promoters)s,
                    publication_doi = %(publication_doi)s,
                    use_cases = %(use_cases)s,
                    updated_at = %(updated_at)s,
                    payload = %(payload)s
                WHERE id = %(id)s
                """,
                {
                    **payload,
                    "markers": Jsonb(payload["markers"]),
                    "promoters": Jsonb(payload["promoters"]),
                    "use_cases": Jsonb(payload["use_cases"]),
                    "payload": Jsonb(payload),
                },
            )


def run_corpus_refresh(
    config: CorpusRefreshConfig,
    *,
    database: RefreshDatabase,
    object_store: TextObjectStore,
    client: NcbiFetchClient,
    started_at: datetime | None = None,
) -> CorpusRefreshReport:
    config.validate()
    started = started_at or datetime.now(UTC)
    stale_before = started - config.stale_after
    report = CorpusRefreshReport(started_at=started, stale_before=stale_before)

    for existing in database.list_stale_genbank_records(config, stale_before=stale_before):
        report.records_examined += 1
        try:
            accession = accession_from_plasmid(existing)
            cached_raw = object_store.get_text(existing.raw_ref)
            fetched_raw = client.fetch_genbank(accession)
            report.records_refetched += 1

            if fetched_raw == cached_raw:
                refreshed = existing.model_copy(update={"updated_at": datetime.now(UTC)})
                database.upsert_plasmid(refreshed)
                object_store.put_text(existing.raw_ref, fetched_raw)
                report.records_unchanged += 1
                continue

            mapped = map_genbank_text_to_plasmid(fetched_raw, raw_ref=existing.raw_ref)
            updated = existing.model_copy(
                update={
                    "name": mapped.name,
                    "sequence": mapped.sequence,
                    "length": mapped.length,
                    "organism": mapped.organism,
                    "vector_type": mapped.vector_type,
                    "markers": mapped.markers,
                    "promoters": mapped.promoters,
                    "publication_doi": mapped.publication_doi,
                    "use_cases": mapped.use_cases,
                    "updated_at": datetime.now(UTC),
                }
            )
            changes = changed_fields(existing, updated)
            object_store.put_text(existing.raw_ref, fetched_raw)
            database.upsert_plasmid(updated)
            report.records_updated += 1
            report.changes.append({"id": existing.id, "accession": accession, "raw_ref": existing.raw_ref, "fields": changes})
        except (ClientError, GenbankIngestionError, RefreshError, KeyError) as exc:
            report.records_skipped += 1
            report.errors.append({"code": "refresh_error", "id": existing.id, "raw_ref": existing.raw_ref, "message": str(exc)})
        except Exception as exc:
            report.records_skipped += 1
            report.errors.append({"code": "unexpected_error", "id": existing.id, "raw_ref": existing.raw_ref, "message": str(exc)})
    return report


def accession_from_plasmid(plasmid: Plasmid) -> str:
    prefix = "genbank:"
    if plasmid.id.startswith(prefix) and len(plasmid.id) > len(prefix):
        return plasmid.id[len(prefix) :]
    raise RefreshError(f"cannot derive NCBI accession from plasmid id: {plasmid.id}")


def changed_fields(before: Plasmid, after: Plasmid) -> dict[str, dict[str, Any]]:
    return {
        field_name: {"before": getattr(before, field_name), "after": getattr(after, field_name)}
        for field_name in COMPARE_FIELDS
        if getattr(before, field_name) != getattr(after, field_name)
    }


def write_report(report: CorpusRefreshReport, output_dir: Path, *, finished_at: datetime | None = None) -> Path:
    finished = finished_at or datetime.now(UTC)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = finished.astimezone(UTC).strftime("%Y-%m-%d-%H%M%S")
    path = output_dir / f"{timestamp}-corpus-refresh.json"
    path.write_text(json.dumps(report.as_dict(finished_at=finished), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Refresh stale cached NCBI GenBank corpus records.")
    parser.add_argument("--stale-days", type=int, default=DEFAULT_STALE_DAYS)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = CorpusRefreshConfig.from_env(
        stale_days=args.stale_days,
        limit=args.limit,
        batch_size=args.batch_size,
        output_dir=args.output_dir,
    )
    try:
        config.genbank.validate_for_real_network()
        report = run_corpus_refresh(
            config,
            database=PostgresRefreshDatabase(config.database_url),
            object_store=S3TextObjectStore(config),
            client=EntrezNcbiClient(config.genbank),
        )
    except (GenbankIngestionError, RefreshError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 2
    finished_at = datetime.now(UTC)
    report_path = write_report(report, config.output_dir, finished_at=finished_at)
    print(json.dumps({"report": str(report_path), **report.as_dict(finished_at=finished_at)}, indent=2))
    return 0 if not report.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
