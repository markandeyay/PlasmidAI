from __future__ import annotations

import re
from dataclasses import dataclass

from Bio.Restriction import AllEnzymes, RestrictionBatch
from Bio.Seq import Seq

from packages.core.schemas import AnnotatedSequence, DesignSpec, ValidationCheck
from packages.validation.common import fail_check, features_of, overlaps_any, pass_check, region, warn_check


CHECK_NAME = "restriction_site_conflicts"
COMMON_CLONING_ENZYMES = {
    "BamHI",
    "EcoRI",
    "HindIII",
    "KpnI",
    "NcoI",
    "NdeI",
    "NotI",
    "PstI",
    "SacI",
    "SalI",
    "SmaI",
    "SpeI",
    "XbaI",
    "XhoI",
}


@dataclass(frozen=True)
class RestrictionSite:
    enzyme: str
    start: int
    end: int


def run_restriction_site_check(sequence: AnnotatedSequence, spec: DesignSpec) -> ValidationCheck:
    enzymes = enzymes_from_spec(spec)
    if not enzymes:
        return pass_check(CHECK_NAME, "No restriction-enzyme cloning context was specified.")

    sites = find_restriction_sites(sequence.sequence, enzymes, circular=sequence.topology == "circular")
    if not sites:
        return pass_check(CHECK_NAME, f"No requested cloning sites found for {', '.join(sorted(enzymes))}.")

    cloning_regions = features_of(sequence, "MCS")
    conflicts = [site for site in sites if not overlaps_any(site.start, site.end, cloning_regions, padding=6)]
    if conflicts:
        first = conflicts[0]
        return fail_check(
            CHECK_NAME,
            f"{first.enzyme} has an internal cut site outside the annotated MCS; redesign cloning strategy or remove the site.",
            region(first.start, first.end, len(sequence.sequence)),
        )
    return pass_check(
        CHECK_NAME,
        f"All requested cloning enzyme sites are confined to the annotated MCS for {', '.join(sorted(enzymes))}.",
    )


def enzymes_from_spec(spec: DesignSpec) -> set[str]:
    haystack = " ".join([spec.cloning_method or "", *spec.constraints])
    found: set[str] = set()
    for enzyme in COMMON_CLONING_ENZYMES:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(enzyme)}(?![A-Za-z0-9])", haystack, flags=re.IGNORECASE):
            found.add(enzyme)
    return found


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
