from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import boto3
import psycopg

from packages.core.schemas import Plasmid
from packages.data_pipeline.ingest.genbank import env, load_dotenv
from packages.data_pipeline.parse.sequence_parser import parse_genbank_text


DEFAULT_OUTPUT_DIR = Path("data/eval/quality")
NULLABLE_FIELDS = tuple(Plasmid.model_fields)


class QualityReportRepository(Protocol):
    def list_plasmids(self) -> list[Plasmid]: ...


class TextObjectStore(Protocol):
    def get_text(self, key: str) -> str: ...


@dataclass(frozen=True)
class QualityReportConfig:
    database_url: str = "postgresql://plasmid:plasmid@localhost:5432/plasmid_design"
    object_store_endpoint: str = "http://localhost:9000"
    object_store_bucket: str = "plasmid-design-local"
    object_store_access_key: str = "minioadmin"
    object_store_secret_key: str = "minioadmin"
    output_dir: Path = DEFAULT_OUTPUT_DIR

    @classmethod
    def from_env(cls, *, output_dir: Path | None = None) -> QualityReportConfig:
        dotenv = load_dotenv(Path(".env"))
        return cls(
            database_url=env("DATABASE_URL", cls.database_url, dotenv),
            object_store_endpoint=env("OBJECT_STORE_ENDPOINT", cls.object_store_endpoint, dotenv),
            object_store_bucket=env("OBJECT_STORE_BUCKET", cls.object_store_bucket, dotenv),
            object_store_access_key=env("OBJECT_STORE_ACCESS_KEY", cls.object_store_access_key, dotenv),
            object_store_secret_key=env("OBJECT_STORE_SECRET_KEY", cls.object_store_secret_key, dotenv),
            output_dir=output_dir or DEFAULT_OUTPUT_DIR,
        )


class PostgresQualityReportRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def list_plasmids(self) -> list[Plasmid]:
        with psycopg.connect(self.database_url) as connection:
            rows = connection.execute("SELECT payload FROM plasmids ORDER BY id").fetchall()
        return [Plasmid.model_validate(row[0]) for row in rows]


class S3QualityReportObjectStore:
    def __init__(self, config: QualityReportConfig) -> None:
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


def build_quality_report(
    repository: QualityReportRepository,
    object_store: TextObjectStore,
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    plasmids = repository.list_plasmids()
    timestamp = generated_at or datetime.now(UTC)
    records_per_source: Counter[str] = Counter()
    profiles: Counter[str] = Counter()
    complete_by_profile: Counter[str] = Counter()
    organisms: Counter[str] = Counter()
    vector_types: Counter[str] = Counter()
    length_ranges: Counter[str] = Counter()
    markers: Counter[str] = Counter()
    applications: Counter[str] = Counter()
    null_counts: Counter[str] = Counter()
    parse_errors: list[dict[str, str]] = []

    for plasmid in plasmids:
        records_per_source[display_source(plasmid)] += 1
        organisms[plasmid.organism or "<null>"] += 1
        vector_types[plasmid.vector_type or "<null>"] += 1
        length_ranges[length_range(plasmid.length)] += 1
        markers.update(plasmid.markers or ["<none>"])
        applications.update(plasmid.use_cases or ["<none>"])
        for field_name in NULLABLE_FIELDS:
            if is_nullish(getattr(plasmid, field_name)):
                null_counts[field_name] += 1

        profile = "unknown"
        annotation_complete = False
        try:
            annotated = parse_genbank_text(object_store.get_text(plasmid.raw_ref))
            profile = annotated.vector_profile
            annotation_complete = annotated.annotation_complete
        except Exception as exc:
            parse_errors.append({"id": plasmid.id, "raw_ref": plasmid.raw_ref, "error": str(exc)})
        profiles[profile] += 1
        if annotation_complete:
            complete_by_profile[profile] += 1

    total = len(plasmids)
    duplicates = duplicate_clusters(plasmids)
    return {
        "generated_at": timestamp.astimezone(UTC).isoformat(),
        "total_records": total,
        "records_per_source": sorted_counts(records_per_source),
        "profiles": {
            "breakdown": sorted_counts(profiles),
            "unclassified": profiles["unknown"],
        },
        "annotation_complete": {
            "count": sum(complete_by_profile.values()),
            "rate": rate(sum(complete_by_profile.values()), total),
            "by_profile": {
                profile: {
                    "count": complete_by_profile[profile],
                    "total": profile_total,
                    "rate": rate(complete_by_profile[profile], profile_total),
                }
                for profile, profile_total in sorted(profiles.items())
            },
        },
        "distributions": {
            "organisms": sorted_counts(organisms),
            "vector_types": sorted_counts(vector_types),
            "length_ranges_bp": ordered_length_counts(length_ranges),
            "selectable_markers": sorted_counts(markers),
            "applications": sorted_counts(applications),
        },
        "null_rates": {
            field_name: {"count": null_counts[field_name], "rate": rate(null_counts[field_name], total)}
            for field_name in NULLABLE_FIELDS
        },
        "duplicate_clusters": duplicates,
        "duplicate_cluster_count": len(duplicates),
        "parse_errors": parse_errors,
    }


def duplicate_clusters(plasmids: list[Plasmid]) -> list[dict[str, Any]]:
    prefix_buckets: dict[str, list[Plasmid]] = defaultdict(list)
    for plasmid in plasmids:
        prefix_hash = hashlib.sha256(plasmid.sequence[:1000].encode("ascii")).hexdigest()
        prefix_buckets[prefix_hash].append(plasmid)

    clusters: list[dict[str, Any]] = []
    for prefix_hash, bucket in prefix_buckets.items():
        if len(bucket) < 2:
            continue
        verified: dict[str, list[Plasmid]] = defaultdict(list)
        for plasmid in bucket:
            verified[plasmid.sequence].append(plasmid)
        for sequence, matches in verified.items():
            if len(matches) < 2:
                continue
            clusters.append(
                {
                    "prefix_sha256": prefix_hash,
                    "sequence_sha256": hashlib.sha256(sequence.encode("ascii")).hexdigest(),
                    "length": len(sequence),
                    "count": len(matches),
                    "record_ids": sorted(plasmid.id for plasmid in matches),
                }
            )
    return sorted(clusters, key=lambda cluster: (-cluster["count"], cluster["record_ids"]))


def render_markdown(report: dict[str, Any]) -> str:
    complete = report["annotation_complete"]
    lines = [
        "# Plasmid Data Quality Report",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Total records: `{report['total_records']}`",
        f"- Complete annotations: `{complete['count']}/{report['total_records']}` ({format_percent(complete['rate'])})",
        f"- Unclassified records: `{report['profiles']['unclassified']}`",
        f"- Duplicate clusters: `{report['duplicate_cluster_count']}`",
        f"- Parse errors: `{len(report['parse_errors'])}`",
        "",
        "## Records Per Source",
        "",
        markdown_table(("Source", "Records"), report["records_per_source"].items()),
        "",
        "## Profile Completeness",
        "",
        markdown_table(
            ("Profile", "Complete", "Total", "Rate"),
            (
                (profile, values["count"], values["total"], format_percent(values["rate"]))
                for profile, values in complete["by_profile"].items()
            ),
        ),
        "",
        "## Distributions",
        "",
    ]
    for title, key in (
        ("Organisms", "organisms"),
        ("Vector Types", "vector_types"),
        ("Length Ranges (bp)", "length_ranges_bp"),
        ("Selectable Markers", "selectable_markers"),
        ("Applications / Use Cases", "applications"),
    ):
        lines.extend([f"### {title}", "", markdown_table(("Value", "Records"), report["distributions"][key].items()), ""])
    lines.extend(
        [
            "## Null Rates",
            "",
            markdown_table(
                ("Field", "Null/Empty", "Rate"),
                (
                    (field_name, values["count"], format_percent(values["rate"]))
                    for field_name, values in report["null_rates"].items()
                ),
            ),
            "",
            "## Duplicate Clusters",
            "",
        ]
    )
    if report["duplicate_clusters"]:
        lines.append(markdown_table(
            ("Count", "Length", "Record IDs"),
            (
                (cluster["count"], cluster["length"], ", ".join(cluster["record_ids"]))
                for cluster in report["duplicate_clusters"]
            ),
        ))
    else:
        lines.append("No exact-sequence duplicate clusters detected.")
    lines.extend(["", "## Parse Errors", ""])
    if report["parse_errors"]:
        lines.append(markdown_table(
            ("Record", "Raw Cache Key", "Error"),
            ((error["id"], error["raw_ref"], error["error"]) for error in report["parse_errors"]),
        ))
    else:
        lines.append("No parser errors detected.")
    lines.append("")
    return "\n".join(lines)


def write_report_files(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.fromisoformat(report["generated_at"]).astimezone(UTC).strftime("%Y-%m-%d-%H%M%S")
    stem = output_dir / f"{timestamp}-quality-report"
    json_path = stem.with_suffix(".json")
    markdown_path = stem.with_suffix(".md")
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def display_source(plasmid: Plasmid) -> str:
    return "curated" if plasmid.id.startswith("curated:") else str(plasmid.source)


def length_range(length: int) -> str:
    if length < 1000:
        return "<1000"
    if length < 5000:
        return "1000-4999"
    if length < 10000:
        return "5000-9999"
    if length < 50000:
        return "10000-49999"
    return ">=50000"


def ordered_length_counts(counts: Counter[str]) -> dict[str, int]:
    return {bucket: counts[bucket] for bucket in ("<1000", "1000-4999", "5000-9999", "10000-49999", ">=50000")}


def sorted_counts(counts: Counter[str]) -> dict[str, int]:
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0].lower())))


def is_nullish(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def markdown_table(headers: tuple[str, ...], rows: Any) -> str:
    values = [tuple(str(cell).replace("|", "\\|") for cell in row) for row in rows]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in values)
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Phase 0 plasmid data-quality reports.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = QualityReportConfig.from_env(output_dir=args.output_dir)
    report = build_quality_report(
        PostgresQualityReportRepository(config.database_url),
        S3QualityReportObjectStore(config),
    )
    json_path, markdown_path = write_report_files(report, config.output_dir)
    print(json.dumps({"json": str(json_path), "markdown": str(markdown_path), "summary": report["annotation_complete"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
