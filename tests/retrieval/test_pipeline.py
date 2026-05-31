from __future__ import annotations

from dataclasses import dataclass

from packages.core.schemas import DesignSpec, Plasmid, PlasmidRecommendation, RetrievedPlasmid
from packages.retrieval.pipeline import RetrievalPipeline, render_retrieval_result


@dataclass
class StaticParser:
    spec: DesignSpec
    calls: list[str]

    def parse(self, free_text: str, clarifications: list[str] | None = None) -> DesignSpec:
        self.calls.append(free_text)
        return self.spec


class StaticRetriever:
    def __init__(self, results: list[RetrievedPlasmid]) -> None:
        self.results = results
        self.calls: list[DesignSpec] = []

    def retrieve(self, spec: DesignSpec, k: int = 5) -> list[RetrievedPlasmid]:
        self.calls.append(spec)
        return self.results[:k]


class StaticRecommender:
    name = "static-recommender"

    def __init__(self, recommendations: list[PlasmidRecommendation]) -> None:
        self.recommendations = recommendations
        self.calls: list[tuple[list[RetrievedPlasmid], DesignSpec]] = []

    def recommend(self, retrieved: list[RetrievedPlasmid], spec: DesignSpec) -> list[PlasmidRecommendation]:
        self.calls.append((retrieved, spec))
        return self.recommendations


def example_plasmid() -> Plasmid:
    return Plasmid(
        id="curated:pEGFP-N1",
        source="curated",
        name="pEGFP-N1",
        sequence="ACGT" * 100,
        length=400,
        organism="Cloning vector pEGFP-N1",
        vector_type="mammalian reporter vector",
        markers=["neomycin phosphotransferase"],
        promoters=["CMV"],
        use_cases=["fluorescent reporting"],
        annotation_complete=True,
        raw_ref="raw/curated/pEGFP-N1.gb",
    )


def test_pipeline_returns_clarification_without_retrieval() -> None:
    parser = StaticParser(
        DesignSpec(
            organism="unknown",
            clarification_needed=True,
            clarification_question="Which organism?",
        ),
        [],
    )
    retriever = StaticRetriever([])
    recommender = StaticRecommender([])

    result = RetrievalPipeline(parser=parser, retriever=retriever, recommender=recommender).design_retrieval("make plasmid")

    assert result.clarification_needed is True
    assert result.clarification_question == "Which organism?"
    assert result.retrieved == []
    assert retriever.calls == []
    assert recommender.calls == []


def test_pipeline_wires_parser_retriever_and_recommender() -> None:
    spec = DesignSpec(organism="Homo sapiens", vector_type="mammalian_reporter_vector")
    retrieved = [RetrievedPlasmid(plasmid=example_plasmid(), score=0.92, matched_fields=["semantic", "vector_type"])]
    recommendations = [
        PlasmidRecommendation(
            plasmid_id="curated:pEGFP-N1",
            rank=1,
            score=0.92,
            why_relevant="pEGFP-N1 is relevant because it matched vector_type.",
            suggested_adaptations=["Use as a GFP reporter template."],
            caveats=[],
        )
    ]
    parser = StaticParser(spec, [])
    retriever = StaticRetriever(retrieved)
    recommender = StaticRecommender(recommendations)

    result = RetrievalPipeline(parser=parser, retriever=retriever, recommender=recommender).design_retrieval("gfp reporter", k=3)

    assert result.spec == spec
    assert result.retrieved == retrieved
    assert result.recommendations == recommendations
    assert retriever.calls == [spec]
    assert recommender.calls == [(retrieved, spec)]


def test_render_retrieval_result_includes_recommendations_and_caveats() -> None:
    plasmid = example_plasmid()
    result = RetrievalPipeline(
        parser=StaticParser(DesignSpec(organism="Homo sapiens"), []),
        retriever=StaticRetriever([]),
        recommender=StaticRecommender([]),
    ).design_retrieval("unused")
    result = result.model_copy(
        update={
            "retrieved": [RetrievedPlasmid(plasmid=plasmid, score=0.91, matched_fields=["semantic"])],
            "recommendations": [
                PlasmidRecommendation(
                    plasmid_id=plasmid.id,
                    rank=1,
                    score=0.91,
                    why_relevant="pEGFP-N1 is relevant because it matched semantic retrieval.",
                    suggested_adaptations=["Swap promoter if needed."],
                    caveats=["Verify annotation."],
                )
            ],
        }
    )

    rendered = render_retrieval_result(result)

    assert "pEGFP-N1" in rendered
    assert "Swap promoter" in rendered
    assert "Verify annotation" in rendered
