from __future__ import annotations

from statistics import mean

from packages.core.schemas import AnnotatedFeature, AnnotatedSequence, DesignSpec, ValidationCheck
from packages.validation.common import fail_check, features_of, geometric_mean, host_context, pass_check, region, warn_check


CHECK_NAME = "codon_usage"
STOP_CODONS = {"TAA", "TAG", "TGA"}


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

    scores = [(feature, codon_adaptation_index(sequence.sequence[feature.start : feature.end], table)) for feature in goi_features]
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
