from __future__ import annotations

import json
from collections import Counter
from io import StringIO
from pathlib import Path
from typing import Any

import boto3
import psycopg
import yaml
from Bio import SeqIO
from botocore.exceptions import ClientError

from packages.core.schemas import AnnotatedSequence, DesignSpec, Plasmid, ValidationReport
from packages.data_pipeline.parse.sequence_parser import parse_genbank_text
from packages.validation.engine import ConstraintEngine


OUT_PATH = Path("data/eval/validation/curated_known_good.jsonl")
BLOCKER_PATH = Path("data/eval/validation/curated_known_good_blocker.json")
MANIFEST_PATH = Path("packages/data_pipeline/ingest/curated_seed_manifest.yaml")
APPROVED_CANDIDATE_IDS = (
    "genbank:AF013597.1",
    "genbank:U47121.2",
    "genbank:AF041805.1",
    "genbank:AF041806.1",
    "genbank:AF041807.1",
)


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in Path(".env").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    return env


def load_curated_manifest() -> dict[str, dict[str, Any]]:
    manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {f"curated:{record['id']}": record for record in manifest["records"]}


def raw_store(env: dict[str, str]):
    return boto3.client(
        "s3",
        endpoint_url=env.get("OBJECT_STORE_ENDPOINT", "http://localhost:9000"),
        aws_access_key_id=env.get("OBJECT_STORE_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=env.get("OBJECT_STORE_SECRET_KEY", "minioadmin"),
        region_name="us-east-1",
    )


def get_raw_text(client: Any, env: dict[str, str], key: str) -> str | None:
    try:
        response = client.get_object(Bucket=env.get("OBJECT_STORE_BUCKET", "plasmid-design-local"), Key=key)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise
    return response["Body"].read().decode("utf-8")


def genbank_metadata(raw_text: str) -> dict[str, Any]:
    record = SeqIO.read(StringIO(raw_text), "genbank")
    accessions = list(record.annotations.get("accessions") or [])
    accession = accessions[0] if accessions else str(record.id)
    references = []
    for ref in record.annotations.get("references") or []:
        item = {
            "title": getattr(ref, "title", None),
            "journal": getattr(ref, "journal", None),
            "pubmed_id": getattr(ref, "pubmed_id", None),
        }
        references.append({key: value for key, value in item.items() if value})
    return {
        "accession": accession,
        "description": record.description,
        "molecule_type": record.annotations.get("molecule_type"),
        "topology": record.annotations.get("topology"),
        "references": references[:3],
    }


def host_for_profile(profile: str) -> str:
    if profile == "yeast_shuttle_vector":
        return "Saccharomyces cerevisiae and Escherichia coli"
    if profile in {"mammalian_expression_vector", "mammalian_reporter_vector"}:
        return "mammalian cells and Escherichia coli"
    if profile == "general_shuttle_vector":
        return "Escherichia coli shuttle host"
    return "Escherichia coli"


def design_spec(plasmid: Plasmid, annotated: AnnotatedSequence) -> DesignSpec:
    return DesignSpec(
        organism=host_for_profile(annotated.vector_profile),
        vector_type=plasmid.vector_type or annotated.vector_profile,
        markers=plasmid.markers,
        promoter_type=plasmid.promoters[0] if plasmid.promoters else None,
        application=plasmid.use_cases[0] if plasmid.use_cases else None,
        source=plasmid.source,
        publication_doi=plasmid.publication_doi,
        constraints=[f"target_length_bp={plasmid.length}", f"topology={annotated.topology}"],
    )


def feature_summary(annotated: AnnotatedSequence) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {}
    for feature in annotated.features:
        buckets.setdefault(str(feature.type), [])
        if feature.name not in buckets[str(feature.type)]:
            buckets[str(feature.type)].append(feature.name)
    return {key: values[:8] for key, values in sorted(buckets.items())}


def warn_justifications(report: ValidationReport) -> list[str]:
    justifications = []
    for check in report.checks:
        if check.status != "WARN":
            continue
        if check.name == "repeat_and_instability":
            justifications.append(
                "Non-blocking repeat/instability warning retained because the cached public source is a complete deposited plasmid and the check is below the Phase 3 blocking threshold."
            )
        elif check.name == "regulatory_compatibility":
            justifications.append(
                "Regulatory warning retained only as expected report shape; source is a complete annotated vector record, but the local parser lacks enough downstream cassette context for a stronger PASS."
            )
        elif check.name == "codon_usage":
            justifications.append(
                "Codon-usage warning retained only for source-vector coding regions; this known-good record is not asserting de novo GOI optimization."
            )
        else:
            justifications.append(f"Expected non-blocking WARN from {check.name}: {check.message}")
    return justifications


def expected_warnings(report: ValidationReport) -> list[dict[str, str]]:
    warnings = []
    for check in report.checks:
        if check.status != "WARN":
            continue
        warnings.append(
            {
                "check": check.name,
                "status": "WARN",
                "rationale": expected_warning_rationale(check.name, check.message),
            }
        )
    return warnings


def expected_warning_rationale(check_name: str, message: str) -> str:
    if check_name == "repeat_and_instability" and "reviewed intentional vector architecture" in message:
        return (
            "Intentional reviewed vector architecture; the warning should remain visible for synthesis "
            "and stable-propagation review."
        )
    if check_name == "repeat_and_instability":
        return "Non-blocking repeat warning retained as a documented caveat for a complete public source vector."
    if check_name == "regulatory_compatibility":
        return "Non-blocking regulatory-context warning retained as a documented source-record caveat."
    if check_name == "codon_usage":
        return "Non-blocking codon-usage warning retained for source-vector coding context, not de novo GOI optimization."
    return f"Expected non-blocking WARN from {check_name}: {message}"


def tier_metadata(report: ValidationReport) -> dict[str, Any]:
    warnings = expected_warnings(report)
    if warnings:
        return {
            "tier": "B",
            "tier_label": "accepted-with-caveats",
            "expected_warnings": warnings,
        }
    return {
        "tier": "A",
        "tier_label": "strict-clean",
        "expected_warnings": [],
    }


def defensible(report: ValidationReport) -> bool:
    if report.overall == "PASS":
        return True
    if report.overall != "WARN":
        return False
    warning_names = {check.name for check in report.checks if check.status == "WARN"}
    return warning_names <= {"repeat_and_instability", "regulatory_compatibility", "codon_usage"}


def known_good_rationale(plasmid: Plasmid, annotated: AnnotatedSequence, report: ValidationReport) -> str:
    base = (
        f"Known-good because this is a complete annotated {annotated.vector_profile} record from the local corpus, "
        f"with cached source sequence metadata and required propagation/selection features parsed from the raw record."
    )
    if plasmid.source == "curated":
        base += " It is also part of the NCBI-backed curated seed manifest."
    if report.overall == "PASS":
        base += " The Phase 3 validation engine returns PASS for all checks under the profile-derived host/spec context."
    else:
        base += " The Phase 3 validation engine returns only non-blocking WARN checks, captured explicitly in warn_justifications."
    return base


def build_entry(
    plasmid: Plasmid,
    annotated: AnnotatedSequence,
    spec: DesignSpec,
    report: ValidationReport,
    metadata: dict[str, Any],
    curated_manifest: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    manifest_record = curated_manifest.get(plasmid.id)
    citations = []
    if manifest_record:
        citations.extend(manifest_record.get("citations") or [])
    accession = manifest_record.get("accession") if manifest_record else metadata.get("accession")
    if accession and not any(str(accession) in citation for citation in citations):
        citations.append(f"https://www.ncbi.nlm.nih.gov/nuccore/{accession}")
    entry = {
        "plasmid_id": plasmid.id,
        "source": plasmid.source,
        "name": plasmid.name,
        "accession": accession,
        "vector_profile": annotated.vector_profile,
        "known_good_basis": [
            "curated_seed_manifest" if manifest_record else "complete_annotated_corpus_record",
            "cached_raw_genbank_record",
            "phase3_constraint_engine_expected_pass_or_justified_warn",
        ],
        "rationale": known_good_rationale(plasmid, annotated, report),
        "citation_source_evidence": {
            "raw_ref": plasmid.raw_ref,
            "publication_doi": plasmid.publication_doi,
            "source_description": metadata.get("description"),
            "source_topology": metadata.get("topology"),
            "references": metadata.get("references", []),
            "citations": citations,
            "curated_manifest_notes": manifest_record.get("curation_notes") if manifest_record else None,
        },
        "feature_evidence": feature_summary(annotated),
        "warn_justifications": warn_justifications(report),
        "design_spec": spec.model_dump(mode="json"),
        "annotated_sequence": annotated.model_dump(mode="json"),
        "expected_validation_report": report.model_dump(mode="json"),
    }
    entry.update(tier_metadata(report))
    return entry


def main() -> None:
    env = load_env()
    curated_manifest = load_curated_manifest()
    client = raw_store(env)
    engine = ConstraintEngine()
    screened = Counter()
    if not OUT_PATH.exists():
        raise FileNotFoundError(f"{OUT_PATH} must exist before approved candidate admission")
    existing_entries = [json.loads(line) for line in OUT_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    target_ids = [entry["plasmid_id"] for entry in existing_entries]
    for candidate_id in APPROVED_CANDIDATE_IDS:
        if candidate_id not in target_ids:
            target_ids.append(candidate_id)

    with psycopg.connect(env["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select payload
                from plasmids
                where payload->>'id' = any(%s)
                """
                ,
                (target_ids,),
            )
            rows = cur.fetchall()

    plasmids = {Plasmid.model_validate(payload).id: Plasmid.model_validate(payload) for (payload,) in rows}
    missing = sorted(set(target_ids) - set(plasmids))
    if missing:
        raise RuntimeError(f"known-good target records missing from Postgres: {missing}")

    entries = []
    approved_set = set(APPROVED_CANDIDATE_IDS)
    for plasmid_id in target_ids:
        plasmid = plasmids[plasmid_id]
        screened["complete_payload"] += 1
        action = "admitting approved candidate" if plasmid.id in approved_set else "refreshing existing known-good"
        print(f"{action} {plasmid.id} length={plasmid.length}", flush=True)
        raw_text = get_raw_text(client, env, plasmid.raw_ref)
        if raw_text is None:
            raise RuntimeError(f"missing raw cache for known-good target {plasmid.id}: {plasmid.raw_ref}")
        try:
            annotated = parse_genbank_text(raw_text)
            metadata = genbank_metadata(raw_text)
        except Exception as exc:
            raise RuntimeError(f"failed to parse known-good target {plasmid.id}") from exc
        if annotated.vector_profile == "unknown":
            raise RuntimeError(f"known-good target parsed unknown profile: {plasmid.id}")
        spec = design_spec(plasmid, annotated)
        report = engine.validate(annotated, spec)
        screened[f"validation_{report.overall}"] += 1
        if not defensible(report):
            raise RuntimeError(f"known-good target is no longer defensible: {plasmid.id} -> {report.overall}")
        entries.append(build_entry(plasmid, annotated, spec, report, metadata, curated_manifest))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        "\n".join(json.dumps(entry, sort_keys=True, separators=(",", ":")) for entry in entries) + ("\n" if entries else ""),
        encoding="utf-8",
    )

    BLOCKER_PATH.write_text(
        json.dumps(
            {
                "status": "quality_over_arbitrary_count_policy",
                "output_path": str(OUT_PATH),
                "defensible_known_good_count": len(entries),
                "required_count": None,
                "reason": "Human policy accepts a profile-diverse curated gold set whose size is determined by source quality; tiering preserves strict-clean versus accepted-with-caveats semantics.",
                "approved_candidate_ids": list(APPROVED_CANDIDATE_IDS),
                "screened": dict(screened),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    profile_counts = Counter(entry["vector_profile"] for entry in entries)
    status_counts = Counter(entry["expected_validation_report"]["overall"] for entry in entries)
    print(
        json.dumps(
            {
                "output_path": str(OUT_PATH),
                "entries": len(entries),
                "profiles": dict(sorted(profile_counts.items())),
                "statuses": dict(sorted(status_counts.items())),
                "screened": dict(sorted(screened.items())),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
