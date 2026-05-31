"""Retrieval package."""

from .document_composer import ComposedDocument, compose_plasmid_document
from .embedder import (
    DEFAULT_MAX_LENGTH,
    PHASE1_EMBEDDING_DIMENSION,
    PHASE1_MODEL_NAME,
    PHASE1_MODEL_REVISION,
    Embedder,
    FakeEmbedder,
    TransformersEmbedder,
)
from .intent_parser import FakeIntentParser, IntentParser, LLMIntentParser
from .recommender import LLMRecommendationGenerator, RecommendationGenerator, TemplateRecommendationGenerator
from .retriever import HybridRetriever, Retriever


def design_retrieval(free_text: str):
    from .pipeline import design_retrieval as run_design_retrieval

    return run_design_retrieval(free_text)

__all__ = [
    "ComposedDocument",
    "DEFAULT_MAX_LENGTH",
    "Embedder",
    "FakeEmbedder",
    "FakeIntentParser",
    "HybridRetriever",
    "IntentParser",
    "LLMIntentParser",
    "LLMRecommendationGenerator",
    "PHASE1_EMBEDDING_DIMENSION",
    "PHASE1_MODEL_NAME",
    "PHASE1_MODEL_REVISION",
    "TransformersEmbedder",
    "RecommendationGenerator",
    "Retriever",
    "TemplateRecommendationGenerator",
    "compose_plasmid_document",
    "design_retrieval",
]
