from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Protocol

import psycopg
import boto3
from botocore.exceptions import ClientError

from packages.core.schemas import AnnotatedSequence, DesignSpec, Plasmid, ValidationCheck, ValidationReport
from packages.data_pipeline.ingest.genbank import env, load_dotenv
from packages.data_pipeline.parse.sequence_parser import parse_genbank_text
from packages.validation.codon import run_codon_check
from packages.validation.common import CHECK_VERSION
from packages.validation.regulatory import run_regulatory_check
from packages.validation.repeats import run_repeat_instability_check
from packages.validation.restriction import run_restriction_site_check


ValidationFunction = Callable[[AnnotatedSequence, DesignSpec], ValidationCheck]


class ConstraintEngineProtocol(Protocol):
    def validate(self, sequence: AnnotatedSequence, spec: DesignSpec) -> ValidationReport: ...


@dataclass(frozen=True)
class ConstraintEngine:
    checks: tuple[ValidationFunction, ...] = field(
        default_factory=lambda: (
            run_restriction_site_check,
            run_repeat_instability_check,
            run_codon_check,
            run_regulatory_check,
        )
    )
    version: str = CHECK_VERSION

    def validate(self, sequence: AnnotatedSequence, spec: DesignSpec) -> ValidationReport:
        checks = [check(sequence, spec) for check in self.checks]
        overall = "PASS"
        if any(check.status == "FAIL" for check in checks):
            overall = "FAIL"
        elif any(check.status == "WARN" for check in checks):
            overall = "WARN"
        return ValidationReport(overall=overall, checks=checks, generated_by_model_version=self.version)


def validate_sequence(sequence: AnnotatedSequence, spec: DesignSpec) -> ValidationReport:
    return ConstraintEngine().validate(sequence, spec)


def default_design_spec_for_plasmid(plasmid: Plasmid) -> DesignSpec:
    return DesignSpec(
        organism=plasmid.organism or "Escherichia coli",
        vector_type=plasmid.vector_type,
        markers=plasmid.markers,
        promoter_type=plasmid.promoters[0] if plasmid.promoters else None,
        application=plasmid.use_cases[0] if plasmid.use_cases else None,
    )


def load_sample_records(database_url: str, *, limit: int) -> list[tuple[Plasmid, AnnotatedSequence]]:
    query = "SELECT payload FROM plasmids ORDER BY id LIMIT %s"
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(query, (limit,))
            rows = cur.fetchall()
    dotenv = load_dotenv(Path(".env"))
    store = S3TextObjectStore(
        endpoint=env("OBJECT_STORE_ENDPOINT", "http://localhost:9000", dotenv),
        bucket=env("OBJECT_STORE_BUCKET", "plasmid-design-local", dotenv),
        access_key=env("OBJECT_STORE_ACCESS_KEY", "minioadmin", dotenv),
        secret_key=env("OBJECT_STORE_SECRET_KEY", "minioadmin", dotenv),
    )
    records: list[tuple[Plasmid, AnnotatedSequence]] = []
    for row in rows:
        plasmid = Plasmid.model_validate(row[0])
        raw = store.get_text(plasmid.raw_ref)
        if raw is None:
            continue
        records.append((plasmid, parse_genbank_text(raw)))
    return records


@dataclass(frozen=True)
class S3TextObjectStore:
    endpoint: str
    bucket: str
    access_key: str
    secret_key: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "client",
            boto3.client(
                "s3",
                endpoint_url=self.endpoint,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name="us-east-1",
            ),
        )

    def get_text(self, key: str) -> str | None:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise
        return response["Body"].read().decode("utf-8")


def summarize_reports(reports: Iterable[ValidationReport]) -> dict[str, int]:
    summary = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for report in reports:
        summary[str(report.overall)] += 1
    return summary


def run_validate_sample(limit: int, output_dir: Path | None = None) -> Path:
    dotenv = load_dotenv(Path(".env"))
    database_url = env("DATABASE_URL", "postgresql://plasmid:plasmid@localhost:5432/plasmid_design", dotenv)
    records = load_sample_records(database_url, limit=limit)
    engine = ConstraintEngine()
    results = []
    for plasmid, annotated in records:
        report = engine.validate(annotated, default_design_spec_for_plasmid(plasmid))
        results.append({"plasmid_id": plasmid.id, "name": plasmid.name, "overall": report.overall, "checks": [check.model_dump() for check in report.checks]})
    out_dir = output_dir or Path("data/eval/validation")
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    path = out_dir / f"{timestamp}-validate-sample.json"
    path.write_text(json.dumps({"count": len(results), "summary": summarize_reports(ValidationReport.model_validate({"overall": item["overall"], "checks": item["checks"], "generated_by_model_version": CHECK_VERSION}) for item in results), "results": results}, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic Phase 3 validation on a sample of corpus records.")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--output-dir", type=Path, default=Path("data/eval/validation"))
    args = parser.parse_args()
    path = run_validate_sample(args.limit, args.output_dir)
    print(f"Wrote validation sample report to {path}")


if __name__ == "__main__":
    main()
