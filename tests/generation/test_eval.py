from __future__ import annotations

from packages.core.schemas import AnnotatedFeature, AnnotatedSequence, DesignSpec, Plasmid, RetrievedPlasmid
from packages.generation.eval import GenerationEvalHarness, GenerationGoldCase, circular_exact_copy, compute_metrics
from packages.generation.generator import FakeGenerator
from packages.generation.spike import StubConstraintEngine


SEQUENCE = "ACGT" * 300


class FakeRetriever:
    def __init__(self, retrieved: list[RetrievedPlasmid]) -> None:
        self.retrieved = retrieved

    def retrieve(self, spec: DesignSpec, k: int = 5) -> list[RetrievedPlasmid]:
        del spec
        return self.retrieved[:k]


class FakeReannotator:
    def __init__(self, annotated: AnnotatedSequence) -> None:
        self.annotated = annotated

    def reannotate(self, generated, template):  # type: ignore[no-untyped-def]
        del generated, template
        return self.annotated


def test_circular_exact_copy_accepts_rotations_and_reverse_complements() -> None:
    assert circular_exact_copy("GTACAC", "ACACGT") is True
    assert circular_exact_copy("ACGT", "ACGT") is True
    assert circular_exact_copy("AAAA", "TTTT") is True
    assert circular_exact_copy("ACGA", "ACGT") is False


def test_fake_generator_eval_reports_expected_novelty_failure() -> None:
    plasmid = Plasmid(
        id="curated:pUC19",
        source="curated",
        name="pUC19",
        sequence=SEQUENCE,
        length=len(SEQUENCE),
        organism="synthetic construct",
        vector_type="plasmid",
        markers=["bla"],
        promoters=[],
        use_cases=["routine cloning"],
        annotation_complete=True,
        raw_ref="raw/curated/pUC19.gb",
    )
    annotated = AnnotatedSequence(
        sequence=SEQUENCE,
        topology="circular",
        vector_profile="bacterial_cloning_vector",
        annotation_complete=True,
        features=[
            AnnotatedFeature(type="ORI", start=0, end=40, strand=1, name="pMB1 origin", confidence=0.95),
            AnnotatedFeature(type="marker", start=50, end=100, strand=1, name="bla", confidence=0.95),
            AnnotatedFeature(type="MCS", start=120, end=160, strand=1, name="multiple cloning site", confidence=0.95),
        ],
    )
    spec = DesignSpec(
        organism="Escherichia coli",
        vector_type="bacterial_cloning_vector",
        markers=["ampicillin"],
        application="routine plasmid cloning",
    )
    case = GenerationGoldCase(
        id="case",
        query="Need a cloning vector",
        spec=spec,
        expected_components={"vector_type": "bacterial_cloning_vector", "markers": ["ampicillin"], "feature_types": ["ORI", "marker", "MCS"]},
        acceptable_template_ids=["curated:pUC19"],
    )
    harness = GenerationEvalHarness(
        retriever=FakeRetriever([RetrievedPlasmid(plasmid=plasmid, score=1.0, matched_fields=["test"])]),
        generator=FakeGenerator(),
        reannotator=FakeReannotator(annotated),
        constraint_engine=StubConstraintEngine(),
        novelty_sequences={"curated:pUC19": SEQUENCE},
    )

    result = harness.evaluate_case(case)
    candidate = result["candidates"][0]

    assert candidate["syntactic_valid"] is True
    assert candidate["component_complete"] is True
    assert candidate["constraint_passed"] is True
    assert candidate["novelty"]["novel"] is False
    assert candidate["phase2_gate_proxy_passed"] is True
    assert candidate["strict_generation_success"] is False


def test_compute_metrics_keeps_novelty_separate_from_gate_proxy() -> None:
    metrics = compute_metrics(
        [
            {
                "unsupported": False,
                "case_passed": True,
                "strict_case_passed": False,
                "candidates": [
                    {
                        "syntactic_valid": True,
                        "sane_length": True,
                        "component_complete": True,
                        "constraint_passed": True,
                        "novelty": {"novel": False},
                        "phase2_gate_proxy_passed": True,
                        "strict_generation_success": False,
                    }
                ],
            }
        ]
    )

    assert metrics["phase2_gate_proxy_rate"] == 1.0
    assert metrics["novel_rate"] == 0.0
    assert metrics["strict_generation_success_rate"] == 0.0
