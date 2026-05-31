from __future__ import annotations

import re


MARKER_TERMS = (
    "resistance",
    "resistant",
    "antibiotic",
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
    "hyg",
    "puromycin",
    "puro",
    "spectinomycin",
    "streptomycin",
    "tetracycline",
    "zeocin",
)
MARKER_TERM_PATTERNS = tuple(re.compile(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])") for term in MARKER_TERMS)
MARKER_GENE_FAMILY_PATTERN = re.compile(r"(?<![a-z0-9])(?:bla|tet)[a-z0-9-]*(?![a-z0-9])")


def contains_marker_term(text: str) -> bool:
    normalized = text.lower()
    return any(pattern.search(normalized) for pattern in MARKER_TERM_PATTERNS) or bool(
        MARKER_GENE_FAMILY_PATTERN.search(normalized)
    )
