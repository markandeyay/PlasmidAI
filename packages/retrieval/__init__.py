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

__all__ = [
    "ComposedDocument",
    "DEFAULT_MAX_LENGTH",
    "Embedder",
    "FakeEmbedder",
    "PHASE1_EMBEDDING_DIMENSION",
    "PHASE1_MODEL_NAME",
    "PHASE1_MODEL_REVISION",
    "TransformersEmbedder",
    "compose_plasmid_document",
]
