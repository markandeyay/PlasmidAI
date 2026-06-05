from __future__ import annotations

import pytest

from packages.core.schemas import AnnotatedFeature, AnnotatedSequence
from packages.data_pipeline.parse.classify import classify, is_annotation_complete


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


@pytest.mark.parametrize(
    ("vector_name", "features", "expected_profile"),
    [
        (
            "pGEX-4T-1",
            [
                feature("ORI", "pMB1 origin", 0),
                feature("marker", "AmpR/bla", 1),
                feature("promoter", "tac promoter", 2),
                feature("GOI", "GST fusion partner", 3),
                feature("MCS", "multiple cloning site", 4),
            ],
            "bacterial_expression_vector",
        ),
        (
            "pUC19",
            [
                feature("ORI", "pMB1/pUC origin", 0),
                feature("marker", "bla", 1),
                feature("MCS", "pUC19 MCS", 2),
            ],
            "bacterial_cloning_vector",
        ),
        (
            "pUC18",
            [
                feature("ORI", "pMB1/pUC origin", 0),
                feature("marker", "bla", 1),
                feature("MCS", "pUC18 MCS", 2),
            ],
            "bacterial_cloning_vector",
        ),
        (
            "pBR322",
            [
                feature("ORI", "pBR322 origin", 0),
                feature("marker", "ampicillin resistance", 1),
                feature("marker", "tetracycline resistance", 2),
            ],
            "bacterial_cloning_vector",
        ),
        (
            "pBluescript-II-SK-plus",
            [
                feature("ORI", "pUC origin", 0),
                feature("marker", "AmpR/bla", 1),
                feature("MCS", "pBluescript polylinker", 2),
                feature("promoter", "T7 promoter", 3),
            ],
            "bacterial_cloning_vector",
        ),
        (
            "pBluescript-II-SK-minus",
            [
                feature("ORI", "pUC origin", 0),
                feature("marker", "AmpR/bla", 1),
                feature("MCS", "pBluescript polylinker", 2),
                feature("promoter", "T3 promoter", 3),
            ],
            "bacterial_cloning_vector",
        ),
        (
            "pACYC184",
            [
                feature("ORI", "p15A origin", 0),
                feature("marker", "chloramphenicol resistance", 1),
                feature("marker", "tetracycline resistance", 2),
            ],
            "bacterial_cloning_vector",
        ),
        (
            "pEGFP-N1",
            [
                feature("ORI", "pUC origin", 0),
                feature("marker", "kanamycin/neomycin resistance", 1),
                feature("promoter", "CMV promoter", 2),
                feature("GOI", "EGFP reporter", 3),
                feature("terminator", "SV40 polyA", 4),
            ],
            "mammalian_reporter_vector",
        ),
        (
            "pGL3-Basic",
            [
                feature("ORI", "pUC origin", 0),
                feature("marker", "AmpR/bla", 1),
                feature("GOI", "luc+", 2),
                feature("terminator", "SV40 late polyA", 3),
            ],
            "mammalian_reporter_vector",
        ),
        (
            "pGL4-10-luc2",
            [
                feature("ORI", "pUC origin", 0),
                feature("marker", "AmpR/bla", 1),
                feature("GOI", "luc2 luciferase reporter", 2),
                feature("terminator", "synthetic polyA", 3),
            ],
            "mammalian_reporter_vector",
        ),
        (
            "pRS415",
            [
                feature("ORI", "ARS/CEN yeast origin", 0),
                feature("marker", "LEU2 yeast selectable marker", 1),
                feature("MCS", "multiple cloning site", 2),
            ],
            "yeast_shuttle_vector",
        ),
        (
            "pRS416",
            [
                feature("ORI", "ARS/CEN yeast origin", 0),
                feature("marker", "URA3 yeast selectable marker", 1),
                feature("MCS", "multiple cloning site", 2),
            ],
            "yeast_shuttle_vector",
        ),
    ],
)
def test_curated_seed_vectors_classify_to_expected_profiles(
    vector_name: str,
    features: list[AnnotatedFeature],
    expected_profile: str,
) -> None:
    sequence = annotated(features)

    result = classify(sequence)

    assert result.profile == expected_profile, vector_name
    assert result.confidence > 0.65
    assert result.signals
    assert is_annotation_complete(sequence, result.profile) is True


def test_unknown_profile_is_not_complete() -> None:
    sequence = annotated([feature("GOI", "hypothetical protein", 0)])

    result = classify(sequence)

    assert result.profile == "unknown"
    assert is_annotation_complete(sequence, result.profile) is False


def test_curated_pacyc184_metadata_supports_single_marker_cloning_profile() -> None:
    sequence = annotated(
        [
            feature("ORI", "p15A origin", 0),
            feature("marker", "chloramphenicol resistance", 1),
        ]
    )

    result = classify(sequence, metadata_text="Cloning vector pACYC184 synthetic construct")

    assert result.profile == "bacterial_cloning_vector"
    assert "metadata-backed cloning backbone" in result.signals


def test_vector_title_with_marker_and_mcs_supports_existing_cloning_profile() -> None:
    sequence = annotated(
        [
            feature("marker", "chloramphenicol acetyltransferase", 0),
            feature("MCS", "pUC19 multiple cloning site", 1),
        ]
    )

    result = classify(sequence, metadata_text="Cloning vector pMAK705, complete sequence")

    assert result.profile == "bacterial_cloning_vector"
    assert "metadata-backed cloning vector" in result.signals


def test_expression_cloning_metadata_requires_full_bacterial_expression_cassette() -> None:
    sequence = annotated(
        [
            feature("ORI", "pMB1/pUC origin", 0),
            feature("marker", "bla", 1),
            feature("promoter", "lac promoter", 2),
            feature("GOI", "bioB", 3),
        ]
    )

    result = classify(sequence, metadata_text="Expression cloning vector pBVI02, complete sequence")

    assert result.profile == "bacterial_expression_vector"
    assert "metadata-backed expression cassette" in result.signals


def test_natural_resistance_plasmid_without_vector_metadata_stays_unknown() -> None:
    sequence = annotated(
        [
            feature("GOI", "RepB family replication initiator", 0),
            feature("marker", "blaZ", 1),
            feature("marker", "cadD", 2),
        ]
    )

    result = classify(sequence, metadata_text="Staphylococcus aureus strain LaCa plasmid complete sequence")

    assert result.profile == "unknown"


def test_pkil_expression_vector_metadata_supports_existing_expression_profile() -> None:
    sequence = annotated(
        [
            feature("ORI", "pMB1 origin", 0),
            feature("marker", "AmpR/bla", 1),
            feature("promoter", "lac promoter", 2),
            feature("GOI", "ccdB selection cassette", 3),
            feature("other", "lacIq repressor", 4),
        ]
    )

    result = classify(sequence, metadata_text="Expression vector pKIL-HIS3, complete sequence")

    assert result.profile == "bacterial_expression_vector"
    assert "metadata-backed expression cassette" in result.signals


def test_gfp_title_expression_vector_supports_reporter_profile_without_natural_guardrail() -> None:
    sequence = annotated(
        [
            feature("ORI", "pUC origin", 0),
            feature("marker", "AmpR/bla", 1),
            feature("GOI", "ryanodine receptor payload", 2),
        ]
    )

    result = classify(sequence, metadata_text="Expression vector unc-68:GFP(1-8), complete sequence")

    assert result.profile == "mammalian_reporter_vector"
    assert "metadata-backed GFP reporter vector" in result.signals


def test_t7_expression_vector_metadata_supports_pviet_like_profile() -> None:
    sequence = annotated(
        [
            feature("marker", "AmpR/bla", 0),
            feature("terminator", "T7 terminator", 1),
            feature("GOI", "His6 tag", 2),
            feature("other", "lacI repressor", 3),
        ]
    )

    result = classify(sequence, metadata_text="T7 expression vector pViet, complete sequence")

    assert result.profile == "bacterial_expression_vector"
    assert "metadata-backed T7 expression vector" in result.signals


def test_plz42_two_marker_lac_metadata_supports_cloning_profile() -> None:
    sequence = annotated(
        [
            feature("marker", "Bla beta-lactamase", 0),
            feature("marker", "Cat chloramphenicol acetyltransferase", 1),
            feature("promoter", "lac UV5 promoter", 2),
        ]
    )

    result = classify(sequence, metadata_text="Cloning vector pLZ42, complete sequence")

    assert result.profile == "bacterial_cloning_vector"
    assert "metadata-backed cloning vector" in result.signals


def test_p1_repl_metadata_supports_cloning_profile_without_global_repl_promotion() -> None:
    sequence = annotated(
        [
            feature("marker", "kanamycin resistance", 0),
            feature("GOI", "sacB counterselection", 1),
            feature("GOI", "kilA", 2),
            feature("GOI", "repL", 3),
        ]
    )

    result = classify(sequence, metadata_text="pSacBII P1 cloning vector with sacB, kilA, repL and kanamycin resistance genes")

    assert result.profile == "bacterial_cloning_vector"
    assert "metadata-backed P1 cloning vector" in result.signals


def test_natural_repl_resistance_plasmid_does_not_use_p1_cloning_fallback() -> None:
    sequence = annotated(
        [
            feature("marker", "kanamycin resistance", 0),
            feature("GOI", "repL replication protein", 1),
            feature("GOI", "mobilization protein", 2),
        ]
    )

    result = classify(sequence, metadata_text="Pseudoselenomonas ruminantium strain plasmid pSR1 complete sequence")

    assert result.profile == "unknown"


def test_vector_like_signals_in_natural_isolate_title_do_not_use_metadata_fallbacks() -> None:
    sequence = annotated(
        [
            feature("ORI", "pMB1/pUC origin-like region", 0),
            feature("marker", "aph aminoglycoside resistance", 1),
            feature("other", "T7 terminator", 2),
            feature("other", "f1 origin-like signal", 3),
        ]
    )

    result = classify(sequence, metadata_text="Staphylococcus haemolyticus strain 1b plasmid pSH_1b_2 complete sequence")

    assert result.profile == "unknown"
