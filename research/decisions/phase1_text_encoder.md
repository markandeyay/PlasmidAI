# Phase 1 Biomedical Text Encoder

**Status:** accepted for Phase 1 research
**Scope:** composed plasmid-document retrieval over natural-language plasmid summaries. This is not a DNA-sequence encoder decision.

## Decision

**Recommendation:** use [`NeuML/pubmedbert-base-embeddings`](https://huggingface.co/NeuML/pubmedbert-base-embeddings) pinned to revision [`b79526d6ef3645e0df4530322e266f24c829f5ef`](https://huggingface.co/NeuML/pubmedbert-base-embeddings/commit/b79526d6ef3645e0df4530322e266f24c829f5ef).

Established facts:

- The exact Hugging Face checkpoint is tagged `apache-2.0`, identifies Microsoft's PubMedBERT full-text checkpoint as its base, and is packaged for both Sentence Transformers and `transformers.AutoModel` loading.[^neuml-card]
- Its model card says it was fine-tuned with Sentence Transformers on PubMed title-abstract pairs and similar-title pairs, maps sentences and paragraphs to 768-dimensional vectors, and uses attention-mask-aware mean pooling with a 512-token maximum.[^neuml-card]
- Its configuration is a 12-layer BERT model with hidden size 768, and its repository publishes a 438 MB `model.safetensors` file plus a 438 MB `pytorch_model.bin` alternative.[^neuml-config][^neuml-tree]
- The card reports a 95.62 average Pearson correlation across its PubMed QA, PubMed subset, and PubMed summary evaluations versus 92.69 for `S-PubMedBert-MS-MARCO`; this is publisher-reported evidence, not an independent plasmid-retrieval benchmark.[^neuml-card]

Recommended integration contract:

- Load the pinned revision with `SentenceTransformer`, or use `AutoTokenizer` plus `AutoModel` when keeping dependencies minimal.
- Use attention-mask-aware mean pooling, then L2-normalize each vector. Store 768-dimensional vectors and compare them with cosine similarity, or inner product after normalization.
- Prefer the safetensors variant. Budget roughly 0.44 GB for one selected weight format and up to roughly 0.88 GB if both published formats are cached.
- Treat CPU latency and retrieval quality as acceptance-test items on the Phase 1 plasmid-summary corpus. The BERT-base-sized checkpoint is a practical local CPU development baseline, not a latency guarantee.

Why this checkpoint: Phase 1 needs one symmetric summary encoder. This checkpoint adds retrieval-oriented sentence training to a biomedical-language base while retaining a single BERT-base-sized local model. That is a closer fit than applying an arbitrary pooling rule to a masked-language-model checkpoint, and simpler than deploying separate query and article encoders.

## Fallback

If a third-party fine-tuned checkpoint cannot be approved, use Microsoft's official [`microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext`](https://huggingface.co/microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext). The official card states that this was previously named PubMedBERT, was pretrained from scratch on PubMed abstracts and PubMed Central full text, is MIT-licensed, and loads through Transformers.[^biomedbert-card] Its configuration is also a 12-layer BERT model with hidden size 768 and a 512-token maximum.[^biomedbert-config]

For fallback use, apply the same attention-mask-aware mean pooling and L2 normalization contract. This is a conservative interoperability fallback, not the preferred semantic-retrieval checkpoint: the official card presents a fill-mask model rather than a sentence-retrieval fine-tune.[^biomedbert-card]

## Candidate Comparison

| Candidate | Established facts | Phase 1 assessment |
| --- | --- | --- |
| `microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext` (formerly PubMedBERT) | Biomedical from-scratch pretraining; official exact checkpoint is MIT-licensed and Transformers-compatible.[^biomedbert-card] The primary paper reports gains from biomedical-domain pretraining from scratch over continual general-domain pretraining.[^pubmedbert-paper] | Best official fallback, but not packaged as a sentence-retrieval model. |
| `dmis-lab/biobert-base-cased-v1.2` | The HF checkpoint exposes Transformers fill-mask loading and a 436 MB PyTorch file.[^biobert-hf] The BioBERT paper describes biomedical-corpus pretraining for biomedical text-mining tasks, and the official code repository is Apache-2.0 licensed.[^biobert-paper][^biobert-repo] | Viable biomedical MLM baseline. Do not select without confirming the commercial-use terms for the exact HF weights: the HF checkpoint page does not state a weight license.[^biobert-hf] |
| `allenai/scibert_scivocab_uncased` | The HF card says SciBERT was trained on 1.14 million multi-domain scientific papers and 3.1 billion tokens, supports Transformers loading, and links the official Apache-2.0 repository.[^scibert-hf][^scibert-repo] The primary paper evaluates scientific NLP tasks across scientific domains.[^scibert-paper] | Broader scientific baseline, less targeted to biomedical summary retrieval, and not packaged as a sentence-retrieval model. |
| `NeuML/pubmedbert-base-embeddings` | Apache-2.0 exact checkpoint; PubMedBERT-based Sentence Transformers fine-tune; 768-dimensional mean-pooled summary embeddings; Transformers-compatible.[^neuml-card] | **Select.** Best fit for one symmetric Phase 1 encoder. |
| `pritamdeka/S-PubMedBert-MS-MARCO` | PubMedBERT-based Sentence Transformers model fine-tuned on MS MARCO; 768-dimensional mean-pooled embeddings; exact checkpoint is tagged `cc-by-nc-2.0`.[^spubmed-card] | Reject for commercial use because the exact checkpoint is non-commercial. |
| `ncbi/MedCPT-Query-Encoder` plus `ncbi/MedCPT-Article-Encoder` | NCBI's public-domain model cards describe separate short-query and article encoders trained from 255 million PubMed query-article pairs; the article card shows 768-dimensional CLS embeddings in the same space as query embeddings.[^medcpt-query][^medcpt-article] The official repository code is also public domain.[^medcpt-repo] | Strong follow-up benchmark if the service adds distinct query and document paths. Do not make it the Phase 1 default because it changes the service to an asymmetric two-checkpoint contract. |
| `cambridgeltl/SapBERT-from-PubMedBERT-fulltext` | Apache-2.0 exact checkpoint trained with UMLS; its card expects biomedical entity-name strings and uses last-layer CLS embeddings.[^sapbert-card] The primary paper targets biomedical entity representations and medical entity linking.[^sapbert-paper] | Keep for entity normalization experiments, not summary-document retrieval. |

## License And Runtime Notes

The selected exact weights are tagged Apache-2.0, the Microsoft base checkpoint is tagged MIT, and the recommended runtime libraries [`transformers`](https://github.com/huggingface/transformers/blob/main/LICENSE) and [`sentence-transformers`](https://github.com/huggingface/sentence-transformers/blob/main/LICENSE) are Apache-2.0 licensed.[^neuml-card][^biomedbert-card][^transformers-license][^sentence-transformers-license] This is a dependency-selection record, not legal advice; retain license notices in distribution review.

Hugging Face Hub uses a shared local cache. Its documented default is `~/.cache/huggingface/hub`; `HF_HUB_CACHE` overrides the hub directory directly and `HF_HOME` changes the parent Hugging Face home directory.[^hf-cache] The cache stores repository revisions using `refs`, content-addressed `blobs`, and `snapshots`; on Windows without symlink support it stores files directly in snapshots and may use more disk across revisions.[^hf-cache-guide]

Recommended local behavior:

1. Pin the revision above so dev, test, and production resolve the same files.
2. Keep the model cache outside the repository. Use the default cache or set `HF_HOME`/`HF_HUB_CACHE` before process start.
3. For offline verification after the first download, initialize with `local_files_only=True`. `SentenceTransformer` documents `revision`, `cache_folder`, and `local_files_only` constructor arguments.[^sentence-transformer-api]

## Sources

[^neuml-card]: NeuML, [`NeuML/pubmedbert-base-embeddings` model card](https://huggingface.co/NeuML/pubmedbert-base-embeddings/blob/main/README.md).
[^neuml-config]: NeuML, [`config.json`](https://huggingface.co/NeuML/pubmedbert-base-embeddings/blob/main/config.json).
[^neuml-tree]: NeuML, [`NeuML/pubmedbert-base-embeddings` file tree](https://huggingface.co/NeuML/pubmedbert-base-embeddings/tree/main).
[^biomedbert-card]: Microsoft, [`microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext` model card](https://huggingface.co/microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext).
[^biomedbert-config]: Microsoft, [`config.json`](https://huggingface.co/microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext/blob/main/config.json).
[^pubmedbert-paper]: Gu et al., ["Domain-Specific Language Model Pretraining for Biomedical Natural Language Processing"](https://doi.org/10.1145/3458754), ACM Transactions on Computing for Healthcare, 2021.
[^biobert-hf]: DMIS Lab, [`dmis-lab/biobert-base-cased-v1.2` file tree](https://huggingface.co/dmis-lab/biobert-base-cased-v1.2/tree/main).
[^biobert-paper]: Lee et al., ["BioBERT: a pre-trained biomedical language representation model for biomedical text mining"](https://doi.org/10.1093/bioinformatics/btz682), Bioinformatics, 2020.
[^biobert-repo]: DMIS Lab, [`dmis-lab/biobert`](https://github.com/dmis-lab/biobert) and its [Apache-2.0 license](https://github.com/dmis-lab/biobert/blob/master/LICENSE).
[^scibert-hf]: Allen Institute for AI, [`allenai/scibert_scivocab_uncased` model card](https://huggingface.co/allenai/scibert_scivocab_uncased).
[^scibert-repo]: Allen Institute for AI, [`allenai/scibert`](https://github.com/allenai/scibert) and its [Apache-2.0 license](https://github.com/allenai/scibert/blob/master/LICENSE).
[^scibert-paper]: Beltagy et al., ["SciBERT: A Pretrained Language Model for Scientific Text"](https://aclanthology.org/D19-1371/), EMNLP-IJCNLP 2019.
[^spubmed-card]: Deka, [`pritamdeka/S-PubMedBert-MS-MARCO` model card](https://huggingface.co/pritamdeka/S-PubMedBert-MS-MARCO).
[^medcpt-query]: NCBI, [`ncbi/MedCPT-Query-Encoder` model card](https://huggingface.co/ncbi/MedCPT-Query-Encoder).
[^medcpt-article]: NCBI, [`ncbi/MedCPT-Article-Encoder` model card](https://huggingface.co/ncbi/MedCPT-Article-Encoder).
[^medcpt-repo]: NCBI, [`ncbi/MedCPT`](https://github.com/ncbi/MedCPT) and its [public-domain notice](https://github.com/ncbi/MedCPT/blob/main/LICENSE).
[^sapbert-card]: Cambridge Language Technology Lab, [`cambridgeltl/SapBERT-from-PubMedBERT-fulltext` model card](https://huggingface.co/cambridgeltl/SapBERT-from-PubMedBERT-fulltext).
[^sapbert-paper]: Liu et al., ["Self-Alignment Pretraining for Biomedical Entity Representations"](https://aclanthology.org/2021.naacl-main.334/), NAACL 2021.
[^transformers-license]: Hugging Face, [`transformers` Apache-2.0 license](https://github.com/huggingface/transformers/blob/main/LICENSE).
[^sentence-transformers-license]: Hugging Face, [`sentence-transformers` Apache-2.0 license](https://github.com/huggingface/sentence-transformers/blob/main/LICENSE).
[^hf-cache]: Hugging Face, ["Hub Local Cache"](https://huggingface.co/docs/hub/local-cache).
[^hf-cache-guide]: Hugging Face, ["Understand caching"](https://huggingface.co/docs/huggingface_hub/guides/manage-cache).
[^sentence-transformer-api]: Hugging Face, [`SentenceTransformer` API](https://sbert.net/docs/package_reference/sentence_transformer/SentenceTransformer.html).
