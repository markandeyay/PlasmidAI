from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Protocol

import boto3
import psycopg
from botocore.exceptions import ClientError
from psycopg.types.json import Jsonb

from packages.core.schemas import Plasmid
from packages.data_pipeline.ingest.genbank import env, load_dotenv, map_genbank_text_to_plasmid
from packages.data_pipeline.parse.sequence_parser import parse_genbank_text


DEFAULT_OUTPUT_DIR = Path("data/eval/reprocess")
DEFAULT_BATCH_SIZE = 100
RELEVANT_FIELDS = (
    "sequence",
    "length",
    "organism",
    "vector_type",
    "markers",
    "promoters",
    "publication_doi",
    "annotation_complete",
    "raw_ref",
)
FILTER_PATTERN = re.compile(r"^markers\s+contains\s+['\"](?P<value>.+)['\"]$", flags=re.IGNORECASE)
FILTER_ALIASES = {"cat_in_replication": "replication"}


class ReprocessError(Exception):
    pass


class MissingCacheError(ReprocessError):
    pass


class TextObjectStore(Protocol):
    def get_text(self, key: str) -> str: ...


class ReprocessDatabase(Protocol):
    def ensure_schema(self) -> None: ...

    def start_run(self, config: ReprocessConfig, *, started_at: datetime) -> int: ...

    def list_candidates(self, config: ReprocessConfig) -> list[Plasmid]: ...

    def update_batch(self, updates: list[Plasmid]) -> None: ...

    def finish_run(self, run_id: int, report: ReprocessReport, *, finished_at: datetime, report_path: str) -> None: ...


@dataclass(frozen=True)
class ReprocessConfig:
    mode: str = "all"
    before: datetime | None = None
    source: str | None = None
    pattern: str | None = None
    batch_size: int = DEFAULT_BATCH_SIZE
    database_url: str = "postgresql://plasmid:plasmid@localhost:5432/plasmid_design"
    object_store_endpoint: str = "http://localhost:9000"
    object_store_bucket: str = "plasmid-design-local"
    object_store_access_key: str = "minioadmin"
    object_store_secret_key: str = "minioadmin"
    output_dir: Path = DEFAULT_OUTPUT_DIR

    @classmethod
    def from_env(
        cls,
        *,
        mode: str,
        before: datetime | None,
        source: str | None,
        pattern: str | None,
        batch_size: int,
        output_dir: Path,
    ) -> ReprocessConfig:
        dotenv = load_dotenv(Path(".env"))
        return cls(
            mode=mode,
            before=before,
            source=source,
            pattern=pattern,
            batch_size=batch_size,
            database_url=env("DATABASE_URL", cls.database_url, dotenv),
            object_store_endpoint=env("OBJECT_STORE_ENDPOINT", cls.object_store_endpoint, dotenv),
            object_store_bucket=env("OBJECT_STORE_BUCKET", cls.object_store_bucket, dotenv),
            object_store_access_key=env("OBJECT_STORE_ACCESS_KEY", cls.object_store_access_key, dotenv),
            object_store_secret_key=env("OBJECT_STORE_SECRET_KEY", cls.object_store_secret_key, dotenv),
            output_dir=output_dir,
        )

    def validate(self) -> None:
        if self.mode not in {"all", "stale", "source", "filter"}:
            raise ReprocessError(f"unsupported reprocess mode: {self.mode}")
        if self.mode == "stale" and self.before is None:
            raise ReprocessError("stale mode requires --before")
        if self.mode == "source" and self.source not in {"genbank", "curated"}:
            raise ReprocessError("source mode requires --source genbank or curated")
        if self.mode == "filter":
            parse_filter_pattern(self.pattern)
        if self.batch_size <= 0:
            raise ReprocessError("batch size must be positive")


@dataclass
class ReprocessReport:
    run_id: int
    mode: str
    started_at: datetime
    records_examined: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    records_missing_cache: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    changes: list[dict[str, Any]] = field(default_factory=list)
    batches: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self, *, finished_at: datetime | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "run_id": self.run_id,
            "mode": self.mode,
            "started_at": self.started_at.astimezone(UTC).isoformat(),
            "records_examined": self.records_examined,
            "records_updated": self.records_updated,
            "records_skipped": self.records_skipped,
            "records_missing_cache": self.records_missing_cache,
            "errors": self.errors,
            "changes": self.changes,
            "batches": self.batches,
        }
        if finished_at is not None:
            payload["finished_at"] = finished_at.astimezone(UTC).isoformat()
        return payload


class S3TextObjectStore:
    def __init__(self, config: ReprocessConfig) -> None:
        self.bucket = config.object_store_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=config.object_store_endpoint,
            aws_access_key_id=config.object_store_access_key,
            aws_secret_access_key=config.object_store_secret_key,
            region_name="us-east-1",
        )

    def get_text(self, key: str) -> str:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                raise MissingCacheError(f"cached blob is missing: {key}") from exc
            raise
        return response["Body"].read().decode("utf-8")


class PostgresReprocessDatabase:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def ensure_schema(self) -> None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reprocess_runs (
                    id BIGSERIAL PRIMARY KEY,
                    mode TEXT NOT NULL,
                    before_timestamp TIMESTAMPTZ,
                    source_filter TEXT,
                    pattern_filter TEXT,
                    batch_size INTEGER NOT NULL,
                    started_at TIMESTAMPTZ NOT NULL,
                    finished_at TIMESTAMPTZ,
                    records_examined INTEGER NOT NULL DEFAULT 0,
                    records_updated INTEGER NOT NULL DEFAULT 0,
                    records_skipped INTEGER NOT NULL DEFAULT 0,
                    records_missing_cache INTEGER NOT NULL DEFAULT 0,
                    errors JSONB NOT NULL DEFAULT '[]'::jsonb,
                    report_path TEXT
                )
                """
            )

    def start_run(self, config: ReprocessConfig, *, started_at: datetime) -> int:
        with psycopg.connect(self.database_url) as connection:
            row = connection.execute(
                """
                INSERT INTO reprocess_runs (
                    mode, before_timestamp, source_filter, pattern_filter, batch_size, started_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (config.mode, config.before, config.source, config.pattern, config.batch_size, started_at),
            ).fetchone()
        if row is None:
            raise ReprocessError("failed to create reprocess run")
        return int(row[0])

    def list_candidates(self, config: ReprocessConfig) -> list[Plasmid]:
        where, params = candidate_where(config)
        with psycopg.connect(self.database_url) as connection:
            rows = connection.execute(f"SELECT payload FROM plasmids {where} ORDER BY id", params).fetchall()
        return [Plasmid.model_validate(row[0]) for row in rows]

    def update_batch(self, updates: list[Plasmid]) -> None:
        if not updates:
            return
        now = datetime.now(UTC)
        with psycopg.connect(self.database_url) as connection:
            for plasmid in updates:
                updated = plasmid.model_copy(update={"updated_at": now})
                payload = updated.model_dump(mode="json")
                connection.execute(
                    """
                    UPDATE plasmids
                    SET sequence = %(sequence)s,
                        length = %(length)s,
                        organism = %(organism)s,
                        vector_type = %(vector_type)s,
                        markers = %(markers)s,
                        promoters = %(promoters)s,
                        publication_doi = %(publication_doi)s,
                        annotation_complete = %(annotation_complete)s,
                        raw_ref = %(raw_ref)s,
                        updated_at = %(updated_at)s,
                        payload = %(payload)s
                    WHERE id = %(id)s
                    """,
                    {
                        **payload,
                        "markers": Jsonb(payload["markers"]),
                        "promoters": Jsonb(payload["promoters"]),
                        "payload": Jsonb(payload),
                    },
                )

    def finish_run(self, run_id: int, report: ReprocessReport, *, finished_at: datetime, report_path: str) -> None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                """
                UPDATE reprocess_runs
                SET finished_at = %s,
                    records_examined = %s,
                    records_updated = %s,
                    records_skipped = %s,
                    records_missing_cache = %s,
                    errors = %s,
                    report_path = %s
                WHERE id = %s
                """,
                (
                    finished_at,
                    report.records_examined,
                    report.records_updated,
                    report.records_skipped,
                    report.records_missing_cache,
                    Jsonb(report.errors),
                    report_path,
                    run_id,
                ),
            )


def run_reprocessing(
    config: ReprocessConfig,
    *,
    database: ReprocessDatabase,
    object_store: TextObjectStore,
    started_at: datetime | None = None,
) -> ReprocessReport:
    config.validate()
    database.ensure_schema()
    started = started_at or datetime.now(UTC)
    run_id = database.start_run(config, started_at=started)
    report = ReprocessReport(run_id=run_id, mode=config.mode, started_at=started)
    candidates = database.list_candidates(config)

    for batch_number, batch in enumerate(batched(candidates, config.batch_size), start=1):
        updates: list[Plasmid] = []
        changes: list[dict[str, Any]] = []
        batch_missing_cache = 0
        batch_errors: list[dict[str, Any]] = []
        for existing in batch:
            report.records_examined += 1
            try:
                raw_text = object_store.get_text(existing.raw_ref)
                updated, profile = reprocess_plasmid(existing, raw_text)
                field_changes = changed_fields(existing, updated)
                if not field_changes:
                    report.records_skipped += 1
                    continue
                updates.append(updated)
                changes.append({"id": existing.id, "vector_profile": profile, "fields": field_changes})
            except MissingCacheError as exc:
                report.records_missing_cache += 1
                report.records_skipped += 1
                batch_missing_cache += 1
                batch_errors.append({"code": "missing_cache", "id": existing.id, "raw_ref": existing.raw_ref, "message": str(exc)})
            except Exception as exc:
                report.records_skipped += 1
                batch_errors.append({"code": "reprocess_error", "id": existing.id, "raw_ref": existing.raw_ref, "message": str(exc)})

        if updates:
            try:
                database.update_batch(updates)
            except Exception as exc:
                report.records_skipped += len(updates)
                batch_errors.append(
                    {
                        "code": "batch_rollback",
                        "batch": batch_number,
                        "record_ids": [plasmid.id for plasmid in updates],
                        "message": str(exc),
                    }
                )
                updates = []
                changes = []
        report.records_updated += len(updates)
        report.errors.extend(batch_errors)
        report.changes.extend(changes)
        batch_report = {
            "batch": batch_number,
            "records_examined": len(batch),
            "records_updated": len(updates),
            "records_missing_cache": batch_missing_cache,
            "errors": len(batch_errors),
        }
        report.batches.append(batch_report)
        print(json.dumps({"batch_progress": batch_report}))
    return report


def reprocess_plasmid(existing: Plasmid, raw_text: str) -> tuple[Plasmid, str]:
    mapped = map_genbank_text_to_plasmid(raw_text, raw_ref=existing.raw_ref)
    annotated = parse_genbank_text(raw_text)
    return existing.model_copy(
        update={
            "sequence": mapped.sequence,
            "length": mapped.length,
            "organism": mapped.organism,
            "vector_type": mapped.vector_type,
            "markers": mapped.markers,
            "promoters": mapped.promoters,
            "publication_doi": mapped.publication_doi,
            "annotation_complete": annotated.annotation_complete,
            "raw_ref": existing.raw_ref,
        }
    ), annotated.vector_profile


def changed_fields(before: Plasmid, after: Plasmid) -> dict[str, dict[str, Any]]:
    return {
        field_name: {"before": getattr(before, field_name), "after": getattr(after, field_name)}
        for field_name in RELEVANT_FIELDS
        if getattr(before, field_name) != getattr(after, field_name)
    }


def candidate_where(config: ReprocessConfig) -> tuple[str, tuple[Any, ...]]:
    if config.mode == "all":
        return "", ()
    if config.mode == "stale":
        return "WHERE updated_at < %s", (config.before,)
    if config.mode == "source" and config.source == "curated":
        return "WHERE id LIKE 'curated:%'", ()
    if config.mode == "source":
        return "WHERE source = %s AND id NOT LIKE 'curated:%'", (config.source,)
    marker_pattern = parse_filter_pattern(config.pattern)
    return "WHERE markers::text ILIKE %s", (f"%{marker_pattern}%",)


def parse_filter_pattern(pattern: str | None) -> str:
    if not pattern:
        raise ReprocessError("filter mode requires --pattern")
    if pattern in FILTER_ALIASES:
        return FILTER_ALIASES[pattern]
    match = FILTER_PATTERN.match(pattern.strip())
    if not match:
        raise ReprocessError("filter pattern must look like: markers contains 'replication'")
    return match.group("value")


def batched(values: list[Plasmid], batch_size: int) -> Iterable[list[Plasmid]]:
    for index in range(0, len(values), batch_size):
        yield values[index : index + batch_size]


def write_report(report: ReprocessReport, output_dir: Path, *, finished_at: datetime | None = None) -> Path:
    finished = finished_at or datetime.now(UTC)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = finished.astimezone(UTC).strftime("%Y-%m-%d-%H%M%S")
    path = output_dir / f"{timestamp}-reprocess-{report.mode}.json"
    path.write_text(json.dumps(report.as_dict(finished_at=finished), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def parse_timestamp(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return timestamp.replace(tzinfo=timestamp.tzinfo or UTC)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reprocess cached plasmid records without external network requests.")
    parser.add_argument("--mode", choices=["all", "stale", "source", "filter"], default="all")
    parser.add_argument("--before", type=parse_timestamp)
    parser.add_argument("--source", choices=["genbank", "curated"])
    parser.add_argument("--pattern")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = ReprocessConfig.from_env(
        mode=args.mode,
        before=args.before,
        source=args.source,
        pattern=args.pattern,
        batch_size=args.batch_size,
        output_dir=args.output_dir,
    )
    database = PostgresReprocessDatabase(config.database_url)
    report = run_reprocessing(config, database=database, object_store=S3TextObjectStore(config))
    finished_at = datetime.now(UTC)
    report_path = write_report(report, config.output_dir, finished_at=finished_at)
    database.finish_run(report.run_id, report, finished_at=finished_at, report_path=str(report_path))
    print(json.dumps({"report": str(report_path), **report.as_dict(finished_at=finished_at)}, indent=2))
    return 0 if not report.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
