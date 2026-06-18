from __future__ import annotations

import re
from statistics import mean

from packages.core.schemas import AnnotatedFeature, AnnotatedSequence, DesignSpec, ValidationCheck
from packages.validation.common import fail_check, features_of, geometric_mean, host_context, pass_check, region, warn_check


CHECK_NAME = "codon_usage"
STOP_CODONS = {"TAA", "TAG", "TGA"}

SOURCE_CONTEXT_SKIP_TERMS = {
    "rep",
    "repa",
    "repe",
    "replication",
    "lac i",
    "laci",
    "lac repressor",
    "lac z",
    "lacz",
    "lac z alpha",
    "lacz alpha",
    "beta galactosidase alpha",
    "screening",
    "mob",
    "moba",
    "tra",
    "transfer",
    "sop",
    "sopa",
    "sopb",
    "par",
    "partition",
    "ccdb",
    "ccd b",
    "marker",
    "ampr",
    "ampicillin",
    "bla",
    "kanr",
    "kanamycin",
    "cat",
    "chloramphenicol",
    "tetracycline",
    "tetr",
    "spec",
    "spectinomycin",
    "aad",
}

PAYLOAD_TERMS = {
    "payload",
    "gene of interest",
    "goi",
    "insert",
    "expression target",
    "target protein",
    "protein of interest",
}

REPORTER_TERMS = {
    "luciferase",
    "luc",
    "gfp",
    "egfp",
    "mcherry",
    "dsred",
    "rfp",
    "yfp",
    "bfp",
}


HOST_CODON_WEIGHTS: dict[str, dict[str, float]] = {
    "bacterial": {
        "GCT": 0.8,
        "GCC": 1.0,
        "GCA": 0.65,
        "GCG": 0.9,
        "CGT": 0.9,
        "CGC": 1.0,
        "CGA": 0.25,
        "CGG": 0.25,
        "AGA": 0.15,
        "AGG": 0.12,
        "GGT": 0.8,
        "GGC": 1.0,
        "GGA": 0.35,
        "GGG": 0.3,
        "CTG": 1.0,
        "TTA": 0.2,
        "TTG": 0.35,
        "CTA": 0.1,
        "CTC": 0.4,
        "CTT": 0.45,
    },
    "yeast": {
        "GCT": 1.0,
        "GCC": 0.6,
        "GCA": 0.8,
        "GCG": 0.25,
        "AGA": 1.0,
        "AGG": 0.45,
        "CGT": 0.45,
        "CGC": 0.25,
        "CGA": 0.3,
        "CGG": 0.2,
        "TTG": 1.0,
        "TTA": 0.9,
        "CTT": 0.7,
        "CTC": 0.35,
        "CTA": 0.4,
        "CTG": 0.45,
    },
    "mammalian": {
        "GCC": 1.0,
        "GCT": 0.65,
        "GCA": 0.55,
        "GCG": 0.25,
        "CGC": 1.0,
        "CGG": 0.95,
        "AGA": 0.75,
        "AGG": 0.8,
        "CGT": 0.35,
        "CGA": 0.4,
        "CTG": 1.0,
        "CTC": 0.55,
        "CTT": 0.45,
        "TTG": 0.4,
        "TTA": 0.15,
        "CTA": 0.25,
    },
}


def run_codon_check(sequence: AnnotatedSequence, spec: DesignSpec) -> ValidationCheck:
    goi_features = features_of(sequence, "GOI")
    if not goi_features:
        return pass_check(CHECK_NAME, "No GOI coding region was annotated; codon-usage scoring skipped.")
    context = host_context(spec)
    table = HOST_CODON_WEIGHTS.get(context.host_class)
    if table is None:
        return warn_check(CHECK_NAME, f"No codon-usage table is configured for host '{spec.organism}'.")

    payload_features, non_payload_reporters, skipped = payload_goi_features(goi_features, spec, sequence)
    if not payload_features:
        reporter_scores = [
            (feature, codon_adaptation_index(sequence.sequence[feature.start : feature.end], table))
            for feature in non_payload_reporters
        ]
        if reporter_scores:
            worst_reporter, worst_score = min(reporter_scores, key=lambda item: item[1])
            if worst_score < 0.75:
                return warn_check(
                    CHECK_NAME,
                    (
                        f"Source reporter ORF '{worst_reporter.name}' is not treated as the requested payload; "
                        f"codon adaptation is {worst_score:.2f} for {context.host_class} expression."
                    ),
                    region(worst_reporter.start, worst_reporter.end, len(sequence.sequence)),
                )
        if skipped:
            names = ", ".join(feature.name for feature in skipped[:3])
            suffix = "..." if len(skipped) > 3 else ""
            return pass_check(
                CHECK_NAME,
                f"No intended payload GOI was annotated; skipped source-vector context CDS ({names}{suffix}).",
            )
        return pass_check(CHECK_NAME, "No intended payload GOI was annotated; codon-usage scoring skipped.")

    scores = [(feature, codon_adaptation_index(sequence.sequence[feature.start : feature.end], table)) for feature in payload_features]
    worst_feature, worst_score = min(scores, key=lambda item: item[1])
    rare = rare_codon_cluster(sequence.sequence[worst_feature.start : worst_feature.end], table)
    if worst_score < 0.55:
        return fail_check(
            CHECK_NAME,
            f"GOI codon adaptation score is low for {context.host_class} expression ({worst_score:.2f}).",
            region(worst_feature.start, worst_feature.end, len(sequence.sequence)),
        )
    if worst_score < 0.75 or rare is not None:
        message = f"GOI codon adaptation score is marginal for {context.host_class} expression ({worst_score:.2f})."
        if rare is not None:
            message += " Rare-codon cluster detected."
        return warn_check(CHECK_NAME, message, region(worst_feature.start, worst_feature.end, len(sequence.sequence)))
    return pass_check(CHECK_NAME, f"GOI codon adaptation score is acceptable ({mean(score for _, score in scores):.2f}).")


def payload_goi_features(
    goi_features: list[AnnotatedFeature],
    spec: DesignSpec,
    sequence: AnnotatedSequence,
) -> tuple[list[AnnotatedFeature], list[AnnotatedFeature], list[AnnotatedFeature]]:
    if not source_record_context(spec):
        return goi_features, [], []

    payload: list[AnnotatedFeature] = []
    reporters: list[AnnotatedFeature] = []
    skipped: list[AnnotatedFeature] = []
    for feature in goi_features:
        if explicit_payload_feature(feature, spec):
            payload.append(feature)
        elif reporter_feature(feature) and reporter_intent(spec, sequence):
            payload.append(feature)
        elif reporter_feature(feature):
            reporters.append(feature)
        else:
            skipped.append(feature)
    return payload, reporters, skipped


def source_record_context(spec: DesignSpec) -> bool:
    return spec.source is not None and str(spec.source) != "generated"


def explicit_payload_feature(feature: AnnotatedFeature, spec: DesignSpec) -> bool:
    text = normalized_feature_text(feature)
    if any(contains_term(text, term) for term in PAYLOAD_TERMS):
        return True
    for gene in spec.genes:
        gene_text = normalize_text(gene)
        if gene_text and gene_text in text:
            return True
    if any(contains_term(text, term) for term in SOURCE_CONTEXT_SKIP_TERMS):
        return False
    return False


def reporter_intent(spec: DesignSpec, sequence: AnnotatedSequence) -> bool:
    text = normalize_text(" ".join([spec.vector_type or "", spec.application or "", sequence.vector_profile, *spec.tags]))
    return any(contains_term(text, term) for term in {"reporter", "luciferase", "fluorescent", "gfp", "egfp"})


def reporter_feature(feature: AnnotatedFeature) -> bool:
    text = normalized_feature_text(feature)
    return any(contains_term(text, term) for term in REPORTER_TERMS)


def normalized_feature_text(feature: AnnotatedFeature) -> str:
    return normalize_text(feature.name)


def normalize_text(value: str) -> str:
    return value.lower().replace("_", " ").replace("-", " ").replace("'", "").strip()


def contains_term(text: str, term: str) -> bool:
    normalized = normalize_text(term)
    if " " in normalized:
        return normalized in text
    return re.search(rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])", text) is not None


def codon_adaptation_index(cds: str, table: dict[str, float]) -> float:
    codons = [cds[index : index + 3] for index in range(0, len(cds) - 2, 3)]
    weights = [table.get(codon, 0.5) for codon in codons if codon not in STOP_CODONS]
    return geometric_mean(weights)


def rare_codon_cluster(cds: str, table: dict[str, float]) -> tuple[int, int] | None:
    codons = [cds[index : index + 3] for index in range(0, len(cds) - 2, 3)]
    rare_flags = [table.get(codon, 0.5) < 0.2 for codon in codons]
    for start in range(0, max(0, len(rare_flags) - 9)):
        if sum(rare_flags[start : start + 10]) >= 3:
            return start * 3, (start + 10) * 3
    return None
