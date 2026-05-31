from __future__ import annotations

from packages.core.schemas import AnnotatedFeature
from packages.data_pipeline.parse.marker_support import distinct_marker_classes


def feature(name: str, index: int) -> AnnotatedFeature:
    start = index * 100
    return AnnotatedFeature(type="marker", start=start, end=start + 50, strand=1, name=name, confidence=0.95)


def test_duplicate_bla_markers_count_once() -> None:
    features = [
        feature("AmpR/bla", 0),
        feature("beta-lactamase", 1),
    ]

    assert distinct_marker_classes(features) == {"ampicillin"}


def test_bla_and_tet_count_as_distinct_marker_classes() -> None:
    features = [
        feature("AmpR/bla", 0),
        feature("TetR", 1),
    ]

    assert distinct_marker_classes(features) == {"ampicillin", "tetracycline"}


def test_identical_unknown_marker_names_collapse() -> None:
    features = [
        feature("selection cassette X", 0),
        feature("selection cassette X", 1),
    ]

    assert distinct_marker_classes(features) == {"unknown:selection cassette x"}


def test_spectinomycin_and_streptomycin_remain_separate_classes() -> None:
    features = [
        feature("spectinomycin resistance", 0),
        feature("streptomycin resistance", 1),
    ]

    assert distinct_marker_classes(features) == {"spectinomycin", "streptomycin"}
