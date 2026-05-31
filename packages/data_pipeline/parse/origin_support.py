from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Sequence

from packages.core.schemas import AnnotatedFeature, AnnotatedSequence
from packages.data_pipeline.parse.text_signals import contains_signal


REFERENCE_PATH = Path(__file__).resolve().parent / "references" / "component_library.json"


@dataclass(frozen=True)
class OriginReference:
    name: str
    aliases: tuple[str, ...]
    replication_family: str | None = None
    replication_role: str | None = None
    host_class: str | None = None


@dataclass(frozen=True)
class OriginMatch:
    feature_name: str
    reference_name: str
    replication_family: str | None
    replication_role: str | None
    host_class: str | None


@dataclass(frozen=True)
class OriginSupportEvidence:
    qualifies: bool
    signals: tuple[str, ...]
    host_classes: tuple[str, ...]
    metadata_phrase_matched: bool


DEFAULT_ORIGIN_METADATA: dict[str, dict[str, str | None]] = {
    "pMB1/pUC origin": {
        "replication_family": "pmb1_puc",
        "replication_role": "autonomous",
        "host_class": "bacterial",
    },
    "p15A origin": {
        "replication_family": "p15a",
        "replication_role": "autonomous",
        "host_class": "bacterial",
    },
    "f1 origin": {
        "replication_family": "f1",
        "replication_role": "ssdna_rescue",
        "host_class": None,
    },
    "ARSH4": {
        "replication_family": "ars",
        "replication_role": "autonomous",
        "host_class": "yeast",
    },
}

FALLBACK_ORIGIN_REFERENCES: tuple[OriginReference, ...] = (
    OriginReference(
        name="pBR322 origin",
        aliases=("pbr322 origin", "pbr322 origin of replication", "pbr322"),
        replication_family="pbr322",
        replication_role="autonomous",
        host_class="bacterial",
    ),
    OriginReference(
        name="ColE1 origin",
        aliases=("cole1 origin", "cole1"),
        replication_family="cole1",
        replication_role="autonomous",
        host_class="bacterial",
    ),
    OriginReference(
        name="pRO1600 origin",
        aliases=("pro1600 origin", "pro1600 replication origin", "pro1600"),
        replication_family="pro1600",
        replication_role="autonomous",
        host_class="bacterial",
    ),
    OriginReference(
        name="2-micron origin",
        aliases=("2-micron origin", "2 micron origin", "2-micron", "2 micron"),
        replication_family="2_micron",
        replication_role="autonomous",
        host_class="yeast",
    ),
    OriginReference(
        name="SV40 origin",
        aliases=("sv40 origin", "sv40 minimum origin", "sv40 ori"),
        replication_family="sv40",
        replication_role="autonomous",
        host_class="mammalian",
    ),
    OriginReference(
        name="second-host replication origin",
        aliases=("second-host replication origin", "second host replication origin"),
        replication_family="second_host_placeholder",
        replication_role="autonomous",
        host_class="secondary_host",
    ),
)


def general_shuttle_evidence(
    annotated_sequence: AnnotatedSequence | Sequence[AnnotatedFeature],
    *,
    metadata_text: str | None = None,
) -> OriginSupportEvidence:
    features = _features(annotated_sequence)
    origin_matches = tuple(
        match
        for feature in features
        if str(feature.type) == "ORI"
        for match in [_match_origin_feature(feature.name)]
        if match is not None
    )
    autonomous_host_classes = tuple(
        sorted(
            {
                match.host_class
                for match in origin_matches
                if _normalized_role(match.replication_role) == "autonomous" and match.host_class is not None
            }
        )
    )
    metadata_phrase_matched = contains_signal(metadata_text or "", "shuttle vector")

    signals = tuple(
        f"origin support: {match.reference_name} [{_normalized_role(match.replication_role) or 'unknown'}/{match.host_class or 'unknown'}]"
        for match in origin_matches
    )
    if len(autonomous_host_classes) >= 2:
        signals += (f"autonomous origin host classes: {', '.join(autonomous_host_classes)}",)
    if metadata_phrase_matched:
        signals += ("trusted metadata phrase: shuttle vector",)

    return OriginSupportEvidence(
        qualifies=len(autonomous_host_classes) >= 2 or metadata_phrase_matched,
        signals=signals,
        host_classes=autonomous_host_classes,
        metadata_phrase_matched=metadata_phrase_matched,
    )


def _match_origin_feature(name: str) -> OriginMatch | None:
    if contains_signal(name, "oriT", aliases=("origin of transfer",)):
        return None

    best_match: OriginReference | None = None
    best_score = -1
    for reference in _origin_references():
        candidates = (reference.name, *reference.aliases)
        matched = [candidate for candidate in candidates if contains_signal(name, candidate)]
        if not matched:
            continue
        score = max(len(candidate) for candidate in matched)
        if score > best_score:
            best_match = reference
            best_score = score

    if best_match is None:
        return None
    return OriginMatch(
        feature_name=name,
        reference_name=best_match.name,
        replication_family=best_match.replication_family,
        replication_role=_normalized_role(best_match.replication_role),
        host_class=best_match.host_class,
    )


@lru_cache(maxsize=1)
def _origin_references() -> tuple[OriginReference, ...]:
    payload = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    references = [
        OriginReference(
            name=item["name"],
            aliases=tuple(item.get("aliases", [])),
            replication_family=_metadata_field(item, "replication_family"),
            replication_role=_metadata_field(item, "replication_role"),
            host_class=_metadata_field(item, "host_class"),
        )
        for item in payload["components"]
        if item.get("type") == "ORI"
    ]
    references.extend(FALLBACK_ORIGIN_REFERENCES)
    return tuple(references)


def _metadata_field(item: dict[str, object], field: str) -> str | None:
    value = item.get(field)
    if value is not None:
        return str(value)
    defaults = DEFAULT_ORIGIN_METADATA.get(str(item["name"]), {})
    default_value = defaults.get(field)
    return str(default_value) if default_value is not None else None


def _features(
    annotated_sequence: AnnotatedSequence | Sequence[AnnotatedFeature],
) -> list[AnnotatedFeature]:
    if isinstance(annotated_sequence, AnnotatedSequence):
        return annotated_sequence.features
    return list(annotated_sequence)


def _normalized_role(replication_role: str | None) -> str | None:
    if replication_role is None:
        return None
    normalized = replication_role.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in {"autonomous", "autonomous_replication"}:
        return "autonomous"
    if normalized in {"ssdna_rescue", "single_strand_rescue"}:
        return "ssdna_rescue"
    if normalized in {"transfer", "origin_of_transfer"}:
        return "transfer"
    return normalized
