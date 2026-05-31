from __future__ import annotations

import re
from collections.abc import Iterable

from packages.core.schemas import AnnotatedFeature


_WHITESPACE_RE = re.compile(r"\s+")
_BOUNDARY_TEMPLATE = r"(?<![a-z0-9])(?:{alias})(?![a-z0-9])"
_CLASS_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ampicillin", re.compile(_BOUNDARY_TEMPLATE.format(alias=r"bla|ampr|beta\-lactamase|ampicillin"), flags=re.IGNORECASE)),
    ("tetracycline", re.compile(_BOUNDARY_TEMPLATE.format(alias=r"tet|tetr|tetracycline"), flags=re.IGNORECASE)),
    ("chloramphenicol", re.compile(_BOUNDARY_TEMPLATE.format(alias=r"cat|chloramphenicol"), flags=re.IGNORECASE)),
    ("aminoglycoside", re.compile(_BOUNDARY_TEMPLATE.format(alias=r"kan|kanr|neomycin|neor|g418"), flags=re.IGNORECASE)),
    ("spectinomycin", re.compile(_BOUNDARY_TEMPLATE.format(alias=r"spectinomycin"), flags=re.IGNORECASE)),
    ("streptomycin", re.compile(_BOUNDARY_TEMPLATE.format(alias=r"streptomycin"), flags=re.IGNORECASE)),
)


def _normalize_unknown_token(name: str) -> str:
    normalized = _WHITESPACE_RE.sub(" ", name.strip().casefold())
    return f"unknown:{normalized}"


def normalize_marker_class(feature: AnnotatedFeature) -> str:
    for marker_class, pattern in _CLASS_PATTERNS:
        if pattern.search(feature.name):
            return marker_class
    return _normalize_unknown_token(feature.name)


def distinct_marker_classes(features: Iterable[AnnotatedFeature]) -> set[str]:
    return {
        normalize_marker_class(feature)
        for feature in features
        if feature.type == "marker"
    }
