from __future__ import annotations

from packages.core.schemas import AnnotatedFeature, AnnotatedSequence, DesignSpec, ValidationCheck
from packages.validation.common import fail_check, features_of, host_context, pass_check, region, text_for_feature, warn_check


CHECK_NAME = "regulatory_compatibility"

BACTERIAL_PROMOTERS = {"lac", "tac", "trc", "arab", "pbad", "lpp"}
MAMMALIAN_PROMOTERS = {"cmv", "ef1", "ef1a", "cag", "pgk", "sv40", "tre", "h1", "u6"}
YEAST_PROMOTERS = {"gal1", "adh1", "tef1", "gpd", "cup1"}
AUXILIARY_PROMOTERS = {"t7", "t3", "sp6"}

BACTERIAL_ORIS = {"puc", "pmb1", "cole1", "pbr322", "p15a", "f1", "rk2", "r6k"}
YEAST_ORIS = {"2 micron", "2-micron", "cen", "ars", "arsh4"}
MAMMALIAN_REPLICATION = {"sv40"}


def run_regulatory_check(sequence: AnnotatedSequence, spec: DesignSpec) -> ValidationCheck:
    context = host_context(spec)
    if not features_of(sequence, "marker"):
        return fail_check(
            CHECK_NAME,
            "No selectable marker is annotated; add an appropriate marker for propagation or selection.",
            failure_context=validation_failure_context(spec),
        )
    if not compatible_origin_present(sequence, context.host_class):
        return fail_check(
            CHECK_NAME,
            f"No origin or maintenance element compatible with {context.host_class or 'requested'} host context was detected.",
            failure_context=validation_failure_context(spec),
        )
    promoter_issue = first_incompatible_promoter(sequence, spec, context.host_class)
    if promoter_issue is not None:
        status, incompatible_promoter, message = promoter_issue
        if status == "WARN":
            return warn_check(
                CHECK_NAME,
                message,
                region(incompatible_promoter.start, incompatible_promoter.end, len(sequence.sequence)),
            )
        return fail_check(
            CHECK_NAME,
            message,
            region(incompatible_promoter.start, incompatible_promoter.end, len(sequence.sequence)),
            failure_context="design_construct_failure",
        )
    terminator_issue = downstream_terminator_issue(sequence)
    if terminator_issue is not None:
        status, message, feature = terminator_issue
        check_region = region(feature.start, feature.end, len(sequence.sequence))
        if status == "FAIL":
            return fail_check(CHECK_NAME, message, check_region)
        return warn_check(CHECK_NAME, message, check_region)
    return pass_check(CHECK_NAME, "Regulatory elements are compatible with the requested host context.")


def validation_failure_context(spec: DesignSpec) -> str:
    if spec.source is not None and str(spec.source) != "generated":
        return "source_record_uncertainty"
    return "design_construct_failure"


def compatible_origin_present(sequence: AnnotatedSequence, host_class: str) -> bool:
    ori_text = " ".join(text_for_feature(feature) for feature in features_of(sequence, "ORI"))
    if host_class == "yeast":
        return any(token in ori_text for token in YEAST_ORIS) and bool(any(token in ori_text for token in BACTERIAL_ORIS))
    if host_class == "mammalian":
        return any(token in ori_text for token in BACTERIAL_ORIS | MAMMALIAN_REPLICATION)
    if host_class == "bacterial":
        return any(token in ori_text for token in BACTERIAL_ORIS)
    return bool(ori_text)


def first_incompatible_promoter(
    sequence: AnnotatedSequence,
    spec: DesignSpec,
    host_class: str,
) -> tuple[str, AnnotatedFeature, str] | None:
    for promoter in features_of(sequence, "promoter"):
        text = text_for_feature(promoter)
        is_bacterial = any(token in text for token in BACTERIAL_PROMOTERS)
        is_auxiliary = any(token in text for token in AUXILIARY_PROMOTERS)
        is_mammalian = any(token in text for token in MAMMALIAN_PROMOTERS)
        is_yeast = any(token in text for token in YEAST_PROMOTERS)
        if is_auxiliary and host_class in {"mammalian", "yeast"}:
            issue = auxiliary_promoter_issue(promoter, sequence, spec, host_class)
            if issue is not None:
                return issue
            continue
        if host_class == "bacterial" and (is_mammalian or is_yeast) and not is_bacterial:
            return (
                "FAIL",
                promoter,
                f"Promoter '{promoter.name}' is not compatible with the requested {host_class} host context.",
            )
        if host_class == "mammalian" and (is_bacterial or is_yeast) and not is_mammalian:
            return (
                "FAIL",
                promoter,
                f"Promoter '{promoter.name}' is not compatible with the requested {host_class} host context.",
            )
        if host_class == "yeast" and (is_bacterial or is_mammalian) and not is_yeast:
            return (
                "FAIL",
                promoter,
                f"Promoter '{promoter.name}' is not compatible with the requested {host_class} host context.",
            )
    return None


def auxiliary_promoter_issue(
    promoter: AnnotatedFeature,
    sequence: AnnotatedSequence,
    spec: DesignSpec,
    host_class: str,
) -> tuple[str, AnnotatedFeature, str] | None:
    if auxiliary_promoter_requested_for_host_expression(spec, promoter):
        return (
            "FAIL",
            promoter,
            f"Auxiliary promoter '{promoter.name}' was requested for {host_class} host expression, but it is not host-compatible.",
        )
    if not source_record_context(spec):
        return (
            "FAIL",
            promoter,
            f"Auxiliary promoter '{promoter.name}' is not compatible with de novo {host_class} host-expression design intent.",
        )
    gois = features_of(sequence, "GOI")
    if not gois or not promoter_near_goi(promoter, gois, len(sequence.sequence)):
        return None
    return (
        "WARN",
        promoter,
        f"Auxiliary promoter '{promoter.name}' appears near a GOI in a source record; review whether it is helper/IVT/sequencing context or expression intent.",
    )


def auxiliary_promoter_requested_for_host_expression(spec: DesignSpec, promoter: AnnotatedFeature) -> bool:
    requested = " ".join([spec.promoter_type or "", spec.application or "", spec.vector_type or "", *spec.tags]).lower()
    promoter_text = text_for_feature(promoter)
    return any(token in requested for token in AUXILIARY_PROMOTERS) and any(token in promoter_text for token in AUXILIARY_PROMOTERS)


def source_record_context(spec: DesignSpec) -> bool:
    return spec.source is not None and str(spec.source) != "generated"


def promoter_near_goi(promoter: AnnotatedFeature, gois: list[AnnotatedFeature], sequence_length: int) -> bool:
    for goi in gois:
        distance = min(abs(promoter.end - goi.start), abs(goi.end - promoter.start))
        circular_distance = min(distance, sequence_length - distance)
        if circular_distance <= 500:
            return True
    return False


def downstream_terminator_issue(sequence: AnnotatedSequence) -> tuple[str, str, AnnotatedFeature] | None:
    gois = features_of(sequence, "GOI")
    if not gois:
        return None
    promoters = features_of(sequence, "promoter")
    if not promoters:
        return None
    terminators = features_of(sequence, "terminator")
    if not terminators:
        return "WARN", "GOI lacks an annotated downstream terminator; expression cassette may be incomplete.", gois[0]
    for goi in gois:
        downstream = [term for term in terminators if term.start >= goi.end or (sequence.topology == "circular" and term.start < goi.start)]
        if not downstream:
            return "WARN", f"GOI '{goi.name}' has no downstream terminator annotation.", goi
    return None
