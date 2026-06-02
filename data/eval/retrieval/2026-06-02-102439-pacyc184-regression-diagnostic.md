# pACYC184 Retrieval Regression Diagnostic

- Query: `Recommend a low-copy bacterial cloning plasmid with chloramphenicol resistance.`
- Branch: `phase0-retrieval-robustness`
- Scope: read-only retrieval audit; no API or worker code inspected or modified.

## Retrieval Trace

Intent parser output from `FakeIntentParser` / heuristic parser:

```json
{
  "organism": "Escherichia coli",
  "cell_line": null,
  "vector_type": "bacterial_cloning_vector",
  "genes": [],
  "tags": [],
  "promoter_type": null,
  "inducer": null,
  "markers": ["chloramphenicol"],
  "source": null,
  "publication_doi": null,
  "application": "cloning",
  "cloning_method": null,
  "constraints": ["low-copy"],
  "clarification_needed": false,
  "clarification_question": null
}
```

Composed query document:

```text
Plasmid design retrieval request. Target organism: Escherichia coli. Vector type: bacterial cloning vector. Selectable markers: chloramphenicol. Application: cloning. Specific constraints and identity cues: low-copy.
```

Exact-name lane:

- No exact-name matches. The query is descriptive and does not contain `pACYC184` or another safe record alias.

Structured filter behavior:

- Hard filters require compatible vector family, compatible organism bucket, and chloramphenicol marker evidence.
- `low-copy` is parsed into `constraints`, but `passes_structured_filters` does not apply constraints as hard filters or boosts.
- `source` is `null`, so no curated-source filter applies.
- Curated source status is not used as a boost in the current retriever.

## Semantic Candidates Before Filters

Top semantic candidates from the current pgvector index, before structured filters:

| Semantic Rank | ID | Name | Score | Source | Profile | Filter Result |
|---:|---|---|---:|---|---|---|
| 1 | `curated:pUC19` | pUC19c | 0.789487 | curated | bacterial_cloning_vector | rejected: no chloramphenicol marker |
| 2 | `curated:pUC18` | pUC18 | 0.768031 | curated | bacterial_cloning_vector | rejected: no chloramphenicol marker |
| 3 | `genbank:AY428809.1` | Cloning vector pSUP202, complete sequence | 0.765673 | genbank | bacterial_cloning_vector | pass |
| 4 | `genbank:U80929.2` | Cloning vector pBACe3.6, complete sequence | 0.753895 | genbank | bacterial_cloning_vector | pass |
| 5 | `genbank:U19585.1` | Cloning vector pPROEX-1, complete sequence | 0.748347 | genbank | bacterial_expression_vector | rejected |
| 6 | `genbank:M37847.1` | Bacterial cloning vector pMMB206, complete genome | 0.746176 | genbank | bacterial_cloning_vector | pass |
| 7 | `genbank:U72488.1` | Cloning vector pRNA8, complete sequence | 0.745208 | genbank | bacterial_cloning_vector | pass |
| 8 | `curated:pBR322` | pBR322 | 0.744093 | curated | bacterial_cloning_vector | rejected: no chloramphenicol marker |
| 9 | `genbank:AF310245.1` | Cloning vector pGEM58ZNf(-), complete sequence | 0.740962 | genbank | bacterial_cloning_vector | rejected |
| 10 | `genbank:U36454.1` | Expression vector pCALn, complete sequence | 0.740322 | genbank | bacterial_cloning_vector | rejected |
| 11 | `genbank:AF133437.1` | Cloning vector pCYPAC6, complete sequence | 0.738727 | genbank | bacterial_cloning_vector | rejected |
| 12 | `genbank:U26464.1` | Cloning vector pZC320, complete sequence | 0.734798 | genbank | unknown | rejected |
| 13 | `genbank:AF222336.1` | Cloning vector pTacSfi, complete sequence | 0.731513 | genbank | bacterial_cloning_vector | rejected |
| 14 | `genbank:AF087042.1` | Cloning vector pCALnFLAG, complete sequence | 0.731463 | genbank | bacterial_expression_vector | rejected |
| 15 | `genbank:L09130.1` | Cloning vector pUC13, complete sequence | 0.730121 | genbank | bacterial_cloning_vector | rejected |
| 16 | `genbank:AY219685.1` | Expression vector pXC99E, complete sequence | 0.724490 | genbank | bacterial_cloning_vector | pass |
| 17 | `genbank:U24178.1` | Cloning vector pKMZB containing zero-background linker, complete sequence | 0.724103 | genbank | bacterial_cloning_vector | rejected |
| 18 | `genbank:AF519766.1` | Cloning vector pMAK705, complete sequence | 0.720818 | genbank | unknown | pass |
| 19 | `curated:pACYC184` | pACYC184 | 0.720336 | curated | unknown | pass |
| 20 | `genbank:U47626.2` | Cloning vector PinPoint<TM> Xa-1, complete sequence | 0.718748 | genbank | bacterial_cloning_vector | rejected |

## Final Filtered Ranking

Final surviving records after structured filters:

| Final Rank | ID | Name | Score | Source | Matched Fields |
|---:|---|---|---:|---|---|
| 1 | `genbank:AY428809.1` | Cloning vector pSUP202, complete sequence | 0.765673 | genbank | semantic, vector_type, organism, markers, application |
| 2 | `genbank:U80929.2` | Cloning vector pBACe3.6, complete sequence | 0.753895 | genbank | semantic, vector_type, organism, markers, application |
| 3 | `genbank:M37847.1` | Bacterial cloning vector pMMB206, complete genome | 0.746176 | genbank | semantic, vector_type, organism, markers, application |
| 4 | `genbank:U72488.1` | Cloning vector pRNA8, complete sequence | 0.745208 | genbank | semantic, vector_type, organism, markers, application |
| 5 | `genbank:AY219685.1` | Expression vector pXC99E, complete sequence | 0.724490 | genbank | semantic, vector_type, organism, markers |
| 6 | `genbank:AF519766.1` | Cloning vector pMAK705, complete sequence | 0.720818 | genbank | semantic, vector_type, organism, markers, application |
| 7 | `curated:pACYC184` | pACYC184 | 0.720336 | curated | semantic, vector_type, organism, markers, application |

## Local Row Verification

Read-only local DB inspection checked `plasmids` and `plasmid_embeddings` rows for the filtered candidates.

Key self-consistency findings:

- `curated:pACYC184` has the decisive public/curated metadata: source `curated`, markers `chloramphenicol resistance gene` and `tetracycline resistance gene`, use case `Low-copy p15A-origin vector with chloramphenicol and tetracycline resistance.`, and origin candidate `p15A origin of replication`.
- `curated:pACYC184` embedding metadata has `vector_profile: unknown` and `annotation_complete: false`; the composed document starts with `Unclassified plasmid pACYC184.`
- Top GenBank competitors carry chloramphenicol marker evidence and mostly `bacterial_cloning_vector` profiles. Their composed documents start with strong title/profile text such as `Bacterial cloning vector Cloning vector pSUP202...`.
- Several top GenBank competitors carry `pMB1/pUC origin`, not p15A, but the current retrieval filters/ranking do not interpret `low-copy` or p15A origin as constraints.

Representative composed documents:

```text
curated:pACYC184
Unclassified plasmid pACYC184. Source description: Low-copy p15A-origin vector with chloramphenicol and tetracycline resistance.. Organism annotation: synthetic construct. Selectable markers: chloramphenicol resistance gene and tetracycline resistance gene. Replication origins: p15A origin of replication. Used for: bacterial cloning, Cloning vector pACYC184, chloramphenicol resistance, cloning vector, and tetracycline resistance. 4245 bp circular plasmid. Source: curated.
```

```text
genbank:AY428809.1
Bacterial cloning vector Cloning vector pSUP202, complete sequence. Organism annotation: Cloning vector pSUP202. Payloads: rop. Selectable markers: tet, bla, ampicillin resistance protein, and cat. Replication origins: pMB1/pUC origin. 7830 bp circular plasmid. Source: genbank.
```

## Cause Evaluation

### (a) Document Composer Underweighting Curated-Seed Status

Partly true, but not the main wording defect by itself.

Evidence:

- The pACYC184 document ends with `Source: curated`, but does not otherwise foreground curated/canonical status.
- A test embedding of a more explicit curated sentence scored higher than the stored document.
- Stored pACYC184 document similarity: `0.720336`.
- Reworded as `Bacterial cloning vector pACYC184...`: `0.746582`.
- Reworded as `Curated bacterial cloning vector pACYC184. Low-copy p15A-origin...`: `0.769324`.

Diagnosis:

- Composer/source wording can help, but the larger defect is that pACYC184 is composed as `Unclassified plasmid` despite its curated bacterial-cloning use case.

### (b) Structured Filter Not Applying Curated-Source/Canonical-Vector Boost

True.

Evidence:

- `spec.source` is `null`, so source is not a hard filter.
- The retriever scores semantic matches directly after hard filters. There is no source-aware or curated-canonical post-filter boost.
- A tiny curated boost of about `+0.0042` would move pACYC184 from rank 7 to rank 5 for this query, because it only needs to pass `genbank:AY219685.1` (`0.724490`) and `genbank:AF519766.1` (`0.720818`) to restore top-5. A boost of about `+0.0454` would be needed for top-1 against `genbank:AY428809.1`.

Diagnosis:

- A small curated-source boost is enough to recover the reported top-5 regression, but it would not make pACYC184 the top answer unless the boost is too large to be generally safe.

### (c) Semantic Ranking Treating Multiple GenBank Chloramphenicol Records As Too Similar

True.

Evidence:

- Six filtered GenBank chloramphenicol records survive ahead of pACYC184.
- The top GenBank records have strong overlapping terms: `Bacterial cloning vector`, `Cloning vector`, `Selectable markers`, and `cat`/`chloramphenicol acetyl transferase`.
- Current scoring has no secondary preference for p15A/low-copy when the user explicitly says `low-copy`.

Diagnosis:

- The expanded corpus introduced legitimate near-neighbors with high semantic overlap, diluting pACYC184's uniqueness. This is expected behavior for pure semantic ranking without copy-number/origin-aware scoring.

### (d) Gold-Set Labeling Issue Where Multiple Records Are Legitimately Correct

Partly true.

Evidence:

- The top GenBank records are legitimate chloramphenicol-marked cloning/vector records according to local ingested metadata.
- However, the query specifically says `low-copy`. The local evidence inspected here shows pACYC184 has explicit `Low-copy p15A-origin` evidence, while several higher-ranked GenBank candidates show pMB1/pUC origins or no low-copy signal.

Diagnosis:

- If the gold case is intended to test only chloramphenicol bacterial cloning retrieval, multiple records are legitimately acceptable.
- If the gold case is intended to test low-copy/canonical pACYC184 retrieval, the single-target label is defensible and the retriever is missing copy-number/origin-aware preference.

## Lane Diagnosis

- Intent lane: mostly correct. It extracts organism, bacterial cloning vector, chloramphenicol marker, cloning application, and `low-copy` as a constraint.
- Query composer lane: acceptable for the request, but constraints are only emitted as free text and later ignored structurally.
- Exact-name lane: correctly not engaged.
- Structured filter lane: broad by design; it filters on vector, organism, marker, source, DOI only. It does not filter or boost `low-copy`, p15A origin, curated source, or canonical vector status.
- Semantic lane: primary regression source. Expanded GenBank chloramphenicol vectors are close semantic matches and outrank the stored pACYC184 document.
- Corpus/document lane: pACYC184 is disadvantaged because embedding metadata has `vector_profile: unknown`, causing `Unclassified plasmid pACYC184` despite curated bacterial-cloning evidence.

## Recommended Minimal Fix

Preferred minimal fix:

- Fix curated pACYC184's document/profile path so curated `bacterial_cloning` use case yields `bacterial_cloning_vector` in composed metadata/document, or update the curated annotation so the embedder emits `Bacterial cloning vector pACYC184` instead of `Unclassified plasmid pACYC184`.

Why this is preferred:

- It does not alter retrieval algorithm structure.
- The local embedding test suggests this alone raises pACYC184 similarity from `0.720336` to about `0.746582`, enough to move it around rank 3 among final filtered results.
- A more explicit curated/canonical wording raised similarity to about `0.769324`, enough to rank first in this diagnostic, but that is a stronger composer policy change.

Secondary minimal fix:

- Add a small post-filter curated-source boost only for curated records that already satisfy all structured filters. A boost around `+0.005` restores top-5 for this case; do not use a large boost unless the policy explicitly says canonical curated seeds should outrank similar GenBank records.

If stronger correctness is required:

- Add copy-number/origin-aware handling for constraints such as `low-copy`, `p15A`, `pMB1`, and `pUC`. This is a structural retrieval improvement because constraints currently are not interpreted beyond query-document text.

Gold-set recommendation:

- Keep `pACYC184` as the sole acceptable target if this case is intended to validate low-copy p15A/canonical-vector preference.
- Broaden acceptable IDs only if the query is reinterpreted as a general chloramphenicol bacterial cloning-vector query rather than a low-copy-specific query.
