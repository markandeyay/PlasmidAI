from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
import psycopg
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.core.schemas import AnnotatedSequence, DesignSpec, Plasmid
from packages.data_pipeline.ingest.genbank import env, load_dotenv
from packages.data_pipeline.parse.sequence_parser import parse_genbank_text
from packages.validation.engine import ConstraintEngine


CANDIDATES = [
    "AF013597.1",
    "AF403427.1",
    "AF519766.1",
    "AY219701.1",
    "U26464.1",
    "AF050464.1",
    "U07168.1",
    "AF216802.1",
    "U47121.2",
    "AF058756.1",
    "AF041805.1",
    "AF041806.1",
    "AF041807.1",
]


def load_plasmids(database_url: str) -> dict[str, Plasmid]:
    ids = [f"genbank:{accession}" for accession in CANDIDATES]
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT payload FROM plasmids WHERE payload->>'id' = ANY(%s)", (ids,))
            return {Plasmid.model_validate(row[0]).id: Plasmid.model_validate(row[0]) for row in cur.fetchall()}


def raw_store(dotenv: dict[str, str]) -> Any:
    return boto3.client(
        "s3",
        endpoint_url=env("OBJECT_STORE_ENDPOINT", "http://localhost:9000", dotenv),
        aws_access_key_id=env("OBJECT_STORE_ACCESS_KEY", "minioadmin", dotenv),
        aws_secret_access_key=env("OBJECT_STORE_SECRET_KEY", "minioadmin", dotenv),
        region_name="us-east-1",
    )


def read_raw(client: Any, dotenv: dict[str, str], key: str) -> str | None:
    try:
        response = client.get_object(Bucket=env("OBJECT_STORE_BUCKET", "plasmid-design-local", dotenv), Key=key)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise
    return response["Body"].read().decode("utf-8")


def host_for_profile(profile: str) -> str:
    if profile == "yeast_shuttle_vector":
        return "Saccharomyces cerevisiae and Escherichia coli"
    if profile in {"mammalian_expression_vector", "mammalian_reporter_vector"}:
        return "mammalian cells and Escherichia coli"
    if profile == "general_shuttle_vector":
        return "Escherichia coli shuttle host"
    return "Escherichia coli"


def design_spec(plasmid: Plasmid | None, annotated: AnnotatedSequence) -> DesignSpec:
    return DesignSpec(
        organism=host_for_profile(annotated.vector_profile),
        vector_type=(plasmid.vector_type if plasmid else None) or annotated.vector_profile,
        markers=plasmid.markers if plasmid else [],
        promoter_type=(plasmid.promoters[0] if plasmid and plasmid.promoters else None),
        application=(plasmid.use_cases[0] if plasmid and plasmid.use_cases else None),
        source=(plasmid.source if plasmid else "genbank"),
        publication_doi=(plasmid.publication_doi if plasmid else None),
        constraints=[f"target_length_bp={len(annotated.sequence)}", f"topology={annotated.topology}"],
    )


def evaluate_candidates() -> list[dict[str, Any]]:
    dotenv = load_dotenv(Path(".env"))
    plasmids = load_plasmids(env("DATABASE_URL", "postgresql://plasmid:plasmid@localhost:5432/plasmid_design", dotenv))
    client = raw_store(dotenv)
    engine = ConstraintEngine()
    results = []
    for accession in CANDIDATES:
        plasmid = plasmids.get(f"genbank:{accession}")
        raw_key = plasmid.raw_ref if plasmid else f"raw/genbank/{accession}.gb"
        raw_text = read_raw(client, dotenv, raw_key)
        if raw_text is None:
            results.append({"accession": accession, "status": "missing_cache", "raw_ref": raw_key})
            continue
        annotated = parse_genbank_text(raw_text)
        spec = design_spec(plasmid, annotated)
        report = engine.validate(annotated, spec)
        results.append(
            {
                "accession": accession,
                "plasmid_id": plasmid.id if plasmid else f"genbank:{accession}",
                "name": plasmid.name if plasmid else accession,
                "raw_ref": raw_key,
                "status": "evaluated",
                "profile": annotated.vector_profile,
                "annotation_complete": annotated.annotation_complete,
                "overall": report.overall,
                "failing_checks": [check.name for check in report.checks if check.status == "FAIL"],
                "warning_checks": [check.name for check in report.checks if check.status == "WARN"],
                "checks": [check.model_dump(mode="json") for check in report.checks],
                "defensible_known_good_candidate": report.overall != "FAIL",
            }
        )
    return results


def write_markdown(path: Path, title: str, results: list[dict[str, Any]]) -> None:
    counts = Counter(item.get("overall", item["status"]) for item in results)
    lines = [
        f"# {title}",
        "",
        f"- Generated at: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Candidate count: `{len(results)}`",
        f"- Outcome counts: `{dict(sorted(counts.items()))}`",
        "",
        "| Candidate | Profile | Overall | Failing checks | Warning checks | Defensible now? |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in results:
        lines.append(
            "| `{}` | `{}` | `{}` | `{}` | `{}` | `{}` |".format(
                item["accession"],
                item.get("profile", "n/a"),
                item.get("overall", item["status"]),
                ", ".join(item.get("failing_checks", [])) or "-",
                ", ".join(item.get("warning_checks", [])) or "-",
                item.get("defensible_known_good_candidate", False),
            )
        )
    lines.extend(["", "## Check Details", ""])
    for item in results:
        lines.append(f"### `{item['accession']}`")
        lines.append("")
        for check in item.get("checks", []):
            lines.append(f"- `{check['name']}` `{check['status']}`: {check['message']}")
        if not item.get("checks"):
            lines.append(f"- `{item['status']}`")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the 13 known-good validation candidates with current rules.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--title", default="Validation Candidate Evaluation")
    args = parser.parse_args()
    results = evaluate_candidates()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.suffix == ".json":
        args.output.write_text(json.dumps({"results": results}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        write_markdown(args.output, args.title, results)
    print(json.dumps({"output": str(args.output), "results": len(results)}))


if __name__ == "__main__":
    main()
