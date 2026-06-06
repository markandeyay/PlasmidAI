from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.core.schemas import AnnotatedSequence, DesignSpec, ValidationReport
from packages.validation.common import CHECK_VERSION
from packages.validation.engine import ConstraintEngine


SOURCE_GOLD_PATH = Path("data/eval/validation/validation_gold.jsonl")
OUTPUT_PATH = Path("data/eval/validation/curated_known_bad.jsonl")
UNCERTAINTY_LOG_PATH = Path("data/eval/validation/curated_known_bad_uncertainty.md")

ENGINE_CHECKS = {
    "restriction_conflicts": "restriction_site_conflicts",
    "repeat_instability": "repeat_and_instability",
    "regulatory_incompatibility": "regulatory_compatibility",
    "codon_usage": "codon_usage",
}

RESTRICTION_ENZYMES = [
    ("EcoRI", "GAATTC"),
    ("BamHI", "GGATCC"),
    ("HindIII", "AAGCTT"),
    ("XhoI", "CTCGAG"),
    ("KpnI", "GGTACC"),
    ("PstI", "CTGCAG"),
    ("SalI", "GTCGAC"),
    ("XbaI", "TCTAGA"),
    ("NcoI", "CCATGG"),
    ("NdeI", "CATATG"),
    ("NotI", "GCGGCCGC"),
    ("SacI", "GAGCTC"),
    ("SpeI", "ACTAGT"),
]

CITATIONS = {
    "restriction_conflicts": [
        "SYSTEM_DESIGN.md Section 8.2 item 1 and Section 8.3.",
        "research/findings/validation_restriction.md: restriction ligation fails when an intended enzyme cuts outside the allowed MCS/cloning region.",
    ],
    "repeat_instability": [
        "SYSTEM_DESIGN.md Section 8.2 item 2 and Section 8.3.",
        "research/findings/validation_repeats.md: homopolymers, GC extremes, and exact direct/inverted repeats are provider-facing synthesis and propagation-instability risks.",
    ],
    "regulatory_incompatibility": [
        "SYSTEM_DESIGN.md Section 8.2 item 4 and Section 8.3.",
        "research/findings/validation_regulatory.md: host-matched promoters, selectable markers, and autonomous origins are required regulatory/vector-compatibility evidence.",
    ],
    "codon_usage": [
        "SYSTEM_DESIGN.md Section 8.2 item 3 and Section 8.3.",
        "research/findings/validation_codon.md: low CAI-like scores and rare-codon clusters are deterministic host-expression validation failures or warnings.",
    ],
}


def stable_dna(length: int, seed: int) -> str:
    bases = "ACGT"
    out: list[str] = []
    while len(out) < length:
        seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
        candidate = bases[(seed >> 16) % 4]
        if len(out) >= 3 and out[-1] == out[-2] == out[-3] == candidate:
            candidate = bases[(bases.index(candidate) + 1) % 4]
        out.append(candidate)
    return "".join(out)


def replace_span(sequence: str, start: int, replacement: str) -> str:
    end = start + len(replacement)
    if end > len(sequence):
        raise ValueError(f"replacement at {start} extends beyond sequence length {len(sequence)}")
    return sequence[:start] + replacement + sequence[end:]


def load_known_good_sources() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in SOURCE_GOLD_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("expected") == "PASS":
            records.append(record)
    if len(records) < 50:
        raise RuntimeError(f"expected at least 50 known-good source records in {SOURCE_GOLD_PATH}, found {len(records)}")
    return records


def source_at(sources: list[dict[str, Any]], index: int) -> dict[str, Any]:
    return deepcopy(sources[index % len(sources)])


def base_entry(
    *,
    case_id: str,
    source: dict[str, Any],
    defect_type: str,
    check_category: str,
    construction_procedure: str,
    expected_failing_checks: list[str],
    design_spec: dict[str, Any],
    annotated_sequence: dict[str, Any],
    rationale: str,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "source_plasmid_id": source["id"],
        "source_record_path": str(SOURCE_GOLD_PATH).replace("\\", "/"),
        "defect_type": defect_type,
        "check_category": check_category,
        "construction_procedure": construction_procedure,
        "expected_failing_checks": expected_failing_checks,
        "expected_validation_report_shape_status": {
            "overall": "FAIL",
            "generated_by_model_version": CHECK_VERSION,
            "checks": [
                {"name": name, "status": "FAIL", "region": "required"}
                for name in expected_failing_checks
            ],
            "report_contract": "ValidationReport with overall FAIL, one ValidationCheck per engine module, and at least the expected failing check(s) at status FAIL.",
        },
        "rationale_citation": {
            "rationale": rationale,
            "citations": CITATIONS[check_category],
        },
        "design_spec": design_spec,
        "annotated_sequence": annotated_sequence,
    }


def build_restriction_cases(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for index, (enzyme, motif) in enumerate(RESTRICTION_ENZYMES):
        source = source_at(sources, index)
        annotated = deepcopy(source["annotated_sequence"])
        spec = deepcopy(source["design_spec"])
        insertion_start = 300 + (index * 11) % 80
        annotated["sequence"] = replace_span(annotated["sequence"], insertion_start, motif)
        spec["cloning_method"] = f"{enzyme} restriction cloning"
        cases.append(
            base_entry(
                case_id=f"ckb_restriction_{index:03d}",
                source=source,
                defect_type=f"restriction_conflict_internal_{enzyme.lower()}_site",
                check_category="restriction_conflicts",
                construction_procedure=(
                    f"Starting from known-good source {source['id']}, overwrite neutral backbone bases "
                    f"{insertion_start}-{insertion_start + len(motif)} with the {enzyme} recognition site {motif}, "
                    f"then set DesignSpec.cloning_method to '{enzyme} restriction cloning'. The inserted site is outside "
                    "the annotated MCS, so the intended cloning enzyme has an internal/vector-backbone conflict."
                ),
                expected_failing_checks=[ENGINE_CHECKS["restriction_conflicts"]],
                design_spec=spec,
                annotated_sequence=annotated,
                rationale=(
                    f"{enzyme} is explicitly requested for restriction cloning, but at least one {enzyme} site is outside "
                    "the annotated MCS. Cutting the final construct would linearize or fragment non-target sequence rather "
                    "than cutting only the intended cloning slot."
                ),
            )
        )
    return cases


def build_repeat_cases(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    variants = (
        [("homopolymer_12nt", "A" * 12, 310), ("homopolymer_12nt", "T" * 12, 325), ("homopolymer_12nt", "C" * 12, 340), ("homopolymer_12nt", "G" * 12, 355), ("homopolymer_12nt", "A" * 13, 370)]
        + [("local_gc_extreme_100bp", "GC" * 50, 300), ("local_gc_extreme_100bp", "AT" * 50, 305), ("local_gc_extreme_100bp", "CG" * 50, 310), ("local_gc_extreme_100bp", "TA" * 50, 315)]
        + [("direct_repeat_40bp", "", 320), ("direct_repeat_40bp", "", 330), ("direct_repeat_40bp", "", 340), ("direct_repeat_40bp", "", 350)]
    )
    for offset, (variant, payload, start) in enumerate(variants):
        source = source_at(sources, 13 + offset)
        annotated = deepcopy(source["annotated_sequence"])
        spec = deepcopy(source["design_spec"])
        if variant == "direct_repeat_40bp":
            payload = annotated["sequence"][20 + offset : 60 + offset]
        annotated["sequence"] = replace_span(annotated["sequence"], start, payload)
        cases.append(
            base_entry(
                case_id=f"ckb_repeat_{offset:03d}",
                source=source,
                defect_type=f"repeat_instability_{variant}",
                check_category="repeat_instability",
                construction_procedure=(
                    f"Starting from known-good source {source['id']}, overwrite bases {start}-{start + len(payload)} "
                    f"with a deterministic {variant.replace('_', ' ')} payload while leaving cloning context as Gibson assembly."
                ),
                expected_failing_checks=[ENGINE_CHECKS["repeat_instability"]],
                design_spec=spec,
                annotated_sequence=annotated,
                rationale=(
                    "The introduced motif crosses the current blocking threshold for repeat/instability validation: "
                    "12+ nt homopolymers, 100 bp windows with extreme GC content, or exact 40 bp direct repeats are "
                    "conservative synthesis-readiness and propagation-stability failures."
                ),
            )
        )
    return cases


def without_features(annotated: dict[str, Any], feature_type: str) -> dict[str, Any]:
    annotated = deepcopy(annotated)
    annotated["features"] = [feature for feature in annotated["features"] if feature["type"] != feature_type]
    return annotated


def add_feature(annotated: dict[str, Any], *, feature_type: str, start: int, end: int, name: str) -> dict[str, Any]:
    annotated = deepcopy(annotated)
    annotated["features"].append({"type": feature_type, "start": start, "end": end, "strand": 1, "name": name, "confidence": 0.99})
    annotated["features"] = sorted(annotated["features"], key=lambda item: (item["start"], item["end"], item["type"], item["name"]))
    return annotated


def build_regulatory_cases(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for offset in range(13):
        source = source_at(sources, 26 + offset)
        annotated = deepcopy(source["annotated_sequence"])
        spec = deepcopy(source["design_spec"])
        if offset < 5:
            spec["organism"] = "Escherichia coli"
            spec["vector_type"] = "bacterial expression vector"
            annotated = add_feature(annotated, feature_type="promoter", start=300, end=350, name="CMV promoter")
            defect = "regulatory_incompatibility_cmv_promoter_in_ecoli"
            procedure = (
                f"Starting from known-good source {source['id']}, add an annotated CMV promoter feature at bases 300-350 "
                "and request an Escherichia coli bacterial expression context."
            )
            rationale = "CMV is a mammalian RNA polymerase II promoter and is not a bacterial expression promoter for an E. coli host context."
        elif offset < 9:
            spec["organism"] = "Homo sapiens"
            spec["vector_type"] = "mammalian expression vector"
            annotated = add_feature(annotated, feature_type="promoter", start=300, end=350, name="lac promoter")
            defect = "regulatory_incompatibility_lac_promoter_in_mammalian_host"
            procedure = (
                f"Starting from known-good source {source['id']}, add an annotated lac promoter feature at bases 300-350 "
                "and request a Homo sapiens mammalian expression context."
            )
            rationale = "The lac promoter is a bacterial promoter and is not host-compatible as the expression promoter in a mammalian host context."
        elif offset < 11:
            marker = next(feature for feature in annotated["features"] if feature["type"] == "marker")
            annotated["sequence"] = replace_span(annotated["sequence"], marker["start"], stable_dna(marker["end"] - marker["start"], 9000 + offset))
            annotated = without_features(annotated, "marker")
            spec["organism"] = "Escherichia coli"
            spec["vector_type"] = "bacterial cloning vector"
            defect = "regulatory_incompatibility_missing_selectable_marker"
            procedure = (
                f"Starting from known-good source {source['id']}, replace the selectable-marker interval with neutral DNA "
                "and remove the marker annotation."
            )
            rationale = "A plasmid intended for bacterial propagation requires selectable-marker evidence; without it the construct cannot be selected or maintained reliably."
        else:
            annotated = without_features(annotated, "ORI")
            annotated = add_feature(annotated, feature_type="ORI", start=0, end=70, name="SV40 origin")
            spec["organism"] = "Escherichia coli"
            spec["vector_type"] = "bacterial cloning vector"
            defect = "regulatory_incompatibility_no_bacterial_origin"
            procedure = (
                f"Starting from known-good source {source['id']}, replace the bacterial ORI annotation with an SV40 origin annotation "
                "while keeping an Escherichia coli propagation context."
            )
            rationale = "SV40 origin evidence is not an autonomous bacterial replication origin; an E. coli plasmid needs a bacterial ORI such as pUC/pMB1/ColE1."
        cases.append(
            base_entry(
                case_id=f"ckb_regulatory_{offset:03d}",
                source=source,
                defect_type=defect,
                check_category="regulatory_incompatibility",
                construction_procedure=procedure,
                expected_failing_checks=[ENGINE_CHECKS["regulatory_incompatibility"]],
                design_spec=spec,
                annotated_sequence=annotated,
                rationale=rationale,
            )
        )
    return cases


def rare_codon_cds(seed: int, codons: int = 50) -> str:
    choices = ["AGA", "AGG", "CTA"]
    out: list[str] = []
    state = seed
    for _ in range(codons):
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        candidate = choices[(state >> 8) % len(choices)]
        if len(out) >= 2 and out[-1] == out[-2] == candidate:
            candidate = choices[(choices.index(candidate) + 1) % len(choices)]
        out.append(candidate)
    return "".join(out)


def build_codon_cases(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for offset in range(13):
        source = source_at(sources, 39 + offset)
        annotated = deepcopy(source["annotated_sequence"])
        spec = deepcopy(source["design_spec"])
        cds = rare_codon_cds(7000 + offset)
        goi_start = 300
        goi_end = goi_start + len(cds)
        annotated["sequence"] = replace_span(annotated["sequence"], goi_start, cds)
        annotated = add_feature(annotated, feature_type="promoter", start=282, end=298, name="lac promoter")
        annotated = add_feature(annotated, feature_type="GOI", start=goi_start, end=goi_end, name=f"E_coli_rare_codon_payload_{offset:02d}")
        annotated = add_feature(annotated, feature_type="terminator", start=goi_end + 5, end=goi_end + 30, name="T7 terminator")
        spec["organism"] = "Escherichia coli"
        spec["vector_type"] = "bacterial expression vector"
        spec["cloning_method"] = "Gibson assembly"
        cases.append(
            base_entry(
                case_id=f"ckb_codon_{offset:03d}",
                source=source,
                defect_type="codon_usage_ecoli_low_cai_rare_codon_cluster",
                check_category="codon_usage",
                construction_procedure=(
                    f"Starting from known-good source {source['id']}, overwrite bases {goi_start}-{goi_end} with a "
                    "150 bp annotated GOI dominated by E. coli rare arginine/leucine codons (AGA, AGG, CTA), then add "
                    "compatible lac promoter and T7 terminator annotations so codon usage is the intended blocking defect."
                ),
                expected_failing_checks=[ENGINE_CHECKS["codon_usage"]],
                design_spec=spec,
                annotated_sequence=annotated,
                rationale=(
                    "The inserted GOI is dominated by codons that the current E. coli table scores as low-adaptiveness, "
                    "creating a low CAI-like score and rare-codon clusters that are validation-relevant for bacterial expression."
                ),
            )
        )
    return cases


def report_check_statuses(report: ValidationReport) -> dict[str, str]:
    return {check.name: str(check.status) for check in report.checks}


def verify_cases(cases: list[dict[str, Any]]) -> None:
    engine = ConstraintEngine()
    failures: list[str] = []
    for case in cases:
        annotated = AnnotatedSequence.model_validate(case["annotated_sequence"])
        spec = DesignSpec.model_validate(case["design_spec"])
        report = engine.validate(annotated, spec)
        statuses = report_check_statuses(report)
        expected = set(case["expected_failing_checks"])
        actual_failures = {name for name, status in statuses.items() if status == "FAIL"}
        if str(report.overall) != "FAIL" or not expected.issubset(actual_failures):
            failures.append(
                f"{case['case_id']}: expected {sorted(expected)} in FAIL with overall FAIL, "
                f"got overall={report.overall} statuses={statuses}"
            )
        case["expected_validation_report_shape_status"]["observed_current_engine_statuses"] = statuses
    if failures:
        raise RuntimeError("Curated known-bad verification failed:\n" + "\n".join(failures))


def write_uncertainty_log() -> None:
    UNCERTAINTY_LOG_PATH.write_text(
        "# Curated Known-Bad Validation Uncertainty Log\n\n"
        "The JSONL set intentionally excludes ambiguous or context-dependent biology that should not be treated as known-bad.\n\n"
        "- Incidental restriction sites in Gibson/HiFi/LIC, Gateway/TOPO, or synthesis-only designs were excluded unless a named enzyme constraint made the site blocking.\n"
        "- Missing downstream terminator/polyA cases were excluded from this blocking set because the current engine reports that path as WARN and cloning-only contexts can be valid without a terminator.\n"
        "- Required viral LTR/ITR-like repeats were excluded because they can be biologically necessary even when they create propagation or synthesis review risk.\n"
        "- CMV-context silencing, promoter strength, induction dose, and cell-line-specific expression concerns were excluded because they are advisory rather than deterministic FAIL criteria here.\n"
        "- Broad-host-range origin interpretation outside the current calibrated bacterial/yeast/mammalian host classes was excluded.\n",
        encoding="utf-8",
    )


def main() -> None:
    sources = load_known_good_sources()
    cases = [
        *build_restriction_cases(sources),
        *build_repeat_cases(sources),
        *build_regulatory_cases(sources),
        *build_codon_cases(sources),
    ]
    verify_cases(cases)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(json.dumps(case, sort_keys=True) for case in cases) + "\n", encoding="utf-8")
    write_uncertainty_log()
    counts: dict[str, int] = {}
    for case in cases:
        counts[case["check_category"]] = counts.get(case["check_category"], 0) + 1
    print(json.dumps({"output": str(OUTPUT_PATH), "count": len(cases), "category_counts": counts}, sort_keys=True))


if __name__ == "__main__":
    main()
