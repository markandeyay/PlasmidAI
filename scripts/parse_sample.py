from __future__ import annotations

import os
import argparse
import sys
from collections import Counter
from pathlib import Path

import boto3
import psycopg

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.data_pipeline.parse.sequence_parser import parse_genbank_text


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse a small sample of cached GenBank plasmid records.")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--source", default="genbank")
    args = parser.parse_args()
    dotenv = load_dotenv(Path(".env"))
    limit = args.limit
    database_url = env("DATABASE_URL", "postgresql://plasmid:plasmid@localhost:5432/plasmid_design", dotenv)
    bucket = env("OBJECT_STORE_BUCKET", "plasmid-design-local", dotenv)
    s3 = boto3.client(
        "s3",
        endpoint_url=env("OBJECT_STORE_ENDPOINT", "http://localhost:9000", dotenv),
        aws_access_key_id=env("OBJECT_STORE_ACCESS_KEY", "minioadmin", dotenv),
        aws_secret_access_key=env("OBJECT_STORE_SECRET_KEY", "minioadmin", dotenv),
        region_name="us-east-1",
    )

    if args.source in {"curated", "curated_seed"}:
        query = """
        SELECT id, raw_ref
        FROM plasmids
        WHERE id LIKE 'curated:%%'
        ORDER BY id
        LIMIT %s
        """
        params = (limit,)
    else:
        query = """
        SELECT id, raw_ref
        FROM plasmids
        WHERE source = %s
        ORDER BY id
        LIMIT %s
        """
        params = (args.source, limit)

    with psycopg.connect(database_url) as connection:
        rows = connection.execute(query, params).fetchall()

    complete = 0
    confidence_buckets: Counter[str] = Counter()
    profile_buckets: Counter[str] = Counter()
    profile_complete: Counter[str] = Counter()
    print(f"records={len(rows)}")
    for plasmid_id, raw_ref in rows:
        raw = s3.get_object(Bucket=bucket, Key=raw_ref)["Body"].read().decode("utf-8")
        annotated = parse_genbank_text(raw)
        counts = Counter(str(feature.type) for feature in annotated.features)
        profile_buckets[annotated.vector_profile] += 1
        for feature in annotated.features:
            if feature.confidence >= 0.90:
                confidence_buckets["high"] += 1
            elif feature.confidence >= 0.75:
                confidence_buckets["medium_high"] += 1
            else:
                confidence_buckets["low"] += 1
        if annotated.annotation_complete:
            complete += 1
            profile_complete[annotated.vector_profile] += 1
        count_text = ", ".join(f"{key}:{value}" for key, value in sorted(counts.items())) or "none"
        print(
            f"{plasmid_id} complete={annotated.annotation_complete} "
            f"profile={annotated.vector_profile} "
            f"features={len(annotated.features)} [{count_text}]"
        )
    print(f"annotation_complete={complete}/{len(rows)}")
    print(
        "profile_breakdown="
        + ", ".join(
            f"{profile}:{profile_complete[profile]}/{count}" for profile, count in sorted(profile_buckets.items())
        )
    )
    print("confidence_breakdown=" + ", ".join(f"{key}:{value}" for key, value in sorted(confidence_buckets.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
