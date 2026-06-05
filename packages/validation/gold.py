from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from packages.core.schemas import AnnotatedFeature, AnnotatedSequence, DesignSpec


DEFAULT_GOLD_PATH = Path("data/eval/validation/validation_gold.jsonl")
DEFAULT_DOC_PATH = Path("data/eval/validation/gold_set_construction.md")


def feature(kind: str, start: int, end: int, name: str) -> AnnotatedFeature:
    return AnnotatedFeature(type=kind, start=start, end=end, strand=1, name=name, confidence=0.99)


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


def clean_case(index: int) -> dict[str, Any]:
    sequence = stable_dna(520, 1000 + index)
    annotated = AnnotatedSequence(
        sequence=sequence,
        topology="circular",
        vector_profile="bacterial_cloning_vector",
        annotation_complete=True,
        features=[
            feature("ORI", 0, 70, "pUC origin"),
            feature("marker", 90, 180, "AmpR"),
            feature("MCS", 220, 280, "multiple cloning site"),
        ],
    )
    spec = DesignSpec(organism="Escherichia coli", vector_type="bacterial cloning vector", cloning_method="Gibson assembly")
    return {
        "id": f"good_cloning_{index:03d}",
        "expected": "PASS",
        "category": "known_good_synthetic_cloning_backbone",
        "design_spec": spec.model_dump(mode="json"),
        "annotated_sequence": annotated.model_dump(mode="json"),
    }


def restriction_bad_case(index: int) -> dict[str, Any]:
    sequence = stable_dna(80, index) + "GAATTC" + stable_dna(180, index + 50) + "GGATCC" + stable_dna(180, index + 90)
    annotated = AnnotatedSequence(
        sequence=sequence,
        topology="circular",
        vector_profile="bacterial_cloning_vector",
        annotation_complete=True,
        features=[
            feature("ORI", 0, 60, "pUC origin"),
            feature("marker", 70, 150, "AmpR"),
            feature("MCS", 266, 272, "multiple cloning site"),
        ],
    )
    spec = DesignSpec(organism="Escherichia coli", cloning_method="EcoRI and BamHI cloning")
    return _bad(index, "restriction_conflict", spec, annotated)


def repeat_bad_case(index: int) -> dict[str, Any]:
    sequence = stable_dna(200, index) + "A" * 12 + stable_dna(200, index + 10)
    annotated = _bad_backbone(sequence)
    spec = DesignSpec(organism="Escherichia coli", cloning_method="Gibson assembly")
    return _bad(index, "homopolymer_instability", spec, annotated)


def regulatory_bad_case(index: int) -> dict[str, Any]:
    sequence = stable_dna(520, index)
    annotated = AnnotatedSequence(
        sequence=sequence,
        topology="circular",
        vector_profile="bacterial_expression_vector",
        annotation_complete=True,
        features=[
            feature("ORI", 0, 60, "pUC origin"),
            feature("marker", 70, 150, "AmpR"),
            feature("promoter", 180, 230, "CMV promoter"),
        ],
    )
    spec = DesignSpec(organism="Escherichia coli", vector_type="bacterial expression vector")
    return _bad(index, "regulatory_incompatibility", spec, annotated)


def codon_bad_case(index: int) -> dict[str, Any]:
    cds = "AGGAGAAGGCTA" * 12
    sequence = stable_dna(160, index) + cds + stable_dna(160, index + 20)
    annotated = AnnotatedSequence(
        sequence=sequence,
        topology="circular",
        vector_profile="bacterial_expression_vector",
        annotation_complete=True,
        features=[
            feature("ORI", 0, 60, "pUC origin"),
            feature("marker", 70, 150, "AmpR"),
            feature("promoter", 155, 175, "lac promoter"),
            feature("GOI", 160, 160 + len(cds), "rare-codon GOI"),
            feature("terminator", 160 + len(cds) + 5, 160 + len(cds) + 30, "T7 terminator"),
        ],
    )
    spec = DesignSpec(organism="Escherichia coli", vector_type="bacterial expression vector")
    return _bad(index, "codon_usage", spec, annotated)


def _bad_backbone(sequence: str) -> AnnotatedSequence:
    return AnnotatedSequence(
        sequence=sequence,
        topology="circular",
        vector_profile="bacterial_cloning_vector",
        annotation_complete=True,
        features=[
            feature("ORI", 0, 60, "pUC origin"),
            feature("marker", 70, 150, "AmpR"),
            feature("MCS", 180, 220, "multiple cloning site"),
        ],
    )


def _bad(index: int, category: str, spec: DesignSpec, annotated: AnnotatedSequence) -> dict[str, Any]:
    return {
        "id": f"bad_{category}_{index:03d}",
        "expected": "FAIL",
        "category": category,
        "design_spec": spec.model_dump(mode="json"),
        "annotated_sequence": annotated.model_dump(mode="json"),
    }


def build_gold_cases() -> list[dict[str, Any]]:
    cases = [clean_case(index) for index in range(50)]
    bad_builders = [restriction_bad_case, repeat_bad_case, regulatory_bad_case, codon_bad_case]
    for index in range(50):
        cases.append(bad_builders[index % len(bad_builders)](index))
    return cases


def write_gold_set(path: Path = DEFAULT_GOLD_PATH, doc_path: Path = DEFAULT_DOC_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cases = build_gold_cases()
    path.write_text("\n".join(json.dumps(case, sort_keys=True) for case in cases) + "\n", encoding="utf-8")
    doc_path.write_text(
        "# Phase 3 Validation Gold Set Construction\n\n"
        "This deterministic seed gold set contains 100 schema-valid annotated constructs: 50 expected PASS cases "
        "and 50 expected FAIL cases. The PASS cases are clean bacterial cloning-backbone constructs with compatible "
        "ORI, marker, and MCS annotations and no explicit restriction-enzyme cloning context. The FAIL cases are "
        "deliberately mutated from the same backbone pattern to exercise one blocking validation path each: internal "
        "restriction-enzyme conflict, synthesis-instability homopolymer, promoter-host incompatibility, and rare-codon "
        "GOI sequence. The set is generated by `packages.validation.gold` so it can be regenerated exactly.\n\n"
        "This is an initial deterministic Phase 3 gate set, not a substitute for later wet-lab validated provider examples. "
        "Future sessions should add real known-good and provider-rejected constructs as provenance allows.\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the deterministic Phase 3 validation gold set.")
    parser.add_argument("--gold-path", type=Path, default=DEFAULT_GOLD_PATH)
    parser.add_argument("--doc-path", type=Path, default=DEFAULT_DOC_PATH)
    args = parser.parse_args()
    write_gold_set(args.gold_path, args.doc_path)
    print(f"Wrote validation gold set to {args.gold_path}")


if __name__ == "__main__":
    main()
