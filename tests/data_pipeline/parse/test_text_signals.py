from __future__ import annotations

import pytest

from packages.data_pipeline.parse.text_signals import contains_signal, matching_signals


@pytest.mark.parametrize(
    ("signal", "hazard"),
    [
        ("cat", "replication"),
        ("ltr", "spectinomycin adenyltransferase"),
        ("ars", "arsenate resistance protein"),
        ("ars", "arsR/smtB family transcriptional regulator"),
        ("cen", "central metabolism regulator"),
        ("tre", "streptomycin resistance protein"),
        ("rre", "ferredoxin reductase"),
        ("psi", "epsilon subunit"),
    ],
)
def test_short_signals_do_not_match_inside_unrelated_words(signal: str, hazard: str) -> None:
    assert not contains_signal(hazard, signal)


@pytest.mark.parametrize(
    ("signal", "text"),
    [
        ("ltr", "5-prime LTR"),
        ("ars", "ARS/CEN yeast origin"),
        ("cen", "ARS/CEN yeast origin"),
        ("tre", "TRE promoter"),
        ("rre", "RRE export element"),
        ("psi", "Psi packaging signal"),
        ("long terminal repeat", "3-prime long terminal repeat"),
        ("packaging signal", "viral packaging signal"),
        ("2 micron", "2 micron yeast origin"),
    ],
)
def test_tokens_and_phrases_match_at_boundaries(signal: str, text: str) -> None:
    assert contains_signal(text, signal)


def test_phrase_matching_accepts_flexible_whitespace() -> None:
    assert contains_signal("viral packaging   signal", "packaging signal")


def test_nested_aliases_require_explicit_allowlist() -> None:
    assert not contains_signal("EGFP reporter", "gfp")
    assert contains_signal("EGFP reporter", "gfp", aliases=("egfp",))

    assert not contains_signal("ARSH4 yeast origin", "ars")
    assert contains_signal("ARSH4 yeast origin", "ars", aliases=("arsh4",))

    assert not contains_signal("pUC19 origin", "puc")
    assert contains_signal("pUC19 origin", "puc", aliases=("puc19",))


def test_matching_signals_returns_canonical_names_in_requested_order() -> None:
    signals = matching_signals(
        "ARSH4 yeast origin with EGFP reporter and 5-prime LTR",
        ("ltr", "ars", "gfp", "psi"),
        aliases={"ars": ("arsh4",), "gfp": ("egfp",)},
    )

    assert signals == ["ltr", "ars", "gfp"]


def test_empty_signal_is_rejected() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        contains_signal("some text", " ")
