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


def test_extended_marker_aliases_map_to_distinct_classes() -> None:
    features = [
        feature("gentamycin acetyltransferase-3-1 aacC1", 0),
        feature("kanamycin resistance", 1),
        feature("aminoglycoside phosphotransferase", 2),
        feature("HygR hygromycin marker", 3),
        feature("PuroR puromycin marker", 4),
        feature("Bsd blasticidin marker", 5),
        feature("Sh ble Zeocin marker", 6),
        feature("Nat nourseothricin marker", 7),
    ]

    assert distinct_marker_classes(features) == {
        "aminoglycoside",
        "hygromycin",
        "puromycin",
        "blasticidin",
        "zeocin",
        "nourseothricin",
    }
