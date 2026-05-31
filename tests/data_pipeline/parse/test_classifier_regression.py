from __future__ import annotations

from dataclasses import dataclass

import pytest

from packages.core.schemas import AnnotatedFeature, AnnotatedSequence
from packages.data_pipeline.parse.classify import classify


@dataclass(frozen=True)
class RegressionCase:
    name: str
    expected_profile: str
    features: tuple[tuple[str, str], ...]
    trace_any: tuple[str, ...]
    source_key: str


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


def annotated(case: RegressionCase) -> AnnotatedSequence:
    return AnnotatedSequence(
        sequence="A" * 12000,
        topology="circular",
        features=[
            feature(feature_type, name, index)
            for index, (feature_type, name) in enumerate(case.features)
        ],
        annotation_complete=False,
    )


def trace_contains_any(signals: tuple[str, ...], expected: tuple[str, ...]) -> bool:
    trace = " ".join(signals).lower()
    return any(item.lower() in trace for item in expected)


PUBLISHED_CASES = (
    RegressionCase(
        "pUC19",
        "bacterial_cloning_vector",
        (("ORI", "pUC/pMB1 origin"), ("marker", "AmpR/bla"), ("MCS", "pUC19 multiple cloning site")),
        ("puc", "multiple cloning"),
        "pUC19",
    ),
    RegressionCase(
        "pBR322",
        "bacterial_cloning_vector",
        (("ORI", "pBR322 origin"), ("marker", "AmpR/bla"), ("marker", "TetR")),
        ("pbr322",),
        "pBR322",
    ),
    RegressionCase(
        "pBluescript-II-SK-plus",
        "bacterial_cloning_vector",
        (
            ("ORI", "pUC origin"),
            ("marker", "AmpR/bla"),
            ("MCS", "pBluescript polylinker"),
            ("promoter", "T7 sequencing promoter"),
            ("promoter", "T3 sequencing promoter"),
        ),
        ("puc", "pbluescript", "polylinker"),
        "pBluescript",
    ),
    RegressionCase(
        "pGEX-4T-1",
        "bacterial_expression_vector",
        (
            ("ORI", "pMB1 origin"),
            ("marker", "AmpR/bla"),
            ("promoter", "tac promoter"),
            ("GOI", "GST fusion partner"),
            ("MCS", "multiple cloning site"),
        ),
        ("tac", "gst"),
        "pGEX",
    ),
    RegressionCase(
        "pBAD-expression",
        "bacterial_expression_vector",
        (
            ("ORI", "pBR322 origin"),
            ("marker", "AmpR/bla"),
            ("promoter", "araBAD promoter"),
            ("GOI", "oriented recombinant CDS"),
            ("other", "Shine-Dalgarno RBS"),
        ),
        ("arabad", "rbs", "shine-dalgarno"),
        "pBAD",
    ),
    RegressionCase(
        "pET-T7lac-expression",
        "bacterial_expression_vector",
        (
            ("ORI", "pBR322 origin"),
            ("marker", "KanR"),
            ("promoter", "T7 promoter with lac operator"),
            ("GOI", "6xHis tagged recombinant CDS"),
            ("other", "RBS"),
        ),
        ("t7", "rbs"),
        "pET",
    ),
    RegressionCase(
        "pcDNA3.1",
        "mammalian_expression_vector",
        (
            ("ORI", "pUC origin"),
            ("marker", "AmpR/bla"),
            ("promoter", "CMV immediate early promoter"),
            ("GOI", "oriented mammalian CDS"),
            ("terminator", "BGH polyadenylation signal"),
        ),
        ("cmv", "bgh", "polyadenylation"),
        "pcDNA3.1",
    ),
    RegressionCase(
        "pCAGGS",
        "mammalian_expression_vector",
        (
            ("ORI", "pUC origin"),
            ("marker", "AmpR/bla"),
            ("promoter", "CAG promoter"),
            ("GOI", "oriented mammalian CDS"),
            ("terminator", "rabbit beta-globin polyadenylation signal"),
        ),
        ("cag", "polyadenylation"),
        "pCAGGS",
    ),
    RegressionCase(
        "pEGFP-N1",
        "mammalian_reporter_vector",
        (
            ("ORI", "pUC origin"),
            ("marker", "NeoR/KanR"),
            ("promoter", "CMV promoter"),
            ("GOI", "EGFP reporter"),
            ("terminator", "SV40 polyA"),
        ),
        ("egfp", "gfp"),
        "pEGFP-N1",
    ),
    RegressionCase(
        "pGL3-Basic-promoterless",
        "mammalian_reporter_vector",
        (
            ("ORI", "pUC origin"),
            ("marker", "AmpR/bla"),
            ("MCS", "promoter cloning site"),
            ("GOI", "luc+ luciferase reporter"),
            ("terminator", "SV40 late polyA"),
        ),
        ("luc+", "luciferase"),
        "pGL3",
    ),
    RegressionCase(
        "pGL4.20-promoterless",
        "mammalian_reporter_vector",
        (
            ("ORI", "pUC origin"),
            ("marker", "AmpR/bla"),
            ("MCS", "promoter cloning site"),
            ("GOI", "luc2 luciferase reporter"),
            ("terminator", "synthetic polyA"),
        ),
        ("luc2", "luciferase"),
        "pGL4",
    ),
    RegressionCase(
        "pLKO.1-TRC",
        "lentiviral_or_retroviral_transfer_vector",
        (
            ("ORI", "pUC origin"),
            ("marker", "AmpR/bla"),
            ("other", "5-prime LTR"),
            ("other", "psi packaging signal"),
            ("other", "3-prime SIN LTR"),
            ("MCS", "AgeI EcoRI shRNA cloning site"),
        ),
        ("ltr", "psi", "packaging signal"),
        "pLKO.1",
    ),
    RegressionCase(
        "lentiviral-transfer-LTR-WPRE",
        "lentiviral_or_retroviral_transfer_vector",
        (
            ("ORI", "pUC origin"),
            ("marker", "AmpR/bla"),
            ("other", "5-prime LTR"),
            ("other", "3-prime LTR"),
            ("other", "WPRE"),
            ("MCS", "payload cloning site"),
        ),
        ("ltr", "wpre"),
        "lentiviral",
    ),
    RegressionCase(
        "pMSCV-retroviral-transfer",
        "lentiviral_or_retroviral_transfer_vector",
        (
            ("ORI", "pUC origin"),
            ("marker", "AmpR/bla"),
            ("other", "MSCV 5-prime LTR"),
            ("other", "psi packaging signal"),
            ("other", "MSCV 3-prime LTR"),
            ("MCS", "payload cloning site"),
        ),
        ("mscv", "ltr", "psi"),
        "retroviral",
    ),
    RegressionCase(
        "pX330",
        "crispr_vector",
        (
            ("ORI", "pUC origin"),
            ("marker", "AmpR/bla"),
            ("promoter", "U6 promoter"),
            ("other", "sgRNA scaffold"),
            ("GOI", "human codon-optimized SpCas9"),
        ),
        ("sgrna", "cas9"),
        "pX330",
    ),
    RegressionCase(
        "lentiCRISPR-v2",
        "crispr_vector",
        (
            ("ORI", "pUC origin"),
            ("marker", "AmpR/bla"),
            ("other", "5-prime LTR"),
            ("other", "psi packaging signal"),
            ("other", "3-prime LTR"),
            ("other", "sgRNA scaffold"),
            ("GOI", "SpCas9"),
        ),
        ("sgrna", "cas9"),
        "lentiCRISPR",
    ),
    RegressionCase(
        "pX458-CRISPR-reporter",
        "crispr_vector",
        (
            ("ORI", "pUC origin"),
            ("marker", "AmpR/bla"),
            ("other", "sgRNA scaffold"),
            ("GOI", "SpCas9"),
            ("GOI", "EGFP reporter"),
        ),
        ("sgrna", "cas9"),
        "pX458",
    ),
    RegressionCase(
        "pRS416",
        "yeast_shuttle_vector",
        (("ORI", "pUC origin"), ("ORI", "ARSH4"), ("marker", "URA3"), ("MCS", "multiple cloning site")),
        ("ura3", "ars"),
        "pRS416",
    ),
    RegressionCase(
        "pYES2",
        "yeast_shuttle_vector",
        (
            ("ORI", "pUC origin"),
            ("ORI", "2-micron origin"),
            ("marker", "URA3"),
            ("promoter", "GAL1 promoter"),
            ("MCS", "multiple cloning site"),
        ),
        ("ura3", "2-micron"),
        "pYES2",
    ),
    RegressionCase(
        "broad-host-range-cloning-shuttle",
        "general_shuttle_vector",
        (
            ("ORI", "ColE1 E. coli origin"),
            ("ORI", "second-host replication origin"),
            ("marker", "AmpR/bla"),
            ("MCS", "multiple cloning site"),
        ),
        ("multiple origins", "selectable marker"),
        "synthetic_general_shuttle",
    ),
)


SYNTHETIC_EDGE_CASES = (
    RegressionCase(
        "pUCP26-like-SP6-cloning-shuttle",
        "bacterial_cloning_vector",
        (
            ("ORI", "pRO1600 replication origin"),
            ("marker", "TetR"),
            ("promoter", "SP6 sequencing promoter"),
            ("GOI", "generic CDS annotation"),
            ("MCS", "multiple cloning site"),
        ),
        ("multiple cloning", "ORI+marker cloning backbone"),
        "synthetic_pUCP26_like",
    ),
    RegressionCase(
        "T7-T3-sequencing-cloning-backbone",
        "bacterial_cloning_vector",
        (
            ("ORI", "pUC origin"),
            ("marker", "AmpR/bla"),
            ("promoter", "T7 sequencing promoter"),
            ("promoter", "T3 sequencing promoter"),
            ("GOI", "generic CDS annotation"),
            ("MCS", "multiple cloning site"),
        ),
        ("puc", "multiple cloning"),
        "synthetic_sequencing_promoters",
    ),
    RegressionCase(
        "pDL278-like-adenyltransferase",
        "bacterial_cloning_vector",
        (
            ("ORI", "bacterial replication origin"),
            ("marker", "spectinomycin adenyltransferase"),
            ("MCS", "multiple cloning site"),
        ),
        ("multiple cloning", "ORI+marker cloning backbone"),
        "synthetic_pDL278_like",
    ),
    RegressionCase(
        "arsenate-reductase-not-yeast",
        "bacterial_cloning_vector",
        (
            ("ORI", "bacterial replication origin"),
            ("marker", "AmpR/bla"),
            ("GOI", "arsenate reductase"),
            ("MCS", "multiple cloning site"),
        ),
        ("multiple cloning", "ORI+marker cloning backbone"),
        "synthetic_substring_boundary",
    ),
    RegressionCase(
        "central-metabolism-not-CEN-yeast",
        "bacterial_cloning_vector",
        (
            ("ORI", "bacterial replication origin"),
            ("marker", "AmpR/bla"),
            ("GOI", "central metabolism protein"),
            ("MCS", "multiple cloning site"),
        ),
        ("multiple cloning", "ORI+marker cloning backbone"),
        "synthetic_substring_boundary",
    ),
    RegressionCase(
        "streptomycin-not-TRE-mammalian",
        "bacterial_cloning_vector",
        (
            ("ORI", "bacterial replication origin"),
            ("marker", "streptomycin resistance"),
            ("GOI", "generic CDS annotation"),
            ("MCS", "multiple cloning site"),
        ),
        ("multiple cloning", "ORI+marker cloning backbone"),
        "synthetic_substring_boundary",
    ),
    RegressionCase(
        "single-LTR-cloning-backbone",
        "bacterial_cloning_vector",
        (
            ("ORI", "pUC origin"),
            ("marker", "AmpR/bla"),
            ("other", "LTR"),
            ("MCS", "multiple cloning site"),
        ),
        ("puc", "multiple cloning"),
        "synthetic_single_ltr",
    ),
    RegressionCase(
        "single-WPRE-cloning-backbone",
        "bacterial_cloning_vector",
        (
            ("ORI", "pUC origin"),
            ("marker", "AmpR/bla"),
            ("other", "WPRE"),
            ("MCS", "multiple cloning site"),
        ),
        ("puc", "multiple cloning"),
        "synthetic_single_viral_element",
    ),
    RegressionCase(
        "partial-CMV-no-payload",
        "unknown",
        (("ORI", "pUC origin"), ("marker", "AmpR/bla"), ("promoter", "CMV promoter")),
        ("no profile-specific signals",),
        "synthetic_ambiguous",
    ),
    RegressionCase(
        "generic-CDS-no-regulatory-context",
        "unknown",
        (("GOI", "hypothetical protein"),),
        ("no profile-specific signals",),
        "synthetic_ambiguous",
    ),
    RegressionCase(
        "origin-only",
        "unknown",
        (("ORI", "uncharacterized replication origin"),),
        ("no profile-specific signals",),
        "synthetic_ambiguous",
    ),
    RegressionCase(
        "LTR-only-fragment",
        "unknown",
        (("other", "LTR"),),
        ("no profile-specific signals",),
        "synthetic_ambiguous",
    ),
    RegressionCase(
        "reporter-name-without-backbone",
        "mammalian_reporter_vector",
        (("GOI", "mCherry reporter"),),
        ("mcherry", "reporter"),
        "synthetic_reporter_fragment",
    ),
    RegressionCase(
        "Cas9-only-module",
        "crispr_vector",
        (("GOI", "SpCas9 nuclease"),),
        ("cas9",),
        "synthetic_crispr_fragment",
    ),
    RegressionCase(
        "dual-host-expression-shuttle-with-CMV",
        "mammalian_expression_vector",
        (
            ("ORI", "ColE1 E. coli origin"),
            ("ORI", "second-host replication origin"),
            ("marker", "AmpR/bla"),
            ("promoter", "CMV immediate early promoter"),
            ("GOI", "oriented mammalian CDS"),
            ("terminator", "BGH polyadenylation signal"),
        ),
        ("cmv", "bgh", "polyadenylation"),
        "synthetic_dual_host_expression",
    ),
)


ALL_CASES = PUBLISHED_CASES + SYNTHETIC_EDGE_CASES


@pytest.mark.parametrize("case", ALL_CASES, ids=lambda case: case.name)
def test_classifier_regression_matrix(case: RegressionCase) -> None:
    result = classify(annotated(case))

    assert result.profile == case.expected_profile, (
        f"{case.name} ({case.source_key}) classified as {result.profile}; "
        f"expected {case.expected_profile}; signals={result.signals}"
    )
    assert trace_contains_any(result.signals, case.trace_any), (
        f"{case.name} ({case.source_key}) trace {result.signals} did not include "
        f"any expected reasoning token from {case.trace_any}"
    )


def test_regression_matrix_spans_every_defined_profile_and_unknown() -> None:
    assert {case.expected_profile for case in ALL_CASES} == {
        "bacterial_cloning_vector",
        "bacterial_expression_vector",
        "mammalian_expression_vector",
        "mammalian_reporter_vector",
        "lentiviral_or_retroviral_transfer_vector",
        "crispr_vector",
        "yeast_shuttle_vector",
        "general_shuttle_vector",
        "unknown",
    }


def test_regression_matrix_has_at_least_thirty_labeled_cases() -> None:
    assert len(ALL_CASES) >= 30

