# Phase 1 Embedding Baseline

Generated: 2026-05-31

## Encoder

- Model: `NeuML/pubmedbert-base-embeddings`
- Revision: `b79526d6ef3645e0df4530322e266f24c829f5ef`
- Vector dimension: `768`
- Pooling: attention-mask-aware mean pooling with L2 normalization
- Storage: Postgres `plasmid_embeddings` sidecar table with pgvector HNSW cosine index

## Corpus Run

The first real-model run processed the current local corpus after a deterministic fake smoke
test. It loaded annotations only from cached MinIO GenBank blobs and wrote derived embeddings
to pgvector.

| Metric | Value |
| --- | ---: |
| Total plasmids | 82 |
| Cached annotations parsed | 82 |
| Missing cache blobs | 0 |
| Parse failures | 0 |
| Real embeddings written | 82 |
| Stored rows for pinned model | 82 |
| Approximate elapsed time | 133 seconds |

The elapsed time includes the initial Hugging Face checkpoint download and local CPU inference.

## Idempotence And Offline Verification

A warm second pass inspected all 82 cached records and skipped every document before model
inference because the composed-document hashes were unchanged:

| Metric | Value |
| --- | ---: |
| Total plasmids inspected | 82 |
| Attempted embeddings | 0 |
| Rows updated | 0 |
| Rows skipped | 82 |
| Approximate elapsed time | 44 seconds |

A separate `--local-files-only --limit 1` run completed with one skipped record and zero
attempted embeddings, confirming that the pinned checkpoint is present in the local Hugging
Face cache and can initialize without network access.
