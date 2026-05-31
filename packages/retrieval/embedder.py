from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass
from typing import Protocol


PHASE1_MODEL_NAME = "NeuML/pubmedbert-base-embeddings"
PHASE1_MODEL_REVISION = "b79526d6ef3645e0df4530322e266f24c829f5ef"
PHASE1_EMBEDDING_DIMENSION = 768
DEFAULT_MAX_LENGTH = 512


class Embedder(Protocol):
    @property
    def dim(self) -> int: ...

    @property
    def model_name(self) -> str: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return [0.0 for _ in vector]
    return [value / norm for value in vector]


def _hash_bytes(text: str, *, index: int) -> bytes:
    return hashlib.sha256(f"{index}:{text}".encode("utf-8")).digest()


@dataclass(frozen=True)
class FakeEmbedder:
    dimension: int = PHASE1_EMBEDDING_DIMENSION
    name: str = "fake-hash-embedder-v1"

    @property
    def dim(self) -> int:
        return self.dimension

    @property
    def model_name(self) -> str:
        return self.name

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            values = [0.0] * self.dimension
            for index in range(self.dimension):
                digest = _hash_bytes(text, index=index)
                bucket = int.from_bytes(digest[:8], "big", signed=False)
                values[index] = (bucket / ((1 << 63) - 1)) - 1.0
            vectors.append(_l2_normalize(values))
        return vectors


class TransformersEmbedder:
    def __init__(
        self,
        *,
        model_name: str = PHASE1_MODEL_NAME,
        revision: str = PHASE1_MODEL_REVISION,
        cache_dir: str | None = None,
        local_files_only: bool = False,
        max_length: int = DEFAULT_MAX_LENGTH,
        device: str | None = None,
    ) -> None:
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError("TransformersEmbedder requires torch and transformers to be installed") from exc

        self._torch = torch
        resolved_cache_dir = cache_dir or os.environ.get("HF_HUB_CACHE") or os.environ.get("HF_HOME")
        self._tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            revision=revision,
            cache_dir=resolved_cache_dir,
            local_files_only=local_files_only,
        )
        self._model = AutoModel.from_pretrained(
            model_name,
            revision=revision,
            cache_dir=resolved_cache_dir,
            local_files_only=local_files_only,
        )
        self._model.eval()
        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(self._device)
        self._model_name = f"{model_name}@{revision}"
        self._max_length = max_length

        hidden_size = getattr(self._model.config, "hidden_size", None)
        if hidden_size != PHASE1_EMBEDDING_DIMENSION:
            raise ValueError(f"expected hidden size {PHASE1_EMBEDDING_DIMENSION}, got {hidden_size}")

    @property
    def dim(self) -> int:
        return PHASE1_EMBEDDING_DIMENSION

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        encoded = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self._max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(self._device) for key, value in encoded.items()}
        with self._torch.no_grad():
            outputs = self._model(**encoded)
        vectors = self._mean_pool(outputs.last_hidden_state, encoded["attention_mask"])
        normalized = self._torch.nn.functional.normalize(vectors, p=2, dim=1)
        return normalized.cpu().tolist()

    def _mean_pool(self, token_embeddings, attention_mask):
        mask = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        masked = token_embeddings * mask
        summed = masked.sum(dim=1)
        counts = mask.sum(dim=1).clamp(min=1e-9)
        return summed / counts
