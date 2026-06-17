from __future__ import annotations

import re
from dataclasses import dataclass

from Bio.Restriction import AllEnzymes, RestrictionBatch
from Bio.Seq import Seq

from packages.core.schemas import AnnotatedFeature, AnnotatedSequence, DesignSpec, ValidationCheck
from packages.validation.common import fail_check, features_of, overlaps_any, pass_check, region


CHECK_NAME = "restriction_site_conflicts"
ENZYMES_BY_NAME = {enzyme.__name__.lower(): enzyme for enzyme in AllEnzymes}
ENZYME_NAME_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])(" + "|".join(re.escape(enzyme.__name__) for enzyme in AllEnzymes) + r")(?![A-Za-z0-9])",
    flags=re.IGNORECASE,
)
AVOID_CONSTRAINT_PATTERN = re.compile(
    r"\b(avoid|no|without|free\s+of|remove|removed|domesticat(?:e|ed|ion)?|internal)\b", flags=re.IGNORECASE
)
PASSIVE_METHOD_PATTERN = re.compile(
    r"\b(gibson|hifi|hi-fi|lic|gateway|topo|ta cloning|synthesis|synthetic|gene synthesis)\b", flags=re.IGNORECASE
)


@dataclass(frozen=True)
class RestrictionSite:
    enzyme: str
    start: int
    end: int


@dataclass(frozen=True)
class RestrictionContext:
    enzymes: set[str]
    avoid_enzymes: set[str]
    recognition_families: dict[str, set[str]]


def run_restriction_site_check(sequence: AnnotatedSequence, spec: DesignSpec) -> ValidationCheck:
    context = restriction_context_from_spec(spec)
    enzymes = context.enzymes
    if not enzymes:
        return pass_check(CHECK_NAME, "No restriction-enzyme cloning context was specified.")

    sites = find_restriction_sites(sequence.sequence, enzymes, circular=sequence.topology == "circular")
    if not sites:
        return pass_check(CHECK_NAME, f"No requested cloning sites found for {', '.join(sorted(enzymes))}.")

    cloning_regions = features_of(sequence, "MCS")
    conflicts = [site for site in sites if not overlaps_any(site.start, site.end, cloning_regions, padding=6)]
    if conflicts:
        first = conflicts[0]
        label = label_for_site(first.enzyme, context)
        context_label = feature_context(sequence, first)
        return fail_check(
            CHECK_NAME,
            f"{label} has an internal site in {context_label} outside the annotated MCS; redesign cloning strategy or remove the site.",
            region(first.start, first.end, len(sequence.sequence)),
        )
    return pass_check(
        CHECK_NAME,
        f"All requested cloning enzyme sites are confined to the annotated MCS for {', '.join(sorted(enzymes))}.",
    )


def enzymes_from_spec(spec: DesignSpec) -> set[str]:
    return restriction_context_from_spec(spec).enzymes


def restriction_context_from_spec(spec: DesignSpec) -> RestrictionContext:
    method = spec.cloning_method or ""
    segments = [method, *spec.constraints]
    method_text = method.lower()
    passive_method = bool(PASSIVE_METHOD_PATTERN.search(method_text))
    enzyme_segments = [(enzyme, segment) for segment in segments for enzyme in enzyme_names_in_text(segment)]
    avoid_enzymes = {enzyme for enzyme, segment in enzyme_segments if AVOID_CONSTRAINT_PATTERN.search(segment)}

    if passive_method:
        selected = set(avoid_enzymes)
    else:
        selected = {enzyme for enzyme, _segment in enzyme_segments}

    recognition_families = {enzyme: recognition_family_for(enzyme) for enzyme in avoid_enzymes}
    enzymes = set(selected)
    for enzyme in selected & avoid_enzymes:
        enzymes.update(recognition_families[enzyme])
    return RestrictionContext(enzymes=enzymes, avoid_enzymes=avoid_enzymes, recognition_families=recognition_families)


def enzyme_names_in_text(text: str) -> set[str]:
    found: set[str] = set()
    for match in ENZYME_NAME_PATTERN.finditer(text or ""):
        enzyme = ENZYMES_BY_NAME.get(match.group(1).lower())
        if enzyme is not None:
            found.add(enzyme.__name__)
    return found


def recognition_family_for(enzyme_name: str) -> set[str]:
    enzyme = ENZYMES_BY_NAME.get(enzyme_name.lower())
    if enzyme is None:
        return {enzyme_name}
    family = {enzyme.__name__}
    family.update(member.__name__ for member in enzyme.isoschizomers())
    return family


def label_for_site(site_enzyme: str, context: RestrictionContext) -> str:
    for requested in sorted(context.avoid_enzymes):
        family = context.recognition_families.get(requested, {requested})
        if site_enzyme in family:
            if len(family) > 1:
                family_label = "/".join([requested, *sorted(family - {requested})])
                return f"{family_label} recognition-site family"
            return requested
    return site_enzyme


def feature_context(sequence: AnnotatedSequence, site: RestrictionSite) -> str:
    overlapping = [feature for feature in sequence.features if site.start < feature.end and site.end > feature.start]
    if not overlapping:
        return "backbone/unannotated sequence"
    goi = first_feature_of(overlapping, "GOI", "CDS", "coding_sequence")
    if goi is not None:
        return feature_label(goi, default="GOI")
    mcs = first_feature_of(overlapping, "MCS")
    if mcs is not None:
        return feature_label(mcs, default="MCS")
    return feature_label(overlapping[0], default="annotated feature")


def first_feature_of(features: list[AnnotatedFeature], *types: str) -> AnnotatedFeature | None:
    wanted = {feature_type.lower() for feature_type in types}
    for feature in features:
        if str(feature.type).lower() in wanted:
            return feature
    return None


def feature_label(feature: AnnotatedFeature, *, default: str) -> str:
    feature_type = str(feature.type) if feature.type else default
    if feature.name and feature.name.lower() != feature_type.lower():
        return f"{feature_type} ({feature.name})"
    return feature_type


def find_restriction_sites(sequence: str, enzymes: set[str], *, circular: bool = True) -> list[RestrictionSite]:
    enzyme_objects = [enzyme for enzyme in AllEnzymes if enzyme.__name__ in enzymes]
    if not enzyme_objects:
        return []
    batch = RestrictionBatch(enzyme_objects)
    search_sequence = Seq(sequence)
    analysis = batch.search(search_sequence, linear=not circular)
    sites: list[RestrictionSite] = []
    for enzyme, positions in analysis.items():
        site_len = len(str(enzyme.site))
        for position in positions:
            start = max(0, int(position) - 1)
            sites.append(RestrictionSite(enzyme=enzyme.__name__, start=start, end=min(start + site_len, len(sequence))))
    return sorted(sites, key=lambda item: (item.start, item.enzyme))
