from __future__ import annotations

import pytest

from packages.core.schemas import DesignSpec, Plasmid, RetrievedPlasmid
from packages.generation import FAKE_GENERATOR_VERSION, FakeGenerator


def _template() -> RetrievedPlasmid:
    plasmid = Plasmid(
        id="curated:pUC19",
        source="curated",
        name="pUC19c",
        sequence="ACGT" * 100,
        length=400,
        organism="Cloning vector pUC19c",
        vector_type="bacterial_cloning_vector",
        markers=["AmpR"],
        promoters=["lac promoter region"],
        use_cases=["bacterial_cloning"],
        annotation_complete=True,
        raw_ref="raw/curated/pUC19.gb",
    )
    return RetrievedPlasmid(plasmid=plasmid, score=1.0, matched_fields=["semantic", "exact_name"])


def test_fake_generator_returns_top_template_sequence_deterministically() -> None:
    generator = FakeGenerator()
    spec = DesignSpec(organism="Escherichia coli", vector_type="bacterial_cloning_vector")

    first = generator.generate(spec, [_template()], n=1)
    second = generator.generate(spec, [_template()], n=1)

    assert first == second
    assert first[0].model_version == FAKE_GENERATOR_VERSION
    assert first[0].parent_template_ids == ["curated:pUC19"]
    assert first[0].annotated_sequence.sequence == _template().plasmid.sequence
    assert first[0].annotated_sequence.topology == "circular"


def test_fake_generator_returns_empty_without_templates_and_rejects_invalid_n() -> None:
    generator = FakeGenerator()
    spec = DesignSpec(organism="Escherichia coli")

    assert generator.generate(spec, []) == []
    with pytest.raises(ValueError, match="n must be positive"):
        generator.generate(spec, [_template()], n=0)
