from __future__ import annotations

from packages.core.schemas import AnnotatedFeature, AnnotatedSequence
from packages.data_pipeline.parse.expression_evidence import (
    bacterial_expression_evidence,
    mammalian_expression_evidence,
)


# Policy sources:
# - Addgene expression plasmid anatomy: https://www.addgene.org/mol-bio-reference/
# - Promega pGEM SP6/T7 cloning-vector context:
#   https://www.promega.com/-/media/files/resources/protocols/technical-manuals/0/pgem-t-and-pgem-t-easy-vector-systems-protocol.pdf
# - Agilent pBluescript T3/T7 sequencing/transcription context:
#   https://www.agilent.com/cs/library/usermanuals/public/212205.pdf
# - NEB T7 expression context:
#   https://www.neb.com/en-us/tools-and-resources/feature-articles/protein-expression-with-t7-express-strains


def annotated(*features: AnnotatedFeature) -> AnnotatedSequence:
    return AnnotatedSequence(
        sequence="A" * 12000,
        topology="circular",
        features=list(features),
        annotation_complete=False,
    )


def feature(feature_type: str, name: str, start: int, end: int, strand: int = 1) -> AnnotatedFeature:
    return AnnotatedFeature(
        type=feature_type,
        name=name,
        start=start,
        end=end,
        strand=strand,
        confidence=0.95,
    )


def test_pucp26_like_sp6_and_generic_cds_are_not_expression_evidence() -> None:
    evidence = bacterial_expression_evidence(
        annotated(
            feature("GOI", "rep", 410, 1244),
            feature("GOI", "lacZ alpha", 1240, 1495, -1),
            feature("MCS", "polylinker", 1424, 1481),
            feature("promoter", "SP6 promoter", 4947, 4965),
        )
    )

    assert evidence.qualifies is False
    assert "SP6 alone is sequencing or in-vitro-transcription evidence" in evidence.reasons
    assert "generic CDS/GOI annotation alone is not expression-purpose evidence" in evidence.reasons


def test_pget_tac_gst_cassette_is_bacterial_expression_evidence() -> None:
    evidence = bacterial_expression_evidence(
        annotated(
            feature("promoter", "tac promoter", 183, 211),
            feature("GOI", "GST fusion partner", 258, 977),
            feature("MCS", "multiple cloning site", 998, 1030),
        )
    )

    assert evidence.qualifies is True
    assert evidence.confidence >= 0.90
    assert evidence.signals[:2] == ("tac", "oriented GOI: GST fusion partner")
    assert "affinity tag" in evidence.signals


def test_trc_and_pbad_are_strong_bacterial_promoters_with_oriented_slots() -> None:
    for promoter_name, expected_signal in (("trc promoter", "trc"), ("araBAD pBAD promoter", "araBAD/pBAD")):
        evidence = bacterial_expression_evidence(
            annotated(
                feature("promoter", promoter_name, 100, 150),
                feature("MCS", "expression cloning slot", 180, 220),
            )
        )

        assert evidence.qualifies is True
        assert expected_signal in evidence.signals


def test_t7_requires_expression_cassette_corroboration() -> None:
    without_corroboration = bacterial_expression_evidence(
        annotated(
            feature("promoter", "T7 promoter", 100, 150),
            feature("GOI", "generic CDS", 180, 500),
        )
    )
    with_corroboration = bacterial_expression_evidence(
        annotated(
            feature("promoter", "T7 promoter with lac operator", 100, 150),
            feature("other", "Shine-Dalgarno RBS", 160, 175),
            feature("GOI", "6xHis tagged recombinant CDS", 180, 500),
        )
    )

    assert without_corroboration.qualifies is False
    assert "T7 lacks explicit expression-cassette corroboration" in without_corroboration.reasons
    assert with_corroboration.qualifies is True
    assert {"T7", "lacO/operator", "RBS", "affinity tag"} <= set(with_corroboration.signals)


def test_t3_and_generic_cds_are_not_bacterial_expression_evidence() -> None:
    evidence = bacterial_expression_evidence(
        annotated(
            feature("promoter", "T3 promoter", 100, 150),
            feature("GOI", "generic CDS", 180, 500),
        )
    )

    assert evidence.qualifies is False
    assert "T3 alone is sequencing or in-vitro-transcription evidence" in evidence.reasons


def test_wrong_orientation_does_not_form_bacterial_expression_cassette() -> None:
    evidence = bacterial_expression_evidence(
        annotated(
            feature("promoter", "tac promoter", 100, 150),
            feature("GOI", "GST fusion partner", 180, 500, -1),
        )
    )

    assert evidence.qualifies is False


def test_mammalian_promoter_requires_oriented_payload_or_cloning_slot() -> None:
    without_slot = mammalian_expression_evidence(
        annotated(feature("promoter", "CMV promoter", 100, 150))
    )
    with_slot = mammalian_expression_evidence(
        annotated(
            feature("promoter", "CMV promoter", 100, 150),
            feature("MCS", "expression cloning slot", 180, 220),
        )
    )

    assert without_slot.qualifies is False
    assert with_slot.qualifies is True
    assert with_slot.signals[:2] == ("CMV", "oriented MCS: expression cloning slot")


def test_mammalian_terminator_or_polya_strengthens_evidence() -> None:
    without_polya = mammalian_expression_evidence(
        annotated(
            feature("promoter", "EF1a promoter", 100, 150),
            feature("GOI", "recombinant CDS", 180, 500),
        )
    )
    with_polya = mammalian_expression_evidence(
        annotated(
            feature("promoter", "EF1a promoter", 100, 150),
            feature("GOI", "recombinant CDS", 180, 500),
            feature("terminator", "BGH polyA", 520, 600),
        )
    )

    assert without_polya.qualifies is True
    assert with_polya.qualifies is True
    assert with_polya.confidence > without_polya.confidence
    assert "terminator/polyA" in with_polya.signals


def test_mammalian_promoter_aliases_are_token_bounded() -> None:
    false_tre = mammalian_expression_evidence(
        annotated(
            feature("promoter", "upstream control region", 100, 150),
            feature("GOI", "recombinant CDS", 180, 500),
        )
    )
    true_tre = mammalian_expression_evidence(
        annotated(
            feature("promoter", "TRE promoter", 100, 150),
            feature("GOI", "recombinant CDS", 180, 500),
        )
    )

    assert false_tre.qualifies is False
    assert true_tre.qualifies is True
