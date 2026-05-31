from __future__ import annotations

import pytest

from packages.core.schemas import AnnotatedFeature, AnnotatedSequence
from packages.data_pipeline.parse.classify import classify


def feature(feature_type: str, name: str, index: int) -> AnnotatedFeature:
    start = index * 100
    return AnnotatedFeature(
        type=feature_type,
        start=start,
        end=start + 50,
        strand=1,
        name=name,
        confidence=0.95,
    )


def annotated(*items: tuple[str, str]) -> AnnotatedSequence:
    return AnnotatedSequence(
        sequence="A" * 12000,
        topology="circular",
        features=[feature(feature_type, name, index) for index, (feature_type, name) in enumerate(items)],
        annotation_complete=False,
    )


@pytest.mark.xfail(reason="Current classifier still overcalls dual bacterial origins as general shuttle.")
def test_por262_like_pbr322_plus_pmb1_stays_bacterial_cloning() -> None:
    result = classify(
        annotated(
            ("ORI", "pBR322 origin"),
            ("ORI", "pMB1 origin"),
            ("marker", "AmpR/bla"),
            ("MCS", "multiple cloning site"),
        )
    )

    assert result.profile == "bacterial_cloning_vector"
    assert result.profile != "general_shuttle_vector"


def test_pbluescript_like_stays_bacterial_cloning() -> None:
    result = classify(
        annotated(
            ("ORI", "pUC origin"),
            ("marker", "AmpR/bla"),
            ("MCS", "pBluescript polylinker"),
            ("promoter", "T7 sequencing promoter"),
            ("promoter", "T3 sequencing promoter"),
        )
    )

    assert result.profile == "bacterial_cloning_vector"


def test_prs416_like_stays_yeast_shuttle() -> None:
    result = classify(
        annotated(
            ("ORI", "pUC origin"),
            ("ORI", "ARSH4"),
            ("marker", "URA3"),
            ("MCS", "multiple cloning site"),
        )
    )

    assert result.profile == "yeast_shuttle_vector"


def test_pyes2_like_stays_yeast_shuttle() -> None:
    result = classify(
        annotated(
            ("ORI", "pUC origin"),
            ("ORI", "2-micron"),
            ("marker", "URA3"),
            ("MCS", "multiple cloning site"),
        )
    )

    assert result.profile == "yeast_shuttle_vector"


@pytest.mark.xfail(
    reason="Host-aware archaeal-origin handling is not wired into the public classifier yet.",
)
def test_colE1_plus_pHK2_with_marker_and_mcs_becomes_general_shuttle() -> None:
    result = classify(
        annotated(
            ("ORI", "ColE1 origin"),
            ("ORI", "pHK2 archaeal origin"),
            ("marker", "selectable marker"),
            ("MCS", "multiple cloning site"),
        )
    )

    assert result.profile == "general_shuttle_vector"


def test_metadata_text_lane_promotes_puCP26_like_general_shuttle() -> None:
    sequence = annotated(
        ("ORI", "pMB1 origin"),
        ("ORI", "pRO1600 origin"),
        ("marker", "selectable marker"),
    )

    try:
        result = classify(sequence, metadata_text="Cloning shuttle vector pUCP26")  # type: ignore[arg-type]
    except TypeError:
        pytest.xfail("metadata_text is not accepted by classify yet.")

    assert result.profile == "general_shuttle_vector"
