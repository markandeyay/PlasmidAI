from __future__ import annotations

from pathlib import Path

from Bio.SeqFeature import FeatureLocation, SeqFeature

from packages.data_pipeline.parse.sequence_parser import normalize_feature_type, parse_genbank_text, parse_seqrecord


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "parser"


def feature_by_type(annotated, feature_type: str):  # type: ignore[no-untyped-def]
    return [feature for feature in annotated.features if str(feature.type) == feature_type]


def test_puc19_trusted_annotations_detect_expected_components() -> None:
    annotated = parse_genbank_text((FIXTURES / "puc19.gb").read_text(encoding="utf-8"))

    promoter = feature_by_type(annotated, "promoter")[0]
    mcs = feature_by_type(annotated, "MCS")[0]
    ori = feature_by_type(annotated, "ORI")[0]
    marker = feature_by_type(annotated, "marker")[0]

    assert (promoter.start, promoter.end, promoter.name) == (237, 395, "lac promoter")
    assert (mcs.start, mcs.end, mcs.name) == (395, 452, "pUC19 MCS")
    assert (ori.start, ori.end, ori.name) == (866, 1455, "pMB1/pUC origin")
    assert (marker.start, marker.end, marker.name) == (1628, 2417, "bla")
    assert all(feature.confidence == 0.95 for feature in [promoter, mcs, ori, marker])
    assert annotated.vector_profile == "bacterial_cloning_vector"
    assert annotated.annotation_complete is True


def test_reference_matching_finds_unannotated_puc19_components() -> None:
    record_text = (FIXTURES / "puc19.gb").read_text(encoding="utf-8")
    from Bio import SeqIO

    record = SeqIO.read(FIXTURES / "puc19.gb", "genbank")
    record.features = [record.features[0]]
    annotated = parse_seqrecord(record)

    assert any(feature.name == "pUC19 MCS" and feature.start == 395 for feature in annotated.features)
    assert any(feature.name == "AmpR/bla" and feature.start == 1628 for feature in annotated.features)
    assert any(feature.name == "pMB1/pUC origin" and feature.start == 866 for feature in annotated.features)


def test_motif_heuristic_flags_restriction_site_dense_mcs_candidate() -> None:
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord

    sequence = "A" * 120 + "GAATTCAAGCTTGGATCCCTGCAGGTCGACTCTAGACCCGGG" + "A" * 120
    record = SeqRecord(Seq(sequence), id="motif", description="motif-only")
    record.annotations["topology"] = "circular"

    annotated = parse_seqrecord(record)

    mcs_features = feature_by_type(annotated, "MCS")
    assert len(mcs_features) == 1
    assert 100 <= mcs_features[0].start <= 130
    assert mcs_features[0].confidence == 0.55


def test_annotation_normalization_does_not_match_short_aliases_inside_words() -> None:
    origin_like = SeqFeature(
        FeatureLocation(0, 10),
        type="misc_feature",
        qualifiers={"note": ["xpmb1x maintenance protein"]},
    )
    mcs_like = SeqFeature(
        FeatureLocation(0, 10),
        type="misc_feature",
        qualifiers={"note": ["xmcsx binding protein"]},
    )

    assert normalize_feature_type(origin_like) is None
    assert normalize_feature_type(mcs_like) is None
