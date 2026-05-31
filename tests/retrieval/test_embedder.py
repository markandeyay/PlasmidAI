from __future__ import annotations

import math

from packages.retrieval.embedder import FakeEmbedder, PHASE1_EMBEDDING_DIMENSION


def test_fake_embedder_is_deterministic_and_normalized() -> None:
    embedder = FakeEmbedder()

    first = embedder.embed(["CMV GFP reporter", "AmpR bacterial cloning"])
    second = embedder.embed(["CMV GFP reporter", "AmpR bacterial cloning"])

    assert embedder.dim == PHASE1_EMBEDDING_DIMENSION
    assert embedder.model_name == "fake-hash-embedder-v1"
    assert first == second
    assert len(first) == 2
    assert len(first[0]) == PHASE1_EMBEDDING_DIMENSION

    norm = math.sqrt(sum(value * value for value in first[0]))
    assert norm == 1.0
    assert first[0] != first[1]
