from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

from packages.core.schemas import RetrievalResult
from packages.retrieval.intent_parser import IntentParser, build_intent_parser
from packages.retrieval.recommender import RecommendationGenerator, build_recommendation_generator
from packages.retrieval.retriever import DEFAULT_RETRIEVAL_K, HybridRetriever, PostgresRetrievalRepository, Retriever


PIPELINE_NAME = "phase1-retrieval-pipeline-v1"


@dataclass(frozen=True)
class RetrievalPipeline:
    parser: IntentParser
    retriever: Retriever
    recommender: RecommendationGenerator
    name: str = PIPELINE_NAME

    def design_retrieval(
        self,
        free_text: str,
        *,
        clarifications: list[str] | None = None,
        k: int = DEFAULT_RETRIEVAL_K,
    ) -> RetrievalResult:
        spec = self.parser.parse(free_text, clarifications=clarifications)
        if spec.clarification_needed:
            return RetrievalResult(
                spec=spec,
                retrieved=[],
                recommendations=[],
                generated_by=self.name,
                clarification_needed=True,
                clarification_question=spec.clarification_question,
            )
        retrieved = self.retriever.retrieve(spec, k=k)
        recommendations = self.recommender.recommend(retrieved, spec)
        return RetrievalResult(
            spec=spec,
            retrieved=retrieved,
            recommendations=recommendations,
            generated_by=self.name,
            clarification_needed=False,
            clarification_question=None,
        )


def design_retrieval(free_text: str) -> RetrievalResult:
    return build_default_pipeline().design_retrieval(free_text)


def build_default_pipeline(
    *,
    k: int = DEFAULT_RETRIEVAL_K,
    use_fake_parser: bool | None = None,
    use_fake_embedder: bool = False,
    local_files_only: bool = False,
    hf_cache_dir: str | None = None,
    use_llm_recommender: bool | None = None,
) -> RetrievalPipeline:
    del k
    from packages.retrieval.embed_corpus import EmbedCorpusConfig, build_embedder, build_vector_store

    config = EmbedCorpusConfig.from_env(
        batch_size=1,
        limit=None,
        use_fake=use_fake_embedder,
        local_files_only=local_files_only,
        hf_cache_dir=hf_cache_dir,
    )
    embedder = build_embedder(config)
    vector_index = build_vector_store(config, embedder)
    vector_index.ensure_schema()
    return RetrievalPipeline(
        parser=build_intent_parser(use_fake=use_fake_parser),
        retriever=HybridRetriever(
            vector_index=vector_index,
            embedder=embedder,
            repository=PostgresRetrievalRepository(config.database_url),
        ),
        recommender=build_recommendation_generator(use_llm=use_llm_recommender),
    )


def render_retrieval_result(result: RetrievalResult) -> str:
    lines: list[str] = ["# Retrieval Design Result", ""]
    if result.clarification_needed:
        lines.extend([
            "Clarification needed before retrieval.",
            "",
            result.clarification_question or "Please clarify the design request.",
        ])
        return "\n".join(lines)

    lines.extend(
        [
            f"Parsed organism: `{result.spec.organism}`",
            f"Parsed vector type: `{result.spec.vector_type or '<unspecified>'}`",
            f"Retrieved matches: `{len(result.retrieved)}`",
            "",
        ]
    )
    for recommendation in result.recommendations:
        plasmid = next(item.plasmid for item in result.retrieved if item.plasmid.id == recommendation.plasmid_id)
        lines.extend(
            [
                f"## {recommendation.rank}. {plasmid.name} (`{plasmid.id}`)",
                f"Score: `{recommendation.score:.4f}`",
                recommendation.why_relevant,
                "",
                "Suggested adaptations:",
            ]
        )
        lines.extend(f"- {change}" for change in recommendation.suggested_adaptations)
        if recommendation.caveats:
            lines.append("")
            lines.append("Caveats:")
            lines.extend(f"- {caveat}" for caveat in recommendation.caveats)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Phase 1 retrieval-only design pipeline.")
    parser.add_argument("--text", required=True, help="Free-text plasmid design request.")
    parser.add_argument("--k", type=int, default=DEFAULT_RETRIEVAL_K)
    parser.add_argument("--fake-parser", action="store_true", help="Use deterministic parser even if LLM env vars are configured.")
    parser.add_argument("--fake-embedder", action="store_true", help="Use fake query embeddings; requires a fake-embedded corpus.")
    parser.add_argument("--local-files-only", action="store_true", help="Load the embedding model from local cache only.")
    parser.add_argument("--hf-cache-dir")
    parser.add_argument("--llm-recommender", action="store_true", help="Use configured LLM recommendation generator.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of markdown.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    pipeline = build_default_pipeline(
        use_fake_parser=True if args.fake_parser else None,
        use_fake_embedder=args.fake_embedder,
        local_files_only=args.local_files_only,
        hf_cache_dir=args.hf_cache_dir,
        use_llm_recommender=True if args.llm_recommender else None,
    )
    result = pipeline.design_retrieval(args.text, k=args.k)
    if args.json:
        print(json.dumps(result.model_dump(mode="json"), indent=2))
    else:
        print(render_retrieval_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
