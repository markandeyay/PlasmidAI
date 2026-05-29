from __future__ import annotations

import json
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any, Iterable

from Bio import SeqIO, pairwise2
from Bio.SeqFeature import SeqFeature
from Bio.SeqRecord import SeqRecord

from packages.core.schemas import AnnotatedFeature, AnnotatedSequence


REFERENCE_PATH = Path(__file__).resolve().parent / "references" / "component_library.json"
CORE_TYPES = {"ORI", "promoter", "marker", "terminator"}
MARKER_TERMS = {
    "resistance",
    "resistant",
    "ampicillin",
    "ampr",
    "bla",
    "beta-lactamase",
    "kanamycin",
    "kanr",
    "neomycin",
    "neo",
    "chloramphenicol",
    "cat",
    "hygromycin",
    "puromycin",
    "puro",
    "spectinomycin",
    "streptomycin",
    "tetracycline",
    "zeocin",
}
RESTRICTION_SITES = {
    "GAATTC",
    "AAGCTT",
    "GGATCC",
    "CTGCAG",
    "GTCGAC",
    "TCTAGA",
    "CCCGGG",
    "GGTACC",
    "GAGCTC",
    "GCATGC",
    "CCGCGG",
}


@dataclass(frozen=True)
class ReferenceComponent:
    name: str
    type: str
    sequence: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParserConfig:
    reference_identity_threshold: float = 0.85
    reference_coverage_threshold: float = 0.70
    trusted_annotation_confidence: float = 0.95
    reference_match_confidence: float = 0.82
    motif_confidence: float = 0.55


def parse_genbank_text(raw_text: str, config: ParserConfig | None = None) -> AnnotatedSequence:
    record = SeqIO.read(StringIO(raw_text), "genbank")
    return parse_seqrecord(record, config=config)


def parse_seqrecord(record: SeqRecord, config: ParserConfig | None = None) -> AnnotatedSequence:
    config = config or ParserConfig()
    sequence = str(record.seq).upper()
    topology = "circular" if record.annotations.get("topology") == "circular" else "linear"
    features: list[AnnotatedFeature] = []

    features.extend(features_from_annotations(record, config))
    references = load_reference_components()
    features.extend(features_from_reference_matches(sequence, features, references, config))
    features.extend(features_from_motifs(sequence, features, config))

    features = sorted(dedupe_features(features), key=lambda item: (item.start, item.end, item.type, item.name))
    observed_types = {feature.type for feature in features}
    return AnnotatedSequence(
        sequence=sequence,
        topology=topology,
        features=features,
        annotation_complete=CORE_TYPES.issubset(observed_types),
    )


def features_from_annotations(record: SeqRecord, config: ParserConfig) -> list[AnnotatedFeature]:
    features: list[AnnotatedFeature] = []
    for source_feature in record.features:
        component_type = normalize_feature_type(source_feature)
        if component_type is None:
            continue
        start, end = feature_bounds(source_feature)
        if end <= start:
            continue
        features.append(
            AnnotatedFeature(
                type=component_type,
                start=start,
                end=end,
                strand=source_feature.location.strand or 0,
                name=best_feature_name(source_feature, fallback=component_type),
                confidence=config.trusted_annotation_confidence,
            )
        )
    return features


def normalize_feature_type(feature: SeqFeature) -> str | None:
    text = qualifier_text(feature).lower()
    feature_type = feature.type.lower()
    if feature_type == "rep_origin" or "origin of replication" in text or "pmb1" in text or "cole1" in text:
        return "ORI"
    if feature_type == "promoter":
        return "promoter"
    if feature_type == "regulatory" and "promoter" in text:
        return "promoter"
    if feature_type in {"terminator", "polyA_signal", "polyA_site"}:
        return "terminator"
    if feature_type in {"regulatory", "misc_feature"} and ("terminator" in text or "polya" in text or "polyadenylation" in text):
        return "terminator"
    if feature_type == "misc_feature" and ("multiple cloning" in text or "polylinker" in text or "mcs" in text):
        return "MCS"
    if feature_type in {"cds", "gene", "misc_feature"} and any(term in text for term in MARKER_TERMS):
        return "marker"
    if feature_type == "cds":
        return "GOI"
    return None


def features_from_reference_matches(
    sequence: str,
    existing: list[AnnotatedFeature],
    references: list[ReferenceComponent],
    config: ParserConfig,
) -> list[AnnotatedFeature]:
    matches: list[AnnotatedFeature] = []
    for reference in references:
        if any(feature.type == reference.type and names_match(feature.name, reference.name, reference.aliases) for feature in existing):
            continue
        match = find_reference_match(sequence, reference, config)
        if match is None:
            continue
        start, end, strand, identity, coverage = match
        if overlaps_existing(start, end, existing + matches, reference.type):
            continue
        confidence = min(0.90, config.reference_match_confidence + 0.05 * max(identity - config.reference_identity_threshold, 0))
        matches.append(
            AnnotatedFeature(
                type=reference.type,
                start=start,
                end=end,
                strand=strand,
                name=reference.name,
                confidence=confidence,
            )
        )
    return matches


def find_reference_match(
    sequence: str,
    reference: ReferenceComponent,
    config: ParserConfig,
) -> tuple[int, int, int, float, float] | None:
    ref = reference.sequence.upper()
    direct = sequence.find(ref)
    if direct >= 0:
        return direct, direct + len(ref), 1, 1.0, 1.0
    alignments = pairwise2.align.localms(sequence, ref, 2, -1, -5, -1, one_alignment_only=True)
    if not alignments:
        return None
    alignment = alignments[0]
    aligned_seq, aligned_ref, score, start, end = alignment[:5]
    ref_aligned_bases = sum(1 for base in aligned_ref if base != "-")
    if ref_aligned_bases == 0:
        return None
    identities = sum(
        1
        for seq_base, ref_base in zip(aligned_seq, aligned_ref)
        if seq_base == ref_base and seq_base != "-" and ref_base != "-"
    )
    identity = identities / ref_aligned_bases
    coverage = ref_aligned_bases / len(ref)
    if identity < config.reference_identity_threshold or coverage < config.reference_coverage_threshold:
        return None
    return int(start), int(end), 1, identity, coverage


def features_from_motifs(
    sequence: str,
    existing: list[AnnotatedFeature],
    config: ParserConfig,
    *,
    window_size: int = 90,
    min_sites: int = 5,
) -> list[AnnotatedFeature]:
    best: tuple[int, int, set[str]] | None = None
    for start in range(0, max(1, len(sequence) - window_size + 1), 10):
        window = sequence[start : start + window_size]
        sites = {site for site in RESTRICTION_SITES if site in window}
        if len(sites) >= min_sites and (best is None or len(sites) > len(best[2])):
            first = min(window.index(site) for site in sites)
            last = max(window.index(site) + len(site) for site in sites)
            best = (start + first, start + last, sites)
    if best is None:
        return []
    start, end, sites = best
    if overlaps_existing(start, end, existing, "MCS"):
        return []
    return [
        AnnotatedFeature(
            type="MCS",
            start=start,
            end=end,
            strand=0,
            name=f"restriction-site dense MCS candidate ({len(sites)} sites)",
            confidence=config.motif_confidence,
        )
    ]


def load_reference_components(path: Path = REFERENCE_PATH) -> list[ReferenceComponent]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    components = []
    for item in payload["components"]:
        components.append(
            ReferenceComponent(
                name=item["name"],
                type=item["type"],
                sequence="".join(item["sequence"].upper().split()),
                aliases=tuple(item.get("aliases", [])),
            )
        )
    return components


def dedupe_features(features: Iterable[AnnotatedFeature]) -> list[AnnotatedFeature]:
    result: list[AnnotatedFeature] = []
    for feature in sorted(features, key=lambda item: item.confidence, reverse=True):
        if overlaps_existing(feature.start, feature.end, result, str(feature.type)):
            continue
        result.append(feature)
    return result


def overlaps_existing(start: int, end: int, features: list[AnnotatedFeature], feature_type: str) -> bool:
    for feature in features:
        if str(feature.type) != feature_type:
            continue
        overlap = max(0, min(end, feature.end) - max(start, feature.start))
        shorter = max(1, min(end - start, feature.end - feature.start))
        if overlap / shorter >= 0.50:
            return True
    return False


def names_match(name: str, reference_name: str, aliases: tuple[str, ...]) -> bool:
    normalized = name.strip().lower()
    return normalized == reference_name.lower() or normalized in {alias.lower() for alias in aliases}


def feature_bounds(feature: SeqFeature) -> tuple[int, int]:
    parts = getattr(feature.location, "parts", None)
    if parts:
        starts = [int(part.start) for part in parts]
        ends = [int(part.end) for part in parts]
        return min(starts), max(ends)
    return int(feature.location.start), int(feature.location.end)


def best_feature_name(feature: SeqFeature, *, fallback: str) -> str:
    for key in ("label", "gene", "product", "note", "regulatory_class"):
        values = feature.qualifiers.get(key)
        if values and values[0]:
            return str(values[0])
    return fallback


def qualifier_text(feature: SeqFeature) -> str:
    values: list[str] = [feature.type]
    for key, raw_values in feature.qualifiers.items():
        values.append(str(key))
        values.extend(str(value) for value in raw_values)
    return " ".join(values)
