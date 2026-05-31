from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Sequence

from packages.core.schemas import AnnotatedFeature, AnnotatedSequence


# Expression-vector policy is intentionally conservative. Addgene distinguishes
# cloning backbones from expression plasmids by the latter's promoter, inserted
# gene, and terminator. Promega and Agilent document SP6/T7/T3 promoters on
# cloning vectors for RNA synthesis and sequencing, while NEB and Merck document
# the extra context needed for T7 bacterial expression.
# Sources:
# https://www.addgene.org/mol-bio-reference/
# https://www.promega.com/-/media/files/resources/protocols/technical-manuals/0/pgem-t-and-pgem-t-easy-vector-systems-protocol.pdf
# https://www.agilent.com/cs/library/usermanuals/public/212205.pdf
# https://www.neb.com/en-us/tools-and-resources/feature-articles/protein-expression-with-t7-express-strains
# https://www.merckmillipore.com/INTERSHOP/web/WFS/Merck-US-Site/en_US/-/USD/ShowDocument-File?ProductSKU=EMD_BIO-71827&DocumentId=TB055
# https://www.ncbi.nlm.nih.gov/nuccore/U40578.1


@dataclass(frozen=True)
class ExpressionEvidence:
    qualifies: bool
    confidence: float
    signals: tuple[str, ...]
    reasons: tuple[str, ...]


def bacterial_expression_evidence(
    annotated_sequence: AnnotatedSequence | Sequence[AnnotatedFeature],
) -> ExpressionEvidence:
    """Return auditable evidence for an in-vivo bacterial expression cassette."""
    features = _features(annotated_sequence)
    promoter_matches = _matching_features(
        features,
        {
            "tac": ("tac",),
            "trc": ("trc",),
            "araBAD/pBAD": ("arabad", "pbad"),
            "lpp-lac": ("lpp-lac",),
            "T7": ("t7",),
            "SP6": ("sp6",),
            "T3": ("t3",),
        },
        feature_type="promoter",
    )
    corroboration = _matched_aliases(
        features,
        {
            "lacO/operator": ("laco", "lac operator", "operator"),
            "RBS": ("rbs", "shine-dalgarno"),
            "affinity tag": ("his-tag", "his tag", "6xhis", "gst", "mbp", "flag", "ha tag"),
            "terminator": ("terminator",),
        },
    )
    weak_promoters = tuple(label for label in ("SP6", "T3") if label in promoter_matches)
    for label in ("tac", "trc", "araBAD/pBAD", "lpp-lac"):
        oriented_slot = _first_oriented_slot(features, promoter_matches.get(label, ()))
        if oriented_slot is not None:
            signals = _ordered_unique((label, _slot_signal(oriented_slot), *corroboration))
            return ExpressionEvidence(
                qualifies=True,
                confidence=0.92 if corroboration else 0.86,
                signals=signals,
                reasons=(f"{label} is a strong bacterial promoter with an oriented payload or cloning slot",),
            )

    t7_slot = _first_oriented_slot(features, promoter_matches.get("T7", ()))
    if t7_slot is not None and corroboration:
        return ExpressionEvidence(
            qualifies=True,
            confidence=0.90,
            signals=_ordered_unique(("T7", _slot_signal(t7_slot), *corroboration)),
            reasons=("T7 has an oriented payload or cloning slot and explicit expression-cassette corroboration",),
        )

    reasons: list[str] = []
    if weak_promoters:
        reasons.append(f"{'/'.join(weak_promoters)} alone is sequencing or in-vitro-transcription evidence")
    if "T7" in promoter_matches:
        reasons.append("T7 lacks explicit expression-cassette corroboration")
    if any(feature.type == "GOI" for feature in features):
        reasons.append("generic CDS/GOI annotation alone is not expression-purpose evidence")
    if not reasons:
        reasons.append("no qualifying bacterial expression cassette")
    return ExpressionEvidence(
        qualifies=False,
        confidence=0.0,
        signals=_ordered_unique((*promoter_matches, *corroboration)),
        reasons=tuple(reasons),
    )


def mammalian_expression_evidence(
    annotated_sequence: AnnotatedSequence | Sequence[AnnotatedFeature],
) -> ExpressionEvidence:
    """Return auditable evidence for a mammalian expression cassette."""
    features = _features(annotated_sequence)
    promoter_matches = _matching_features(
        features,
        {
            "CMV": ("cmv",),
            "EF1a": ("ef1a", "ef-1a", "ef1-alpha", "ef-1-alpha"),
            "CAG": ("cag",),
            "PGK": ("pgk",),
            "SV40": ("sv40",),
            "TRE": ("tre",),
        },
        feature_type="promoter",
    )
    terminator_signals = _matched_aliases(
        features,
        {"terminator/polyA": ("terminator", "polya", "polyadenylation", "poly(a)")},
    )
    for label, promoters in promoter_matches.items():
        oriented_slot = _first_oriented_slot(features, promoters)
        if oriented_slot is None:
            continue
        signals = _ordered_unique((label, _slot_signal(oriented_slot), *terminator_signals))
        reason = f"{label} has an oriented payload or cloning slot"
        if terminator_signals:
            reason += " and terminator/polyA support"
        return ExpressionEvidence(
            qualifies=True,
            confidence=0.92 if terminator_signals else 0.82,
            signals=signals,
            reasons=(reason,),
        )

    reasons: list[str] = []
    if promoter_matches:
        reasons.append("mammalian promoter lacks an oriented payload or cloning slot")
    if any(feature.type == "GOI" for feature in features):
        reasons.append("generic CDS/GOI annotation alone is not expression-purpose evidence")
    if not reasons:
        reasons.append("no qualifying mammalian expression cassette")
    return ExpressionEvidence(
        qualifies=False,
        confidence=0.0,
        signals=_ordered_unique((*promoter_matches, *terminator_signals)),
        reasons=tuple(reasons),
    )


def _features(
    annotated_sequence: AnnotatedSequence | Sequence[AnnotatedFeature],
) -> list[AnnotatedFeature]:
    if isinstance(annotated_sequence, AnnotatedSequence):
        return annotated_sequence.features
    return list(annotated_sequence)


def _matching_features(
    features: Iterable[AnnotatedFeature],
    aliases_by_label: dict[str, tuple[str, ...]],
    *,
    feature_type: str,
) -> dict[str, tuple[AnnotatedFeature, ...]]:
    matches: dict[str, tuple[AnnotatedFeature, ...]] = {}
    for label, aliases in aliases_by_label.items():
        matching = tuple(
            feature
            for feature in features
            if feature.type == feature_type and _contains_alias(feature.name, aliases)
        )
        if matching:
            matches[label] = matching
    return matches


def _matched_aliases(
    features: Iterable[AnnotatedFeature],
    aliases_by_label: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    text = " ".join(feature.name for feature in features)
    return tuple(
        label
        for label, aliases in aliases_by_label.items()
        if _contains_alias(text, aliases)
    )


def _contains_alias(text: str, aliases: Iterable[str]) -> bool:
    return any(
        re.search(rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])", text, re.IGNORECASE)
        for alias in aliases
    )


def _first_oriented_slot(
    features: Iterable[AnnotatedFeature],
    promoters: Iterable[AnnotatedFeature],
) -> AnnotatedFeature | None:
    slots = [feature for feature in features if feature.type in {"GOI", "MCS"}]
    for promoter in promoters:
        for slot in slots:
            if promoter.strand == 1 and slot.strand in {0, 1} and slot.start >= promoter.end:
                return slot
            if promoter.strand == -1 and slot.strand in {-1, 0} and slot.end <= promoter.start:
                return slot
    return None


def _slot_signal(slot: AnnotatedFeature) -> str:
    return f"oriented {slot.type}: {slot.name}"


def _ordered_unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))
