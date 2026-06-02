from __future__ import annotations

import pytest

from packages.core.schemas import DesignSpec, GeneratedSequence, Plasmid, RetrievedPlasmid
from packages.generation import FAKE_GENERATOR_VERSION, FakeGenerator, MarkerSwap


def template() -> RetrievedPlasmid:
    plasmid = Plasmid(
        id="curated:test-template",
        source="curated",
        name="test-template",
        sequence="AAAACCCCGGGGTTTT",
        length=16,
        organism="Escherichia coli",
        vector_type="bacterial_cloning_vector",
        markers=["ampR"],
        annotation_complete=True,
        raw_ref="raw/curated/test-template.gb",
    )
    return RetrievedPlasmid(plasmid=plasmid, score=1.0, matched_fields=["lexical_name"])


def test_fake_generator_returns_top_template_as_schema_valid_candidate() -> None:
    generated = FakeGenerator().generate(DesignSpec(organism="Escherichia coli"), [template()], n=2)

    assert len(generated) == 2
    assert all(isinstance(candidate, GeneratedSequence) for candidate in generated)
    assert all(candidate.annotated_sequence.sequence == "AAAACCCCGGGGTTTT" for candidate in generated)
    assert all(candidate.annotated_sequence.annotation_complete is False for candidate in generated)
    assert all(candidate.parent_template_ids == ["curated:test-template"] for candidate in generated)
    assert all(candidate.model_version == FAKE_GENERATOR_VERSION for candidate in generated)


def test_fake_generator_applies_explicit_marker_swap_deterministically() -> None:
    generator = FakeGenerator(marker_swap=MarkerSwap(original_sequence="CCCC", replacement_sequence="ATAT"))

    first = generator.generate(DesignSpec(organism="Escherichia coli"), [template()])
    second = generator.generate(DesignSpec(organism="Escherichia coli"), [template()])

    assert first == second
    assert first[0].annotated_sequence.sequence == "AAAAATATGGGGTTTT"


def test_fake_generator_returns_no_candidates_without_templates() -> None:
    assert FakeGenerator().generate(DesignSpec(organism="Escherichia coli"), []) == []


def test_fake_generator_rejects_non_positive_candidate_count() -> None:
    with pytest.raises(ValueError, match="n must be positive"):
        FakeGenerator().generate(DesignSpec(organism="Escherichia coli"), [template()], n=0)


def test_marker_swap_requires_one_exact_original_sequence_match() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        FakeGenerator(marker_swap=MarkerSwap("ACAC", "ATAT")).generate(
            DesignSpec(organism="Escherichia coli"),
            [template()],
        )
