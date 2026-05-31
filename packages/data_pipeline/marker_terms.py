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
MARKER_GENE_ALIASES = (
    "blai",
    "blar1",
    "blaz",
    "teta",
    "tetb",
    "tetc",
    "tetd",
    "tete",
    "tetg",
    "teth",
    "tetk",
    "tetl",
    "tetm",
    "teto",
    "tetq",
    "tetr",
    "tets",
    "tetw",
    "tetx",
)
MARKER_GENE_PATTERNS = tuple(
    re.compile(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])")
    for alias in MARKER_GENE_ALIASES
)


def contains_marker_term(text: str) -> bool:
    normalized = text.lower()
    return any(pattern.search(normalized) for pattern in (*MARKER_TERM_PATTERNS, *MARKER_GENE_PATTERNS))
