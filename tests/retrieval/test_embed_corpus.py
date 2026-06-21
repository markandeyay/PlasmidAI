from __future__ import annotations

from dataclasses import dataclass

from packages.core.schemas import Plasmid
from packages.retrieval.embed_corpus import embed_corpus
from packages.retrieval.embedder import FakeEmbedder
from packages.retrieval.vector_store import InMemoryVectorStore


@dataclass
class FakeRepository:
    plasmids: list[Plasmid]

    def list_plasmids(self, *, limit: int | None = None) -> list[Plasmid]:
        if limit is None:
            return list(self.plasmids)
        return list(self.plasmids[:limit])


class FakeObjectStore:
    def __init__(self, payloads: dict[str, str | None]) -> None:
        self.payloads = payloads

    def get_text(self, key: str) -> str | None:
        return self.payloads.get(key)


class RecordingFakeEmbedder:
    def __init__(self) -> None:
        self.delegate = FakeEmbedder()
        self.batch_sizes: list[int] = []

    @property
    def dim(self) -> int:
        return self.delegate.dim

    @property
    def model_name(self) -> str:
        return self.delegate.model_name

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.batch_sizes.append(len(texts))
        return self.delegate.embed(texts)


def plasmid(plasmid_id: str, raw_ref: str, *, use_cases: list[str] | None = None) -> Plasmid:
    return Plasmid(
        id=plasmid_id,
        source="curated" if plasmid_id.startswith("curated:") else "addgene",
        name=plasmid_id,
        sequence="ACGT" * 100,
        length=400,
        organism="synthetic construct",
        vector_type="plasmid",
        markers=["AmpR"],
        promoters=["lac promoter"],
        use_cases=use_cases or ["bacterial_cloning"],
        annotation_complete=False,
        raw_ref=raw_ref,
    )


def test_embed_corpus_parses_cached_genbank_and_skips_unchanged_records() -> None:
    genbank_blob = """LOCUS       PUC19                     240 bp    DNA     circular SYN 01-JAN-2000
DEFINITION  High-copy cloning vector with lac promoter and AmpR.
ACCESSION   TEST0001
VERSION     TEST0001.1
KEYWORDS    plasmid.
SOURCE      synthetic DNA construct
  ORGANISM  synthetic DNA construct
FEATURES             Location/Qualifiers
     promoter        1..20
                     /label=\"lac promoter region\"
     CDS             21..60
                     /gene=\"bla\"
     rep_origin      61..120
                     /label=\"pMB1/pUC origin\"
ORIGIN
        1 acgtacgtac gtacgtacgt acgtacgtac gtacgtacgt acgtacgtac gtacgtacgt
       61 acgtacgtac gtacgtacgt acgtacgtac gtacgtacgt acgtacgtac gtacgtacgt
      121 acgtacgtac gtacgtacgt acgtacgtac gtacgtacgt acgtacgtac gtacgtacgt
      181 acgtacgtac gtacgtacgt acgtacgtac gtacgtacgt acgtacgtac gtacgtacgt
//
"""
    repo = FakeRepository(
        [
            plasmid("curated:pUC19", "raw/curated/pUC19.gb", use_cases=["high-copy cloning vector", "bacterial_cloning"]),
            plasmid("addgene:1001", "raw/addgene/1001.json", use_cases=["reporter_fluorescent"]),
        ]
    )
    store = FakeObjectStore({"raw/curated/pUC19.gb": genbank_blob, "raw/addgene/1001.json": None})
    vector_index = InMemoryVectorStore(model_name="fake-hash-embedder-v1", dimension=768)
    embedder = RecordingFakeEmbedder()

    first = embed_corpus(repo, store, vector_index, embedder, batch_size=1)
    second = embed_corpus(repo, store, vector_index, embedder, batch_size=2)

    assert first.total_plasmids == 2
    assert first.annotated_from_cache == 1
    assert first.missing_cache == 0
    assert first.inserted == 2
    assert first.updated == 0
    assert first.skipped == 0

    assert second.inserted == 0
    assert second.updated == 0
    assert second.skipped == 2
    assert second.attempted_embeddings == 0
    assert embedder.batch_sizes == [1, 1, 0]

    row = vector_index.get_row("curated:pUC19")
    assert row is not None
    assert "ACGT" not in row["composed_document"]
    assert row["metadata"]["raw_ref"] == "raw/curated/pUC19.gb"
    assert row["metadata"]["candidates"]["origins"][0]["label"] == "pMB1/pUC origin"


def test_embed_corpus_records_parse_failures_and_continues() -> None:
    repo = FakeRepository([plasmid("curated:broken", "raw/curated/broken.gb")])
    store = FakeObjectStore({"raw/curated/broken.gb": "not a genbank record"})
    vector_index = InMemoryVectorStore(model_name="fake-hash-embedder-v1", dimension=768)

    report = embed_corpus(repo, store, vector_index, FakeEmbedder(), batch_size=1)

    assert report.parse_failures == 1
    assert report.inserted == 1
    assert report.errors[0]["id"] == "curated:broken"
