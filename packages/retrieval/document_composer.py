from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from packages.core.schemas import AnnotatedFeature, AnnotatedSequence, FeatureType, Plasmid


DOCUMENT_VERSION = "phase1-plasmid-document-v1"
PLACEHOLDER_VALUES = {"", "none", "null", "n/a"}
LOW_INFORMATION_USE_CASES = {
    "plasmid",
    "vector",
    "artificial sequence",
    "origin of replication",
}
USE_CASE_REWRITES = {
    "bacterial_cloning": "bacterial cloning",
    "bacterial_expression": "bacterial expression",
    "reporter_fluorescent": "fluorescent reporting",
    "yeast_shuttle": "yeast shuttle cloning",
}
PROFILE_SENTENCES = {
    "bacterial_cloning_vector": "Bacterial cloning vector {name}.",
    "bacterial_expression_vector": "Bacterial expression vector {name}.",
    "mammalian_expression_vector": "Mammalian expression vector {name}.",
    "mammalian_reporter_vector": "Mammalian reporter vector {name}.",
    "lentiviral_or_retroviral_transfer_vector": "Lentiviral or retroviral transfer vector {name}.",
    "crispr_vector": "CRISPR vector {name}.",
    "yeast_shuttle_vector": "Yeast shuttle vector {name}.",
    "general_shuttle_vector": "General shuttle vector {name}.",
}


@dataclass(frozen=True)
class ComposedDocument:
    text: str
    metadata: dict[str, Any]


def compose_plasmid_document(
    plasmid: Plasmid,
    annotated_sequence: AnnotatedSequence | None = None,
) -> ComposedDocument:
    features = list(annotated_sequence.features) if annotated_sequence else []
    vector_profile = annotated_sequence.vector_profile if annotated_sequence else "unknown"
    topology = str(annotated_sequence.topology) if annotated_sequence else "circular"
    annotation_complete = (
        annotated_sequence.annotation_complete if annotated_sequence is not None else plasmid.annotation_complete
    )

    emitted: list[dict[str, str]] = []
    clauses: list[str] = []

    profile_sentence = PROFILE_SENTENCES.get(vector_profile, "Unclassified plasmid {name}.").format(name=plasmid.name)
    clauses.append(profile_sentence)
    emitted.append({"field": "profile", "text": profile_sentence})

    source_description = _source_description(plasmid)
    if source_description is not None:
        text = f"Source description: {source_description}."
        clauses.append(text)
        emitted.append({"field": "source_description", "text": text})

    organism = _normalize_scalar(plasmid.organism)
    if organism is not None:
        text = f"Organism annotation: {organism}."
        clauses.append(text)
        emitted.append({"field": "organism", "text": text})

    promoters = _merge_labels(plasmid.promoters, _render_feature_labels(features, FeatureType.PROMOTER))
    if promoters:
        text = f"Promoters: {_join_list(promoters)}."
        clauses.append(text)
        emitted.append({"field": "promoters", "text": text})

    payloads = _render_feature_labels(features, FeatureType.GOI)
    if payloads:
        text = f"Payloads: {_join_list(payloads)}."
        clauses.append(text)
        emitted.append({"field": "payloads", "text": text})

    cloning_sites = _render_feature_labels(features, FeatureType.MCS)
    if cloning_sites:
        text = f"Cloning sites: {_join_list(cloning_sites)}."
        clauses.append(text)
        emitted.append({"field": "cloning_sites", "text": text})

    terminators = _render_feature_labels(features, FeatureType.TERMINATOR)
    if terminators:
        text = f"Terminators: {_join_list(terminators)}."
        clauses.append(text)
        emitted.append({"field": "terminators", "text": text})

    markers = _merge_labels(plasmid.markers, _render_feature_labels(features, FeatureType.MARKER))
    if markers:
        text = f"Selectable markers: {_join_list(markers)}."
        clauses.append(text)
        emitted.append({"field": "markers", "text": text})

    origins = _render_feature_labels(features, FeatureType.ORI)
    if origins:
        text = f"Replication origins: {_join_list(origins)}."
        clauses.append(text)
        emitted.append({"field": "origins", "text": text})

    use_cases = _select_use_cases(plasmid, source_description)
    if use_cases:
        text = f"Used for: {_join_list(use_cases)}."
        clauses.append(text)
        emitted.append({"field": "use_cases", "text": text})

    closing = f"{plasmid.length} bp {topology} plasmid. Source: {plasmid.source}."
    clauses.append(closing)
    emitted.append({"field": "physical", "text": closing})

    metadata = {
        "document_version": DOCUMENT_VERSION,
        "plasmid_id": plasmid.id,
        "raw_ref": plasmid.raw_ref,
        "source": str(plasmid.source),
        "vector_profile": vector_profile,
        "annotation_complete": annotation_complete,
        "emitted_clauses": emitted,
        "source_description": source_description,
        "candidates": {
            "promoters": _candidate_entries(plasmid.promoters, features, FeatureType.PROMOTER),
            "payloads": _feature_entries(features, FeatureType.GOI),
            "cloning_sites": _feature_entries(features, FeatureType.MCS),
            "terminators": _feature_entries(features, FeatureType.TERMINATOR),
            "markers": _candidate_entries(plasmid.markers, features, FeatureType.MARKER),
            "origins": _feature_entries(features, FeatureType.ORI),
            "use_cases": [_normalize_use_case(value) for value in plasmid.use_cases if _normalize_use_case(value) is not None],
        },
    }
    return ComposedDocument(text=" ".join(clauses), metadata=metadata)


def _normalize_scalar(value: str | None) -> str | None:
    if value is None:
        return None
    collapsed = re.sub(r"\s+", " ", value).strip()
    if collapsed.casefold() in PLACEHOLDER_VALUES:
        return None
    return collapsed


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _source_description(plasmid: Plasmid) -> str | None:
    candidates = [_normalize_scalar(value) for value in plasmid.use_cases]
    normalized_name = plasmid.name.casefold()
    for candidate in candidates:
        if candidate is None:
            continue
        folded = candidate.casefold()
        if folded == normalized_name:
            continue
        if folded in LOW_INFORMATION_USE_CASES:
            continue
        if folded in USE_CASE_REWRITES or "_" in candidate:
            continue
        return candidate
    return None


def _join_list(values: list[str]) -> str:
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return ", ".join(values[:-1]) + f", and {values[-1]}"


def _render_feature_labels(features: list[AnnotatedFeature], feature_type: FeatureType) -> list[str]:
    labels: list[str] = []
    for feature in sorted(
        [item for item in features if item.type == feature_type],
        key=lambda item: (_normalize_scalar(item.name) or "", item.start, item.end),
    ):
        label = _normalize_scalar(feature.name)
        if label is None:
            continue
        if feature.confidence < 0.50:
            continue
        if 0.50 <= feature.confidence < 0.80 and "candidate" not in label.casefold():
            label = f"{label} candidate"
        labels.append(label)
    return _dedupe(labels)


def _merge_labels(metadata_values: list[str], feature_values: list[str]) -> list[str]:
    values = [_normalize_scalar(value) for value in metadata_values]
    return _dedupe([value for value in values if value is not None] + feature_values)


def _normalize_use_case(value: str) -> str | None:
    normalized = _normalize_scalar(value)
    if normalized is None:
        return None
    folded = normalized.casefold()
    if "complete sequence" in folded:
        return None
    rewritten = USE_CASE_REWRITES.get(folded, normalized.replace("_", " "))
    if rewritten.casefold() in LOW_INFORMATION_USE_CASES:
        return None
    return rewritten


def _select_use_cases(plasmid: Plasmid, source_description: str | None) -> list[str]:
    selected: list[str] = []
    normalized_name = plasmid.name.casefold()
    source_casefold = source_description.casefold() if source_description else None
    for raw in plasmid.use_cases:
        candidate = _normalize_use_case(raw)
        if candidate is None:
            continue
        folded = candidate.casefold()
        if folded == normalized_name or folded == source_casefold:
            continue
        selected.append(candidate)
        if len(_dedupe(selected)) >= 5:
            break
    return _dedupe(selected)


def _feature_entries(features: list[AnnotatedFeature], feature_type: FeatureType) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for feature in features:
        if feature.type != feature_type:
            continue
        entries.append(
            {
                "label": feature.name,
                "type": str(feature.type),
                "start": feature.start,
                "end": feature.end,
                "strand": feature.strand,
                "confidence": feature.confidence,
            }
        )
    return entries


def _candidate_entries(
    metadata_values: list[str],
    features: list[AnnotatedFeature],
    feature_type: FeatureType,
) -> list[dict[str, Any]]:
    metadata_entries = [{"label": value, "origin": "metadata"} for value in metadata_values if _normalize_scalar(value) is not None]
    feature_entries = [
        {
            "label": feature.name,
            "origin": "feature",
            "type": str(feature.type),
            "start": feature.start,
            "end": feature.end,
            "strand": feature.strand,
            "confidence": feature.confidence,
        }
        for feature in features
        if feature.type == feature_type
    ]
    return metadata_entries + feature_entries
