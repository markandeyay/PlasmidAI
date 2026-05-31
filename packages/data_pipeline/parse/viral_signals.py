from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


# Lentiviral transfer vectors retain LTRs and packaging-related cis elements.
# Sources:
# - https://www.addgene.org/guides/lentivirus/
# - https://www.ncbi.nlm.nih.gov/pmc/articles/PMC515268/
# Retroviral transfer vectors likewise retain LTRs and packaging signals while
# packaging genes are supplied separately:
# - https://www.addgene.org/guides/retrovirus/


@dataclass(frozen=True)
class ViralSignalEvaluation:
    """Auditable result for conservative viral transfer-vector detection."""

    is_transfer_vector: bool
    matched_signals: tuple[str, ...]
    corroborating_rule: str | None


def evaluate_viral_signals(feature_text: str | Iterable[str]) -> ViralSignalEvaluation:
    """Evaluate viral-vector hallmarks using token boundaries and corroboration.

    A generic LTR annotation is not sufficient by itself. Admission requires
    both terminal LTR annotations, or an LTR plus a packaging signal, or an LTR
    plus a known viral-backbone element.
    """

    text = _normalize_text(feature_text)
    matched: list[str] = []

    has_five_prime_ltr = _matches_any(text, _FIVE_PRIME_LTR_PATTERNS)
    has_three_prime_ltr = _matches_any(text, _THREE_PRIME_LTR_PATTERNS)
    has_generic_ltr = _matches_any(text, _GENERIC_LTR_PATTERNS)
    has_ltr = has_five_prime_ltr or has_three_prime_ltr or has_generic_ltr

    if has_five_prime_ltr:
        matched.append("5-prime LTR")
    if has_three_prime_ltr:
        matched.append("3-prime LTR")
    if has_generic_ltr and not (has_five_prime_ltr or has_three_prime_ltr):
        matched.append("LTR")

    packaging_signals = _matched_aliases(text, _PACKAGING_SIGNAL_PATTERNS)
    backbone_signals = _matched_aliases(text, _BACKBONE_SIGNAL_PATTERNS)
    matched.extend(packaging_signals)
    matched.extend(backbone_signals)

    if has_five_prime_ltr and has_three_prime_ltr:
        rule = "both 5-prime and 3-prime LTRs"
    elif has_ltr and packaging_signals:
        rule = "LTR plus packaging signal"
    elif has_ltr and backbone_signals:
        rule = "LTR plus known viral-backbone element"
    else:
        rule = None

    return ViralSignalEvaluation(
        is_transfer_vector=rule is not None,
        matched_signals=tuple(matched),
        corroborating_rule=rule,
    )


def _normalize_text(feature_text: str | Iterable[str]) -> str:
    if isinstance(feature_text, str):
        return feature_text.lower()
    return " ".join(feature_text).lower()


def _matches_any(text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _matched_aliases(text: str, patterns: dict[str, tuple[re.Pattern[str], ...]]) -> list[str]:
    return [alias for alias, alias_patterns in patterns.items() if _matches_any(text, alias_patterns)]


def _compile(*patterns: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(pattern, flags=re.IGNORECASE) for pattern in patterns)


# Use alphanumeric boundaries rather than ``\b`` so hyphenated feature names
# remain matchable while strings such as "adenyltransferase" cannot emit "ltr".
_LTR = r"(?:ltr|long[\s-]+terminal[\s-]+repeat)"
_FIVE_PRIME = r"(?:5\s*-?\s*(?:['\u2032]|prime)?|five[\s-]+prime)"
_THREE_PRIME = r"(?:3\s*-?\s*(?:['\u2032]|prime)?|three[\s-]+prime)"

_FIVE_PRIME_LTR_PATTERNS = _compile(
    rf"(?<![a-z0-9]){_FIVE_PRIME}[\s-]*{_LTR}(?![a-z0-9])",
    rf"(?<![a-z0-9]){_LTR}[\s-]*{_FIVE_PRIME}(?![a-z0-9])",
)
_THREE_PRIME_LTR_PATTERNS = _compile(
    rf"(?<![a-z0-9]){_THREE_PRIME}[\s-]*{_LTR}(?![a-z0-9])",
    rf"(?<![a-z0-9]){_LTR}[\s-]*{_THREE_PRIME}(?![a-z0-9])",
)
_GENERIC_LTR_PATTERNS = _compile(rf"(?<![a-z0-9]){_LTR}(?![a-z0-9])")

_PACKAGING_SIGNAL_PATTERNS = {
    "psi packaging signal": _compile(
        r"(?<![a-z0-9])psi(?:[\s-]+packaging)?(?:[\s-]+signal)?(?![a-z0-9])",
        r"(?<![a-z0-9])packaging[\s-]+signal(?![a-z0-9])",
        r"(?<![a-z0-9])\u03c8(?![a-z0-9])",
    ),
}

_BACKBONE_SIGNAL_PATTERNS = {
    "gag": _compile(r"(?<![a-z0-9])gag(?:[\s-]+fragment)?(?![a-z0-9])"),
    "pol": _compile(r"(?<![a-z0-9])pol(?:[\s-]+fragment)?(?![a-z0-9])"),
    "env": _compile(r"(?<![a-z0-9])env(?:[\s-]+fragment)?(?![a-z0-9])"),
    "RRE": _compile(
        r"(?<![a-z0-9])rre(?![a-z0-9])",
        r"(?<![a-z0-9])rev[\s-]+response[\s-]+element(?![a-z0-9])",
    ),
    "WPRE": _compile(
        r"(?<![a-z0-9])wpre(?![a-z0-9])",
        r"(?<![a-z0-9])woodchuck[\s-]+hepatitis[\s-]+virus[\s-]+posttranscriptional[\s-]+regulatory[\s-]+element(?![a-z0-9])",
    ),
    "cPPT": _compile(
        r"(?<![a-z0-9])c[\s-]*ppt(?![a-z0-9])",
        r"(?<![a-z0-9])central[\s-]+polypurine[\s-]+tract(?![a-z0-9])",
    ),
    "MSCV": _compile(r"(?<![a-z0-9])mscv(?![a-z0-9])"),
}
