from __future__ import annotations

import pytest
from pydantic import ValidationError

from packages.core.schemas import (
    AnnotatedFeature,
    AnnotatedSequence,
    DesignSpec,
    ExperimentalContext,
    FeatureRegion,
    GeneratedSequence,
    Match,
    OutcomeReport,
    Plasmid,
    PlasmidRecommendation,
    Provenance,
    RetrievedPlasmid,
    RetrievalResult,
    TextSpan,
    ValidationCheck,
    ValidationReport,
    Vector,
)


SEQUENCE = "ATGCGTACGTAGCTAGCTAA"


def example_plasmid() -> Plasmid:
    return Plasmid(
        id="addgene:12345",
        source="addgene",
        name="Example CMV GFP",
        sequence=SEQUENCE.lower(),
        length=len(SEQUENCE),
        organism="Escherichia coli",
        vector_type="mammalian expression",
        markers=["AmpR"],
        promoters=["CMV"],
        publication_doi="10.1000/example",
        use_cases=["fluorescent reporter"],
        annotation_complete=True,
        raw_ref="raw/addgene/12345.json",
    )


def example_annotated_sequence() -> AnnotatedSequence:
    return AnnotatedSequence(
        sequence=SEQUENCE,
        topology="circular",
        annotation_complete=True,
        features=[
            AnnotatedFeature(type="promoter", start=0, end=6, strand=1, name="CMV", confidence=0.98),
            AnnotatedFeature(type="GOI", start=6, end=15, strand=1, name="GFP", confidence=0.92),
            AnnotatedFeature(type="terminator", start=15, end=20, strand=1, name="bGH polyA", confidence=0.85),
        ],
    )


def test_plasmid_validates_representative_record() -> None:
    plasmid = example_plasmid()

    assert plasmid.sequence == SEQUENCE
    assert plasmid.length == len(SEQUENCE)
    assert plasmid.source == "addgene"


def test_plasmid_rejects_length_mismatch_and_non_acgt_sequence() -> None:
    with pytest.raises(ValidationError, match="length must match sequence length"):
        Plasmid(**{**example_plasmid().model_dump(), "length": 1})

    with pytest.raises(ValidationError, match="non-ACGT"):
        Plasmid(**{**example_plasmid().model_dump(), "sequence": "ACGTN", "length": 5})


def test_experimental_context_validates_representative_record() -> None:
    context = ExperimentalContext(
        id="ctx:1",
        plasmid_ids=["addgene:12345"],
        organism="Homo sapiens",
        cell_line="HEK293T",
        vector_type="lentiviral",
        genes=["BRCA1"],
        tags=["GFP"],
        promoter_type="doxycycline-inducible",
        inducer="doxycycline",
        application="live-cell imaging",
        assay="DNA repair foci imaging",
        provenance=Provenance(
            doi="10.1000/example",
            sentence_span=TextSpan(start=10, end=120, text="Example experimental sentence."),
        ),
        extraction_confidence=0.87,
    )

    assert context.plasmid_ids == ["addgene:12345"]
    assert context.extraction_confidence == pytest.approx(0.87)


def test_annotated_sequence_validates_features_and_incomplete_property() -> None:
    annotated = example_annotated_sequence()

    assert annotated.topology == "circular"
    assert annotated.features[1].name == "GFP"
    assert annotated.annotation_incomplete is False

    with pytest.raises(ValidationError, match="outside the sequence"):
        AnnotatedSequence(
            sequence=SEQUENCE,
            topology="linear",
            annotation_complete=False,
            features=[AnnotatedFeature(type="ORI", start=0, end=100, strand=1, name="pUC ori", confidence=0.8)],
        )


def test_design_spec_validates_representative_intent_parse_output() -> None:
    spec = DesignSpec(
        organism="Homo sapiens",
        cell_line="HEK293T",
        vector_type="lentiviral",
        genes=["BRCA1"],
        tags=["GFP"],
        promoter_type="TRE",
        inducer="doxycycline",
        markers=["puromycin"],
        application="live-cell imaging",
        cloning_method="Gibson",
        constraints=["avoid BsmBI"],
    )

    assert spec.clarification_needed is False
    assert spec.genes == ["BRCA1"]

    with pytest.raises(ValidationError, match="clarification_question"):
        DesignSpec(organism="Homo sapiens", clarification_needed=True)


def test_validation_report_validates_representative_report() -> None:
    report = ValidationReport(
        overall="WARN",
        checks=[
            ValidationCheck(
                name="restriction_sites",
                status="PASS",
                message="No forbidden sites found.",
                region=None,
            ),
            ValidationCheck(
                name="annotation_completeness",
                status="WARN",
                message="Terminator confidence is below the preferred threshold.",
                region=FeatureRegion(start=15, end=20),
            ),
        ],
        generated_by_model_version="fake-validator-0",
    )

    assert report.overall == "WARN"
    assert report.checks[1].region is not None


def test_supporting_types_validate_retrieval_generation_and_vectors() -> None:
    plasmid = example_plasmid()
    annotated = example_annotated_sequence()

    retrieved = RetrievedPlasmid(plasmid=plasmid, score=0.91, matched_fields=["promoters", "use_cases"])
    recommendation = PlasmidRecommendation(
        plasmid_id=plasmid.id,
        rank=1,
        score=0.91,
        why_relevant="Example CMV GFP is relevant because it has a CMV promoter.",
        suggested_adaptations=["Swap marker if needed."],
        caveats=[],
    )
    retrieval_result = RetrievalResult(
        spec=DesignSpec(organism="Homo sapiens"),
        retrieved=[retrieved],
        recommendations=[recommendation],
        generated_by="fake-retrieval-0",
    )
    generated = GeneratedSequence(
        annotated_sequence=annotated,
        model_version="fake-generator-0",
        parent_template_ids=[plasmid.id],
    )
    match = Match(id=plasmid.id, score=0.88, metadata={"source": "addgene"})
    vector = Vector([0.1, 0.2, 0.3])
    outcome = OutcomeReport(
        design_id="design-1",
        model_version="fake-generator-0",
        construct_validated=True,
        sequencing_result="Sanger sequence matched the insert junctions.",
        expression_result="GFP signal observed above negative control.",
        training_consent=True,
        outcome_label="positive",
        provenance={"reporter": "user"},
    )

    assert retrieved.score == pytest.approx(0.91)
    assert retrieval_result.recommendations[0].plasmid_id == plasmid.id
    assert generated.parent_template_ids == ["addgene:12345"]
    assert match.metadata["source"] == "addgene"
    assert vector.root == [0.1, 0.2, 0.3]
    assert outcome.training_consent is True
