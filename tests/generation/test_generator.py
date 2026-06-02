from __future__ import annotations

import pytest

from packages.core.schemas import DesignSpec, GeneratedSequence, Plasmid, RetrievedPlasmid
from packages.generation import FAKE_GENERATOR_VERSION, FakeGenerator, MarkerSwap


def _template() -> RetrievedPlasmid:
    plasmid = Plasmid(
        id="curated:pUC19",
        source="curated",
        name="pUC19c",
        sequence="AAAACCCCGGGGTTTT",
        length=16,
        organism="Cloning vector pUC19c",
        vector_type="bacterial_cloning_vector",
        markers=["AmpR"],
        promoters=["lac promoter region"],
        use_cases=["bacterial_cloning"],
        annotation_complete=True,
        raw_ref="raw/curated/pUC19.gb",
    )
    return RetrievedPlasmid(plasmid=plasmid, score=1.0, matched_fields=["semantic", "exact_name"])


def test_fake_generator_returns_top_template_as_schema_valid_candidate() -> None:
    generator = FakeGenerator()
    spec = DesignSpec(organism="Escherichia coli", vector_type="bacterial_cloning_vector")

    generated = generator.generate(spec, [_template()], n=2)

    assert len(generated) == 2
    assert all(isinstance(candidate, GeneratedSequence) for candidate in generated)
    assert all(candidate.model_version == FAKE_GENERATOR_VERSION for candidate in generated)
    assert all(candidate.parent_template_ids == ["curated:pUC19"] for candidate in generated)
    assert all(candidate.annotated_sequence.sequence == _template().plasmid.sequence for candidate in generated)
    assert all(candidate.annotated_sequence.topology == "circular" for candidate in generated)
    assert all(candidate.annotated_sequence.annotation_complete is False for candidate in generated)


def test_fake_generator_applies_explicit_marker_swap_deterministically() -> None:
    generator = FakeGenerator(marker_swap=MarkerSwap(original_sequence="CCCC", replacement_sequence="ATAT"))
    spec = DesignSpec(organism="Escherichia coli", vector_type="bacterial_cloning_vector")

    first = generator.generate(spec, [_template()])
    second = generator.generate(spec, [_template()])

    assert first == second
    assert first[0].annotated_sequence.sequence == "AAAAATATGGGGTTTT"


def test_fake_generator_returns_empty_without_templates_and_rejects_invalid_n() -> None:
    generator = FakeGenerator()
    spec = DesignSpec(organism="Escherichia coli")

    assert generator.generate(spec, []) == []
    with pytest.raises(ValueError, match="n must be positive"):
        generator.generate(spec, [_template()], n=0)


def test_marker_swap_requires_one_exact_original_sequence_match() -> None:
    generator = FakeGenerator(marker_swap=MarkerSwap(original_sequence="ACAC", replacement_sequence="ATAT"))
    spec = DesignSpec(organism="Escherichia coli", vector_type="bacterial_cloning_vector")

    with pytest.raises(ValueError, match="exactly one"):
        generator.generate(spec, [_template()])
