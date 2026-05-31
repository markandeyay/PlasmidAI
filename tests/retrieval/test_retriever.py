from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import pytest

from packages.core.schemas import DesignSpec, Plasmid
from packages.retrieval.document_composer import DOCUMENT_VERSION
from packages.retrieval.retriever import (
    HybridRetriever,
    compose_design_query_document,
    matched_fields,
    passes_structured_filters,
)
from packages.retrieval.vector_store import EmbeddingRecord, InMemoryVectorStore, VectorMatch


class StaticEmbedder:
    def __init__(self, vector: list[float] | None = None) -> None:
        self.vector = vector or [1.0, 0.0, 0.0]
        self.texts: list[str] = []

    @property
    def dim(self) -> int:
        return len(self.vector)

    @property
    def model_name(self) -> str:
        return "static-test-embedder"

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.texts.extend(texts)
        return [list(self.vector) for _ in texts]


@dataclass
class FakeRepository:
    plasmids: list[Plasmid]

    def get_plasmids(self, plasmid_ids: Sequence[str]) -> list[Plasmid]:
        by_id = {plasmid.id: plasmid for plasmid in self.plasmids}
        return [by_id[plasmid_id] for plasmid_id in plasmid_ids if plasmid_id in by_id]


class RecordingVectorIndex:
    dimension = 3
    model_name = "static-test-embedder"

    def __init__(self, matches: list[VectorMatch]) -> None:
        self.matches = matches
        self.calls: list[dict[str, Any]] = []

    def ensure_schema(self) -> None:
        return None

    def filter_changed(self, documents: Mapping[str, str]) -> set[str]:
        return set(documents)

    def upsert(self, records):
        raise NotImplementedError

    def query(self, query_vector, *, limit: int = 10, metadata_filter=None) -> list[VectorMatch]:
        self.calls.append({"query_vector": query_vector, "limit": limit, "metadata_filter": metadata_filter})
        return self.matches[:limit]


def plasmid(
    plasmid_id: str,
    *,
    name: str | None = None,
    organism: str | None = "synthetic construct",
    vector_type: str | None = None,
    markers: list[str] | None = None,
    promoters: list[str] | None = None,
    use_cases: list[str] | None = None,
    annotation_complete: bool = True,
) -> Plasmid:
    return Plasmid(
        id=plasmid_id,
        source="curated" if plasmid_id.startswith("curated:") else "genbank",
        name=name or plasmid_id,
        sequence="ACGT" * 100,
        length=400,
        organism=organism,
        vector_type=vector_type,
        markers=markers or [],
        promoters=promoters or [],
        use_cases=use_cases or [],
        annotation_complete=annotation_complete,
        raw_ref=f"raw/{plasmid_id}.gb",
    )


def metadata(
    *,
    vector_profile: str,
    markers: list[str] | None = None,
    promoters: list[str] | None = None,
    payloads: list[str] | None = None,
    use_cases: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "document_version": DOCUMENT_VERSION,
        "vector_profile": vector_profile,
        "candidates": {
            "markers": [{"label": value} for value in markers or []],
            "promoters": [{"label": value} for value in promoters or []],
            "payloads": [{"label": value} for value in payloads or []],
            "use_cases": use_cases or [],
        },
    }


def test_compose_design_query_document_renders_non_empty_spec_fields() -> None:
    spec = DesignSpec(
        organism="Homo sapiens",
        cell_line="HEK293",
        vector_type="lentiviral_or_retroviral_transfer_vector",
        genes=["BRCA1"],
        tags=["GFP"],
        promoter_type="doxycycline-inducible",
        inducer="doxycycline",
        markers=["puromycin"],
        application="live imaging",
        cloning_method="Gibson",
        constraints=["avoid BsmBI"],
    )

    text = compose_design_query_document(spec)

    assert "Homo sapiens" in text
    assert "HEK293" in text
    assert "lentiviral or retroviral transfer vector" in text
    assert "BRCA1" in text
    assert "GFP" in text
    assert "puromycin" in text
    assert "avoid BsmBI" in text
    assert "Specific constraints and identity cues" in text


def test_hybrid_retriever_applies_required_marker_hard_constraint() -> None:
    amp = plasmid("curated:amp", markers=["AmpR"], use_cases=["bacterial_cloning"])
    puro = plasmid("curated:puro", markers=["PuroR"], use_cases=["mammalian expression"])
    store = InMemoryVectorStore(model_name="static-test-embedder", dimension=3)
    store.upsert(
        [
            EmbeddingRecord("curated:amp", "amp", [1.0, 0.0, 0.0], metadata(vector_profile="bacterial_cloning_vector", markers=["AmpR"])),
            EmbeddingRecord("curated:puro", "puro", [0.9, 0.1, 0.0], metadata(vector_profile="mammalian_expression_vector", markers=["puromycin resistance"])),
        ]
    )
    retriever = HybridRetriever(vector_index=store, embedder=StaticEmbedder(), repository=FakeRepository([amp, puro]))

    results = retriever.retrieve(DesignSpec(organism="Homo sapiens", markers=["puromycin"]), k=5)

    assert [result.plasmid.id for result in results] == ["curated:puro"]
    assert "markers" in results[0].matched_fields


def test_marker_alias_matching_handles_bla_and_neor_kanr() -> None:
    amp = plasmid("curated:amp", markers=["bla"], use_cases=["bacterial_cloning"])
    kan = plasmid("curated:kan", markers=["NeoR/KanR"], use_cases=["bacterial_cloning"])

    assert passes_structured_filters(
        DesignSpec(organism="Escherichia coli", vector_type="bacterial_cloning_vector", markers=["ampicillin"]),
        amp,
        metadata(vector_profile="bacterial_cloning_vector", markers=["bla"]),
    )
    assert passes_structured_filters(
        DesignSpec(organism="Escherichia coli", vector_type="bacterial_cloning_vector", markers=["kanamycin"]),
        kan,
        metadata(vector_profile="bacterial_cloning_vector", markers=["NeoR/KanR"]),
    )


def test_vector_type_and_organism_filters_use_profiles_and_host_buckets() -> None:
    mammalian = plasmid("curated:pegfp", organism="Cloning vector pEGFP-N1", use_cases=["fluorescent reporting"])
    bacterial = plasmid("curated:puc", organism="synthetic construct", use_cases=["bacterial_cloning"])

    mammalian_meta = metadata(vector_profile="mammalian_reporter_vector", payloads=["EGFP"], use_cases=["fluorescent reporting"])
    bacterial_meta = metadata(vector_profile="bacterial_cloning_vector", markers=["AmpR"], use_cases=["bacterial cloning"])

    assert passes_structured_filters(
        DesignSpec(organism="Homo sapiens", vector_type="mammalian_reporter_vector"),
        mammalian,
        mammalian_meta,
    )
    assert not passes_structured_filters(
        DesignSpec(organism="Homo sapiens", vector_type="mammalian_reporter_vector"),
        bacterial,
        bacterial_meta,
    )


def test_general_shuttle_vector_without_host_bucket_passes_bacterial_filter_when_not_conflicting() -> None:
    candidate = plasmid(
        "genbank:AF216802.1",
        name="pDL278",
        organism="synthetic construct",
        markers=["SpecR"],
        use_cases=["shuttle vector"],
    )

    assert passes_structured_filters(
        DesignSpec(organism="Escherichia coli", vector_type="general_shuttle_vector", markers=["spectinomycin"]),
        candidate,
        metadata(vector_profile="general_shuttle_vector", markers=["SpecR"]),
    )


def test_general_shuttle_vector_without_host_bucket_still_rejects_conflicting_host_evidence() -> None:
    candidate = plasmid(
        "curated:conflict",
        organism="Homo sapiens",
        use_cases=["shuttle vector", "mammalian expression"],
    )

    assert not passes_structured_filters(
        DesignSpec(organism="Escherichia coli", vector_type="general_shuttle_vector"),
        candidate,
        metadata(vector_profile="general_shuttle_vector", use_cases=["mammalian expression"]),
    )


def test_matched_fields_reports_explainable_matches() -> None:
    item = plasmid(
        "curated:pegfp",
        markers=["neomycin phosphotransferase"],
        promoters=["CMV immediate-early enhancer/promoter"],
        use_cases=["fluorescent reporting"],
    )
    spec = DesignSpec(
        organism="Homo sapiens",
        vector_type="mammalian_reporter_vector",
        genes=["EGFP"],
        promoter_type="CMV",
        markers=["neomycin/G418"],
        application="fluorescent reporting",
    )

    fields = matched_fields(
        spec,
        item,
        metadata(
            vector_profile="mammalian_reporter_vector",
            markers=["neomycin phosphotransferase"],
            promoters=["CMV immediate-early enhancer/promoter"],
            payloads=["EGFP"],
            use_cases=["fluorescent reporting"],
        ),
    )

    assert fields == ["semantic", "vector_type", "organism", "markers", "promoters", "genes", "application"]


def test_hybrid_retriever_overfetches_and_uses_document_version_filter() -> None:
    item = plasmid("curated:puc", use_cases=["bacterial_cloning"])
    index = RecordingVectorIndex(
        [VectorMatch(plasmid_id="curated:puc", score=0.9, metadata=metadata(vector_profile="bacterial_cloning_vector"), document_sha256="sha")]
    )
    embedder = StaticEmbedder()
    retriever = HybridRetriever(
        vector_index=index,
        embedder=embedder,
        repository=FakeRepository([item]),
        candidate_multiplier=3,
        min_candidate_limit=10,
    )

    results = retriever.retrieve(DesignSpec(organism="Escherichia coli", vector_type="bacterial_cloning_vector"), k=2)

    assert [result.plasmid.id for result in results] == ["curated:puc"]
    assert index.calls[0]["limit"] == 10
    assert index.calls[0]["metadata_filter"] == {"document_version": DOCUMENT_VERSION}
    assert "Escherichia coli" in embedder.texts[0]


def test_retriever_returns_empty_when_parser_requested_clarification() -> None:
    index = RecordingVectorIndex([])
    retriever = HybridRetriever(vector_index=index, embedder=StaticEmbedder(), repository=FakeRepository([]))

    results = retriever.retrieve(
        DesignSpec(
            organism="unknown",
            clarification_needed=True,
            clarification_question="Which organism?",
        )
    )

    assert results == []
    assert index.calls == []


def test_retriever_rejects_invalid_k() -> None:
    retriever = HybridRetriever(vector_index=RecordingVectorIndex([]), embedder=StaticEmbedder(), repository=FakeRepository([]))

    with pytest.raises(ValueError, match="k must be positive"):
        retriever.retrieve(DesignSpec(organism="Escherichia coli"), k=0)


def test_compose_design_query_document_preserves_identity_and_feature_constraints() -> None:
    spec = DesignSpec(
        organism="Aeromonas salmonicida",
        markers=["tetracycline"],
        constraints=["pRAS1_2402_89", "sul1", "dfrA16"],
    )

    text = compose_design_query_document(spec)

    assert "Aeromonas salmonicida" in text
    assert "tetracycline" in text
    assert "pRAS1_2402_89, sul1, dfrA16" in text
