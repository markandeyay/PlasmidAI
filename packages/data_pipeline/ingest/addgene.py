from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Protocol
from urllib.parse import urljoin

import boto3
import psycopg
import requests
from botocore.exceptions import ClientError
from psycopg.types.json import Jsonb

from packages.core.schemas import Plasmid


SOURCE = "addgene"
DEFAULT_BASE_URL = "https://api.developers.addgene.org/"
DEFAULT_STALE_DAYS = 1
DEFAULT_DEV_LIMIT = 10


class AddgeneIngestionError(Exception):
    code = "addgene_ingestion_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}

    def to_error_record(self, plasmid_id: int | str | None = None) -> dict[str, Any]:
        record: dict[str, Any] = {
            "code": self.code,
            "message": str(self),
        }
        if plasmid_id is not None:
            record["plasmid_id"] = str(plasmid_id)
        if self.details:
            record["details"] = self.details
        return record


class AddgeneConfigError(AddgeneIngestionError):
    code = "config_error"


class AddgeneHttpError(AddgeneIngestionError):
    code = "http_error"


class AddgeneMappingError(AddgeneIngestionError):
    code = "mapping_error"


class ObjectStore(Protocol):
    def exists(self, key: str) -> bool: ...

    def is_fresh(self, key: str, max_age: timedelta) -> bool: ...

    def put_json(self, key: str, payload: dict[str, Any]) -> None: ...

    def get_json(self, key: str) -> dict[str, Any]: ...


class AddgeneClient(Protocol):
    def iter_plasmid_ids(self, *, limit: int | None = None) -> Iterable[int]: ...

    def fetch_plasmid_with_sequences(self, plasmid_id: int) -> dict[str, Any]: ...


class PlasmidRepository(Protocol):
    def ensure_schema(self) -> None: ...

    def start_run(self, *, source: str, mode: str, started_at: datetime) -> int: ...

    def finish_run(
        self,
        run_id: int,
        *,
        finished_at: datetime,
        records_seen: int,
        records_upserted: int,
        errors: list[dict[str, Any]],
    ) -> None: ...

    def upsert_plasmid(self, plasmid: Plasmid) -> None: ...


@dataclass(frozen=True)
class AddgeneIngestionConfig:
    mode: str = "dev"
    limit: int | None = DEFAULT_DEV_LIMIT
    stale_after: timedelta = timedelta(days=DEFAULT_STALE_DAYS)
    base_url: str = DEFAULT_BASE_URL
    token: str | None = None
    license_accepted: bool = False
    database_url: str = "postgresql://plasmid:plasmid@localhost:5432/plasmid_design"
    object_store_endpoint: str = "http://localhost:9000"
    object_store_bucket: str = "plasmid-design-local"
    object_store_access_key: str = "minioadmin"
    object_store_secret_key: str = "minioadmin"
    min_interval_seconds: float = 1.0
    max_retries: int = 3
    backoff_seconds: float = 2.0
    page_size: int = 100

    @classmethod
    def from_env(cls, *, mode: str, limit: int | None, stale_days: int) -> AddgeneIngestionConfig:
        dotenv = load_dotenv(Path(".env"))
        configured_limit = limit
        if mode == "dev" and configured_limit is None:
            configured_limit = int(env("N", str(DEFAULT_DEV_LIMIT), dotenv))

        return cls(
            mode=mode,
            limit=configured_limit,
            stale_after=timedelta(days=stale_days),
            base_url=env("ADDGENE_API_BASE_URL", DEFAULT_BASE_URL, dotenv) or DEFAULT_BASE_URL,
            token=env("ADDGENE_API_TOKEN", "", dotenv) or env("ADDGENE_API_KEY", "", dotenv) or None,
            license_accepted=env("ADDGENE_DATA_LICENSE_ACCEPTED", "false", dotenv).lower()
            in {"1", "true", "yes"},
            database_url=env("DATABASE_URL", "postgresql://plasmid:plasmid@localhost:5432/plasmid_design", dotenv),
            object_store_endpoint=env("OBJECT_STORE_ENDPOINT", "http://localhost:9000", dotenv),
            object_store_bucket=env("OBJECT_STORE_BUCKET", "plasmid-design-local", dotenv),
            object_store_access_key=env("OBJECT_STORE_ACCESS_KEY", "minioadmin", dotenv),
            object_store_secret_key=env("OBJECT_STORE_SECRET_KEY", "minioadmin", dotenv),
            min_interval_seconds=float(env("ADDGENE_MIN_INTERVAL_SECONDS", "1.0", dotenv)),
            max_retries=int(env("ADDGENE_MAX_RETRIES", "3", dotenv)),
            backoff_seconds=float(env("ADDGENE_BACKOFF_SECONDS", "2.0", dotenv)),
            page_size=int(env("ADDGENE_PAGE_SIZE", "100", dotenv)),
        )

    def validate_for_real_network(self) -> None:
        if self.mode not in {"dev", "bulk", "refresh"}:
            raise AddgeneConfigError(f"unsupported Addgene ingestion mode: {self.mode}")
        missing: list[str] = []
        if not self.token:
            missing.append("ADDGENE_API_TOKEN")
        if not self.license_accepted:
            missing.append("ADDGENE_DATA_LICENSE_ACCEPTED=true")
        if missing:
            raise AddgeneConfigError(
                "Addgene ingestion requires approved API credentials and accepted data license",
                details={"missing_or_unaccepted": missing},
            )


@dataclass
class IngestionResult:
    run_id: int
    records_seen: int = 0
    records_upserted: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)


class RateLimiter:
    def __init__(self, min_interval_seconds: float) -> None:
        self.min_interval_seconds = min_interval_seconds
        self._last_request_at: float | None = None

    def wait(self) -> None:
        if self._last_request_at is None:
            self._last_request_at = time.monotonic()
            return
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_request_at = time.monotonic()


class RequestsAddgeneClient:
    def __init__(self, config: AddgeneIngestionConfig) -> None:
        self.base_url = config.base_url.rstrip("/") + "/"
        self.page_size = config.page_size
        self.max_retries = config.max_retries
        self.backoff_seconds = config.backoff_seconds
        self.rate_limiter = RateLimiter(config.min_interval_seconds)
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Token {config.token}", "Accept": "application/json"})

    def iter_plasmid_ids(self, *, limit: int | None = None) -> Iterable[int]:
        yielded = 0
        page = 1
        while True:
            response = self._get_json("catalog/plasmid/", params={"page": page, "page_size": self.page_size})
            results = response.get("results") or response.get("plasmids") or []
            if not isinstance(results, list):
                raise AddgeneHttpError("Addgene catalog response did not contain a result list")
            for item in results:
                plasmid_id = item.get("id") if isinstance(item, dict) else item
                if plasmid_id is None:
                    continue
                yield int(plasmid_id)
                yielded += 1
                if limit is not None and yielded >= limit:
                    return
            if not response.get("next") or not results:
                return
            page += 1

    def fetch_plasmid_with_sequences(self, plasmid_id: int) -> dict[str, Any]:
        return self._get_json(f"catalog/plasmid-with-sequences/{plasmid_id}/")

    def _get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = urljoin(self.base_url, path)
        last_error: str | None = None
        for attempt in range(self.max_retries + 1):
            self.rate_limiter.wait()
            try:
                response = self.session.get(url, params=params, timeout=60, allow_redirects=True)
            except requests.RequestException as exc:
                last_error = str(exc)
                if attempt >= self.max_retries:
                    break
                time.sleep(self.backoff_seconds * (2**attempt))
                continue
            if response.status_code == 200:
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise AddgeneHttpError("Addgene response was not valid JSON") from exc
                if not isinstance(payload, dict):
                    raise AddgeneHttpError("Addgene JSON response root was not an object")
                return payload
            last_error = f"HTTP {response.status_code}: {response.text[:500]}"
            if attempt >= self.max_retries:
                break
            time.sleep(self.backoff_seconds * (2**attempt))
        raise AddgeneHttpError(f"Addgene request failed for {url}", details={"last_error": last_error})


class S3ObjectStore:
    def __init__(self, config: AddgeneIngestionConfig) -> None:
        self.bucket = config.object_store_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=config.object_store_endpoint,
            aws_access_key_id=config.object_store_access_key,
            aws_secret_access_key=config.object_store_secret_key,
            region_name="us-east-1",
        )
        self._ensure_bucket()

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise

    def is_fresh(self, key: str, max_age: timedelta) -> bool:
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise
        last_modified = response["LastModified"]
        if last_modified.tzinfo is None:
            last_modified = last_modified.replace(tzinfo=UTC)
        return datetime.now(UTC) - last_modified <= max_age

    def put_json(self, key: str, payload: dict[str, Any]) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(payload, sort_keys=True).encode("utf-8"),
            ContentType="application/json",
        )

    def get_json(self, key: str) -> dict[str, Any]:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        payload = json.loads(response["Body"].read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise AddgeneMappingError("cached Addgene blob root was not a JSON object")
        return payload

    def _ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self.bucket)


class PostgresPlasmidRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def ensure_schema(self) -> None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS plasmids (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    name TEXT NOT NULL,
                    sequence TEXT NOT NULL,
                    length INTEGER NOT NULL,
                    organism TEXT,
                    vector_type TEXT,
                    markers JSONB NOT NULL DEFAULT '[]'::jsonb,
                    promoters JSONB NOT NULL DEFAULT '[]'::jsonb,
                    publication_doi TEXT,
                    use_cases JSONB NOT NULL DEFAULT '[]'::jsonb,
                    annotation_complete BOOLEAN NOT NULL,
                    raw_ref TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL,
                    payload JSONB NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ingestion_runs (
                    id BIGSERIAL PRIMARY KEY,
                    source TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    started_at TIMESTAMPTZ NOT NULL,
                    finished_at TIMESTAMPTZ,
                    records_seen INTEGER NOT NULL DEFAULT 0,
                    records_upserted INTEGER NOT NULL DEFAULT 0,
                    errors JSONB NOT NULL DEFAULT '[]'::jsonb
                )
                """
            )

    def start_run(self, *, source: str, mode: str, started_at: datetime) -> int:
        with psycopg.connect(self.database_url) as connection:
            row = connection.execute(
                """
                INSERT INTO ingestion_runs (source, mode, started_at)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (source, mode, started_at),
            ).fetchone()
            if row is None:
                raise AddgeneIngestionError("failed to create ingestion run")
            return int(row[0])

    def finish_run(
        self,
        run_id: int,
        *,
        finished_at: datetime,
        records_seen: int,
        records_upserted: int,
        errors: list[dict[str, Any]],
    ) -> None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                """
                UPDATE ingestion_runs
                SET finished_at = %s,
                    records_seen = %s,
                    records_upserted = %s,
                    errors = %s
                WHERE id = %s
                """,
                (finished_at, records_seen, records_upserted, Jsonb(errors), run_id),
            )

    def upsert_plasmid(self, plasmid: Plasmid) -> None:
        payload = plasmid.model_dump(mode="json")
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                """
                INSERT INTO plasmids (
                    id, source, name, sequence, length, organism, vector_type,
                    markers, promoters, publication_doi, use_cases,
                    annotation_complete, raw_ref, created_at, updated_at, payload
                )
                VALUES (
                    %(id)s, %(source)s, %(name)s, %(sequence)s, %(length)s,
                    %(organism)s, %(vector_type)s, %(markers)s, %(promoters)s,
                    %(publication_doi)s, %(use_cases)s, %(annotation_complete)s,
                    %(raw_ref)s, %(created_at)s, %(updated_at)s, %(payload)s
                )
                ON CONFLICT (id) DO UPDATE
                SET source = EXCLUDED.source,
                    name = EXCLUDED.name,
                    sequence = EXCLUDED.sequence,
                    length = EXCLUDED.length,
                    organism = EXCLUDED.organism,
                    vector_type = EXCLUDED.vector_type,
                    markers = EXCLUDED.markers,
                    promoters = EXCLUDED.promoters,
                    publication_doi = EXCLUDED.publication_doi,
                    use_cases = EXCLUDED.use_cases,
                    annotation_complete = EXCLUDED.annotation_complete,
                    raw_ref = EXCLUDED.raw_ref,
                    updated_at = EXCLUDED.updated_at,
                    payload = EXCLUDED.payload
                """,
                {
                    **payload,
                    "markers": Jsonb(payload["markers"]),
                    "promoters": Jsonb(payload["promoters"]),
                    "use_cases": Jsonb(payload["use_cases"]),
                    "payload": Jsonb(payload),
                },
            )


def run_addgene_ingestion(
    config: AddgeneIngestionConfig,
    *,
    client: AddgeneClient,
    object_store: ObjectStore,
    repository: PlasmidRepository,
) -> IngestionResult:
    repository.ensure_schema()
    run_id = repository.start_run(source=SOURCE, mode=config.mode, started_at=datetime.now(UTC))
    result = IngestionResult(run_id=run_id)
    try:
        for plasmid_id in client.iter_plasmid_ids(limit=config.limit):
            result.records_seen += 1
            key = raw_cache_key(plasmid_id)
            try:
                if should_fetch_cache(config, object_store, key):
                    raw = client.fetch_plasmid_with_sequences(plasmid_id)
                    object_store.put_json(key, raw)
                cached_raw = object_store.get_json(key)
                plasmid = map_addgene_raw_to_plasmid(cached_raw, raw_ref=key)
                repository.upsert_plasmid(plasmid)
                result.records_upserted += 1
            except AddgeneIngestionError as exc:
                result.errors.append(exc.to_error_record(plasmid_id))
            except Exception as exc:
                result.errors.append(
                    {"code": "unexpected_error", "plasmid_id": str(plasmid_id), "message": str(exc)}
                )
        return result
    finally:
        repository.finish_run(
            run_id,
            finished_at=datetime.now(UTC),
            records_seen=result.records_seen,
            records_upserted=result.records_upserted,
            errors=result.errors,
        )


def should_fetch_cache(config: AddgeneIngestionConfig, object_store: ObjectStore, key: str) -> bool:
    if config.mode == "bulk":
        return not object_store.exists(key)
    return not object_store.is_fresh(key, config.stale_after)


def raw_cache_key(plasmid_id: int | str) -> str:
    return f"raw/addgene/{plasmid_id}.json"


def map_addgene_raw_to_plasmid(raw: dict[str, Any], *, raw_ref: str) -> Plasmid:
    addgene_id = raw.get("id")
    if addgene_id is None:
        raise AddgeneMappingError("Addgene raw record is missing id")

    sequence = select_best_sequence(raw)
    if sequence is None:
        raise AddgeneMappingError("Addgene raw record is missing a sequence")

    markers = dedupe_strings([raw.get("bacterial_resistance"), *as_list(raw.get("resistance_markers"))])
    promoters = dedupe_strings(
        [
            get_nested(raw, "cloning", "promoter"),
            *as_list(raw.get("promoters")),
            *[
                get_nested(insert, "cloning", "promoter")
                for insert in as_list(raw.get("inserts"))
                if isinstance(insert, dict)
            ],
        ]
    )
    vector_types = as_list(get_nested(raw, "cloning", "vector_types")) or as_list(raw.get("vector_types"))
    use_cases = dedupe_strings(
        [
            raw.get("purpose"),
            raw.get("description"),
            raw.get("experimental_use"),
            *as_list(raw.get("expression")),
            *[tag.get("tag") for tag in as_list(raw.get("tags")) if isinstance(tag, dict)],
        ]
    )

    return Plasmid(
        id=f"addgene:{addgene_id}",
        source=SOURCE,
        name=str(raw.get("name") or f"Addgene {addgene_id}"),
        sequence=sequence,
        length=len("".join(str(sequence).upper().split())),
        organism=select_organism(raw),
        vector_type=str(vector_types[0]) if vector_types else None,
        markers=markers,
        promoters=promoters,
        publication_doi=get_nested(raw, "article", "doi"),
        use_cases=use_cases,
        annotation_complete=False,
        raw_ref=raw_ref,
    )


def select_best_sequence(raw: dict[str, Any]) -> str | None:
    sequences = raw.get("sequences")
    if isinstance(sequences, dict):
        for bucket in (
            "public_addgene_full_sequences",
            "public_user_full_sequences",
            "public_addgene_partial_sequences",
            "public_user_partial_sequences",
        ):
            for candidate in as_list(sequences.get(bucket)):
                if isinstance(candidate, dict) and candidate.get("sequence"):
                    return str(candidate["sequence"])
    if raw.get("sequence"):
        return str(raw["sequence"])
    return None


def select_organism(raw: dict[str, Any]) -> str | None:
    for insert in as_list(raw.get("inserts")):
        if not isinstance(insert, dict):
            continue
        for species in as_list(insert.get("species")):
            if isinstance(species, dict) and species.get("species"):
                return str(species["species"])
            if isinstance(species, str) and species:
                return species
    species = as_list(raw.get("species"))
    return str(species[0]) if species else None


def get_nested(value: dict[str, Any], *keys: str) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def as_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    return [value]


def dedupe_strings(values: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if not text or text.lower() == "none":
            continue
        key = text.lower()
        if key not in seen:
            seen.add(key)
            result.append(text)
    return result


def load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def env(name: str, default: str, dotenv: dict[str, str]) -> str:
    return os.environ.get(name) or dotenv.get(name) or default


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest Addgene plasmid metadata and raw sequences.")
    parser.add_argument("--mode", choices=["dev", "bulk", "refresh"], default=os.environ.get("MODE", "dev"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--stale-days", type=int, default=DEFAULT_STALE_DAYS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = AddgeneIngestionConfig.from_env(
        mode=args.mode,
        limit=args.limit,
        stale_days=args.stale_days,
    )
    try:
        config.validate_for_real_network()
        result = run_addgene_ingestion(
            config,
            client=RequestsAddgeneClient(config),
            object_store=S3ObjectStore(config),
            repository=PostgresPlasmidRepository(config.database_url),
        )
    except AddgeneIngestionError as exc:
        print(json.dumps({"error": exc.to_error_record()}, indent=2))
        return 2
    print(
        json.dumps(
            {
                "run_id": result.run_id,
                "records_seen": result.records_seen,
                "records_upserted": result.records_upserted,
                "errors": result.errors,
            },
            indent=2,
        )
    )
    return 0 if not result.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
