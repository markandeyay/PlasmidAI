from __future__ import annotations

import json
import os

import pytest

from packages.core.schemas import DesignSpec
from packages.retrieval.intent_parser import FakeIntentParser, LLMIntentParser, OpenAIIntentClient


def test_fake_intent_parser_normalizes_lentiviral_dox_hek293_and_tagged_gene() -> None:
    spec = FakeIntentParser().parse(
        "I need a lenti vector expressing GFP-tagged BRCA1 under a dox inducible promoter in 293 cells for live imaging."
    )

    assert spec.organism == "Homo sapiens"
    assert spec.cell_line == "HEK293"
    assert spec.vector_type == "lentiviral_or_retroviral_transfer_vector"
    assert spec.genes == ["BRCA1"]
    assert spec.tags == ["GFP"]
    assert spec.promoter_type == "doxycycline-inducible"
    assert spec.inducer == "doxycycline"
    assert spec.application == "live imaging"
    assert spec.clarification_needed is False


def test_fake_intent_parser_normalizes_hek293t_and_bacterial_expression_query() -> None:
    hek = FakeIntentParser().parse("Need a CMV GFP reporter in 293T cells with G418 selection.")
    bacterial = FakeIntentParser().parse("Need E coli T7 expression of His-tagged GFP with kan resistance.")

    assert hek.cell_line == "HEK293T"
    assert hek.organism == "Homo sapiens"
    assert hek.promoter_type == "CMV"
    assert hek.markers == ["neomycin/G418"]

    assert bacterial.organism == "Escherichia coli"
    assert bacterial.vector_type == "bacterial_expression_vector"
    assert bacterial.promoter_type == "T7"
    assert bacterial.genes == ["GFP"]
    assert bacterial.tags == ["His6"]
    assert bacterial.markers == ["kanamycin"]


def test_fake_intent_parser_extracts_retrieval_gold_style_queries() -> None:
    cloning = FakeIntentParser().parse("Recommend a low-copy bacterial cloning plasmid with chloramphenicol resistance.")
    yeast = FakeIntentParser().parse("I need a yeast centromere shuttle plasmid specifically selected by URA3 rather than LEU2.")
    puc = FakeIntentParser().parse("Recommend a high-copy ampicillin-resistant pUC plasmid when either MCS orientation is acceptable.")
    pbr = FakeIntentParser().parse(
        "Which curated cloning vector carries both ampicillin and tetracycline resistance with a pMB1-derived replication region?"
    )

    assert cloning.organism == "Escherichia coli"
    assert cloning.vector_type == "bacterial_cloning_vector"
    assert cloning.markers == ["chloramphenicol"]
    assert "low-copy" in cloning.constraints

    assert yeast.organism == "Saccharomyces cerevisiae"
    assert yeast.vector_type == "yeast_shuttle_vector"
    assert yeast.markers == ["URA3"]
    assert "exclude LEU2" in yeast.constraints
    assert yeast.application == "yeast transformation"
    assert puc.organism == "Escherichia coli"
    assert puc.markers == ["ampicillin"]
    assert pbr.clarification_needed is False
    assert pbr.markers == ["ampicillin", "tetracycline"]


def test_fake_intent_parser_clarifies_missing_or_ambiguous_critical_fields() -> None:
    generic = FakeIntentParser().parse("Make me a plasmid to express my gene in mammalian cells.")
    viral = FakeIntentParser().parse("I want a viral vector with antibiotic resistance.")

    assert generic.clarification_needed is True
    assert generic.clarification_question is not None
    assert generic.organism == "unknown"

    assert viral.clarification_needed is True
    assert viral.clarification_question is not None
    assert "viral" in viral.clarification_question.casefold()


def test_fake_intent_parser_uses_canned_specs_and_clarification_answers() -> None:
    parser = FakeIntentParser(
        {
            "custom query": DesignSpec(
                organism="E. coli",
                vector_type="cloning vector",
                markers=["AmpR"],
            )
        }
    )

    canned = parser.parse("custom query")
    clarified = FakeIntentParser().parse("Need a reporter plasmid.", clarifications=["Use HEK293 cells and GFP."])

    assert canned.organism == "Escherichia coli"
    assert canned.vector_type == "bacterial_cloning_vector"
    assert canned.markers == ["ampicillin"]

    assert clarified.organism == "Homo sapiens"
    assert clarified.cell_line == "HEK293"
    assert clarified.genes == ["GFP"]


def test_llm_intent_parser_validates_and_post_normalizes_output() -> None:
    def fake_llm(_messages, _schema) -> str:
        return json.dumps(
            {
                "organism": "E. coli",
                "cell_line": None,
                "vector_type": "lenti",
                "genes": ["BRCA1"],
                "tags": ["gfp"],
                "promoter_type": "dox inducible",
                "inducer": "dox",
                "markers": ["puro"],
                "application": "live imaging",
                "cloning_method": None,
                "constraints": [],
                "clarification_needed": False,
                "clarification_question": None,
            }
        )

    spec = LLMIntentParser(fake_llm).parse("ignored")

    assert spec.organism == "Escherichia coli"
    assert spec.vector_type == "lentiviral_or_retroviral_transfer_vector"
    assert spec.tags == ["GFP"]
    assert spec.promoter_type == "doxycycline-inducible"
    assert spec.inducer == "doxycycline"
    assert spec.markers == ["puromycin"]


def test_llm_intent_parser_rejects_invalid_json_and_extra_keys() -> None:
    with pytest.raises(ValueError, match="invalid JSON"):
        LLMIntentParser(lambda _messages, _schema: "not json").parse("x")

    def extra_key(_messages, _schema) -> str:
        payload = {
            "organism": "Homo sapiens",
            "cell_line": None,
            "vector_type": None,
            "genes": [],
            "tags": [],
            "promoter_type": None,
            "inducer": None,
            "markers": [],
            "application": "expression",
            "cloning_method": None,
            "constraints": [],
            "clarification_needed": False,
            "clarification_question": None,
            "invented": True,
        }
        return json.dumps(payload)

    with pytest.raises(ValueError, match="invalid DesignSpec"):
        LLMIntentParser(extra_key).parse("x")


@pytest.mark.skipif(
    not (os.environ.get("RUN_REAL_LLM_INTENT_TESTS") == "1" and os.environ.get("OPENAI_API_KEY")),
    reason="real LLM intent parser test requires RUN_REAL_LLM_INTENT_TESTS=1 and OPENAI_API_KEY",
)
def test_openai_intent_client_smoke() -> None:
    parser = LLMIntentParser(OpenAIIntentClient.from_env())

    spec = parser.parse("Need E coli T7 expression of His-tagged GFP with kan resistance.")

    assert spec.organism == "Escherichia coli"
    assert spec.vector_type == "bacterial_expression_vector"
