from __future__ import annotations

from Bio.Seq import Seq
from Bio.SeqFeature import FeatureLocation, SeqFeature
from Bio.SeqRecord import SeqRecord

from packages.core.schemas import AnnotatedFeature, AnnotatedSequence
from packages.data_pipeline.parse.classify import classify, is_annotation_complete
from packages.data_pipeline.parse.origin_support import general_shuttle_evidence
from packages.data_pipeline.parse.sequence_parser import parse_seqrecord


def annotated(features: list[AnnotatedFeature]) -> AnnotatedSequence:
    return AnnotatedSequence(
        sequence="A" * 12000,
        topology="circular",
        features=features,
        annotation_complete=False,
    )


def feature(feature_type: str, name: str, index: int) -> AnnotatedFeature:
    start = index * 100
    return AnnotatedFeature(type=feature_type, start=start, end=start + 50, strand=1, name=name, confidence=0.95)


def test_por262_like_two_bacterial_origins_do_not_trigger_general_shuttle() -> None:
    sequence = annotated(
        [
            feature("promoter", "lpp-lac fusion promoter.", 0),
            feature("GOI", "NADPH-cytochrome P450 reductase", 1),
            feature("ORI", "pBR322 origin of replication (ROP protein).", 2),
            feature("ORI", "pMB1/pUC origin", 3),
            feature("marker", "beta-lactamase", 4),
        ]
    )

    result = classify(sequence)

    assert result.profile == "bacterial_expression_vector"
    assert is_annotation_complete(sequence, "general_shuttle_vector") is False


def test_puc_plus_f1_is_not_sequence_supported_shuttle() -> None:
    sequence = annotated(
        [
            feature("ORI", "pMB1/pUC origin", 0),
            feature("ORI", "f1 origin", 1),
            feature("marker", "AmpR/bla", 2),
            feature("MCS", "multiple cloning site", 3),
        ]
    )

    result = classify(sequence)

    assert result.profile == "bacterial_cloning_vector"


def test_puc_plus_arsh4_has_cross_host_sequence_support() -> None:
    sequence = annotated(
        [
            feature("ORI", "pMB1/pUC origin", 0),
            feature("ORI", "ARSH4", 1),
            feature("marker", "URA3 yeast selectable marker", 2),
            feature("MCS", "multiple cloning site", 3),
        ]
    )

    evidence = general_shuttle_evidence(sequence)

    assert evidence.qualifies is True
    assert evidence.signals == (
        "origin support: pMB1/pUC origin [autonomous/bacterial]",
        "origin support: ARSH4 [autonomous/yeast]",
        "autonomous origin host classes: bacterial, yeast",
    )
    assert is_annotation_complete(sequence, "general_shuttle_vector") is True


def test_metadata_phrase_admits_interbacterial_shuttle_via_parse_seqrecord() -> None:
    record = SeqRecord(Seq("A" * 2000), id="pUCP26-like", description="Escherichia-Pseudomonas shuttle vector")
    record.annotations["topology"] = "circular"
    record.features = [
        SeqFeature(FeatureLocation(10, 110), type="rep_origin", qualifiers={"note": ["pMB1/pUC origin"]}),
        SeqFeature(FeatureLocation(150, 260), type="rep_origin", qualifiers={"note": ["pRO1600 replication origin"]}),
        SeqFeature(FeatureLocation(300, 900), type="CDS", qualifiers={"product": ["beta-lactamase"]}),
        SeqFeature(FeatureLocation(950, 1020), type="misc_feature", qualifiers={"note": ["multiple cloning site"]}),
    ]

    annotated_record = parse_seqrecord(record)
    result = classify(
        annotated_record,
        metadata_text="Escherichia-Pseudomonas shuttle vector",
    )

    assert annotated_record.vector_profile == "general_shuttle_vector"
    assert result.signals == (
        "origin support: pMB1/pUC origin [autonomous/bacterial]",
        "origin support: pRO1600 origin [autonomous/bacterial]",
        "trusted metadata phrase: shuttle vector",
        "selectable marker",
    )


def test_orit_is_ignored_for_general_shuttle_support() -> None:
    sequence = annotated(
        [
            feature("ORI", "pMB1/pUC origin", 0),
            feature("ORI", "oriT", 1),
            feature("marker", "AmpR/bla", 2),
            feature("MCS", "multiple cloning site", 3),
        ]
    )

    evidence = general_shuttle_evidence(sequence)
    result = classify(sequence)

    assert evidence.qualifies is False
    assert result.profile == "bacterial_cloning_vector"
