# Expanded Phase 1 Retrieval Gate Failure Analysis

## Scope

This is a read-only analysis of the expanded Phase 1 retrieval evaluation in
`data/eval/retrieval/2026-05-31-215648-retrieval-baseline.json`. It focuses on
the two top-5 misses and the meaningful non-rank-1 outcomes.

Inspected inputs:

- `data/eval/retrieval/2026-05-31-215648-retrieval-baseline.json`
- `data/eval/retrieval/2026-05-31-215648-retrieval-baseline.md`
- `data/eval/retrieval/2026-05-31-gold-expansion-rationale.md`
- `data/eval/retrieval_gold.jsonl`
- `packages/retrieval/intent_parser.py`
- `packages/retrieval/retriever.py`
- `packages/retrieval/document_composer.py`
- `packages/retrieval/vector_store.py`
- current local Postgres `plasmids` and `plasmid_embeddings` rows, queried
  read-only at `localhost:55432`

Diagnostic probes loaded the existing cached embedding model and queried the
existing pgvector rows without writing database state. No production code,
tests, gold labels, or database rows were modified.

## Executive Summary

The expanded baseline scores 20 retrieval queries and one clarification query:

| Metric | Result |
| --- | ---: |
| Top-1 hit rate | `0.650` |
| Top-5 hit rate | `0.900` |
| MRR | `0.743` |
| Clarification pass rate | `1.000` |

The top-5 gate is numerically above the `0.800` threshold, but a bounded
mid-tier `FIX-1` pass is warranted before treating retrieval quality as
settled.

The two misses have different root causes:

1. Query 16, pDL278, is a structured-filter miss. Intent parsing is correct,
   the target is semantic rank `7`, and spectinomycin matching succeeds. The
   organism filter rejects a `general_shuttle_vector` row whose indexed
   metadata has no explicit bacterial-host bucket. This confirms the gold
   expansion rationale observation that structured host evidence is too
   strict for pDL278.
2. Query 20, Aeromonas pRAS1_2402_89, is primarily an IntentParser/query
   composition miss followed by a semantic-ranking miss. The original request
   is reduced to `Escherichia coli` plus `tetracycline`; the Aeromonas species,
   plasmid name, `sul1`, and `dfrA16` are absent from the composed query. The
   target falls to raw semantic rank `82`, outside the normal 50-candidate
   window. Embedding the original request directly moves the verified target
   to rank `1`, so this is not a corpus gap.

The non-rank-1 cases show a recurring pattern: the composed query document
retains broad profile terms while discarding the differentiating wording.
This affects pBluescript, pSB3, and pFR-Luc. pACYC184 is a narrower semantic
weighting issue. pBR322 is partly expected ambiguity because pSUP202 satisfies
the represented biological criteria.

## Retrieval Mechanics Relevant To The Failures

`HybridRetriever.retrieve()` embeds a normalized query document, overfetches
at least 50 semantic candidates, then applies hard vector-type, organism, and
marker filters. It does not embed the original user wording.

`compose_design_query_document()` can only emit fields retained in
`DesignSpec`. It has no target-plasmid-name field and no general field for
specific origin, MCS, ARS, or unsupported marker requirements.

`_organism_matches()` treats a generic `shuttle` vector family as a populated
family set. When the candidate has no host bucket, it requires the requested
bucket itself to appear in that family set. For pDL278 this becomes
`"bacterial" in {"shuttle"}`, which is false even though there is no
conflicting host evidence.

## Indexed Metadata Audit

All evaluated targets below exist in both `plasmids` and
`plasmid_embeddings`. There is no target-row corpus gap.

| Target | Indexed profile | Document observations |
| --- | --- | --- |
| `genbank:AF216802.1` / pDL278 | `general_shuttle_vector` | Document contains pDL278 name, spectinomycin adenyltransferase, pUC19 MCS, lac promoter region, and pMB1/pUC origin. It has no explicit bacterial host annotation. |
| `genbank:PZ138287.1` / pRAS1_2402_89 | `unknown` | Document contains Aeromonas name, `tetA`, `tetR`, `sul1`, and `dfrA16`. It also emits 42 payload candidates before its marker clause, versus 0-2 payloads for the other audited rows. |
| `genbank:AF058756.1` / pFR-Luc | `mammalian_reporter_vector` | Document contains pFR-Luc name, luciferase, AmpR, MCS candidate, and SV40 late polyA. |
| `genbank:PV135004.1` / pSB3 | `yeast_shuttle_vector` | Document contains Zygosaccharomyces rouxii pSB3 name and an ARS region. |
| `curated:pACYC184` | `unknown` | The profile is unknown, but bacterial-cloning use-case text allows the vector filter to match. The document explicitly contains low-copy p15A and chloramphenicol text. |
| `curated:pBR322` | `bacterial_cloning_vector` | Document contains pMB1-derived replication text, bla/AmpR, and tetracycline text. |
| curated pBluescript SK variants | `bacterial_cloning_vector` | Documents contain phagemid description, f1 origin, MCS candidate, T3 promoter, lac promoter region, pMB1/pUC origin, and AmpR. |

The pRAS1 payload density is a composer weighting concern, but it is not the
primary demonstrated failure. The primary defect is loss of user specificity
before embedding. Payload capping or field weighting should be evaluated as a
bounded follow-up experiment, not assumed to be sufficient on its own.

## Misses

### Query 16: pDL278

Query:

`E. coli SpecR shuttle vector.`

Parsed intent and composed query are correct:

```text
organism = Escherichia coli
vector_type = general_shuttle_vector
markers = [spectinomycin]

Plasmid design retrieval request. Target organism: Escherichia coli.
Vector type: general shuttle vector. Selectable markers: spectinomycin.
```

Read-only probe result:

| Check | Result |
| --- | --- |
| Raw semantic target rank | `7` |
| Vector filter | pass |
| Marker filter | pass |
| Organism filter | fail |
| Final accepted rank | none |

Classification: **structured-filter miss**.

Bounded `FIX-1` recommendation: relax only the missing-host branch for generic
`general_shuttle_vector` candidates. A candidate with family `shuttle`, no
candidate host bucket, and no conflicting host evidence should not be rejected
solely because the requested bacterial bucket is absent. Preserve rejection
when explicit conflicting mammalian, yeast, or plant evidence exists. Return a
caveat that host support is not explicit rather than claiming validated host
compatibility.

Biology-policy flag: retrieval permissiveness for missing host metadata is a
product-policy decision. The bounded change should allow inspection and
comparison retrieval; it must not assert experimentally validated host range.

### Query 20: Aeromonas pRAS1_2402_89

Query:

`For a bacterial resistance-plasmid comparison, retrieve the Aeromonas
salmonicida pRAS1_2402_89 plasmid carrying tetracycline resistance, sul1, and
dfrA16.`

Current parsed intent:

```text
organism = Escherichia coli
vector_type = none
markers = [tetracycline]

Plasmid design retrieval request. Target organism: Escherichia coli.
Selectable markers: tetracycline.
```

The parser maps generic `bacterial` wording to `Escherichia coli` and drops the
species, exact plasmid name, `sul1`, and `dfrA16`. The target still passes the
current structured filters if all 82 rows are overfetched, but its raw semantic
rank is `82`, so it is absent from the normal 50-candidate set.

Read-only ranking probes:

| Query document variant | pRAS1 raw rank | Score |
| --- | ---: | ---: |
| Current composed query | `82` | `0.3165` |
| Original user wording only | `1` | `0.7356` |
| Rich structured text with name, Aeromonas, tetracycline, `sul1`, `dfrA16` | `1` | `0.7937` |
| Current composed query plus original wording | `11` | `0.6409` |

Classification: **IntentParser miss** and downstream **semantic-ranking miss**.
This is not a corpus gap and not primarily a structured-filter miss.

Bounded `FIX-1` recommendations:

1. Add controlled terms for `Aeromonas salmonicida`, `sul1`, and `dfrA16` so
   this calibrated comparison query does not collapse to E. coli plus
   tetracycline.
2. Add a comparison-retrieval few-shot example that preserves proper species,
   exact plasmid identifiers, and unsupported differentiators as constraints
   instead of dropping them.
3. Evaluate a composer template adjustment that front-loads identity,
   organism, and markers and caps or downweights long natural-plasmid payload
   lists. The pRAS1 document has 42 payload candidates and eight marker
   candidate entries.

Architecture flag: controlled-vocabulary additions are a bounded calibration
fix, not a general solution for arbitrary natural-plasmid names, organisms,
and resistance genes. Reliable open-ended named retrieval likely needs a
target-name field or lexical/exact-match retrieval path. Increasing vector
overfetch alone is not an appropriate fix for a target at semantic rank 82.

## Meaningful Non-Rank-1 Outcomes

### Query 6: pACYC184 At Rank 2

Target: `curated:pACYC184`

The target is raw semantic rank `5` and accepted rank `2`. pSUP202 ranks first
because it matches bacterial cloning and chloramphenicol, while the current
semantic weighting does not make the explicit `low-copy` constraint decisive.
pACYC184's indexed document does contain `Low-copy p15A-origin`.

Classification: **semantic-ranking miss** with residual **expected ambiguity**.

Bounded recommendation: increase composer weighting for explicit constraints
such as `low-copy`; do not add a hard copy-number filter until corpus metadata
has reviewed, comparable copy-number evidence. Determining whether pSUP202 is
biologically unsuitable requires biology judgment rather than a retrieval
guess.

### Query 8: pBR322 At Rank 2

Target: `curated:pBR322`

pSUP202 ranks first and pBR322 second after filtering. Both rows match
ampicillin, tetracycline, bacterial cloning, and a pMB1-family origin. The
query word `curated` and the pBR322-specific replication wording are not
represented in the composed query.

Classification: primarily **expected ambiguity**. It becomes a conditional
**gold-set bug** if the intended task is biological compatibility rather than
provenance-constrained retrieval.

Recommendation: do not force a semantic tie-break toward pBR322. Human review
should decide whether `curated` is a real provenance requirement. If it is,
modeling source/provenance as an intent field and structured filter is an
architecture change outside bounded retrieval tuning.

### Query 9: pBluescript At Rank 5

Targets: curated pBluescript II SK variants

The current parser reduces the request to E. coli, bacterial cloning, T7, and
cloning application. It drops `phagemid`, `f1 origin`, `lacZ alpha MCS`, and
`T3`. The minus variant survives at accepted rank `5`; the plus variant is
accepted rank `7`.

Read-only probe:

| Query document variant | pBluescript SK(+) raw rank |
| --- | ---: |
| Current composed query | `8` |
| Original user wording only | `1` |
| Current composed query plus original wording | `2` |

Classification: **IntentParser miss** and downstream **semantic-ranking miss**.

Bounded recommendation: extend controlled-term/constraint preservation for
phagemid, f1 origin, lacZ alpha MCS, and secondary promoter-site requirements.
Add a phagemid few-shot example so an LLM parser retains differentiating
features as constraints when no dedicated field exists.

Architecture flag: a fully general origin/MCS requirement model would require
new structured intent fields. That is outside the bounded tuning pass.

### Query 18: pFR-Luc At Rank 3

Target: `genbank:AF058756.1`

The parsed query retains mammalian reporter, luciferase, AmpR, and reporter
assay but loses exact `pFR-Luc` identity and the upstream cloning-site
requirement. pGL3-Basic and pGL4.10[luc2] are valid semantic reporter neighbors
and rank above pFR-Luc.

Read-only probe:

| Query document variant | pFR-Luc raw rank |
| --- | ---: |
| Current composed query | `3` |
| Original user wording only | `2` |
| Current composed query plus original wording | `3` |

Classification: **IntentParser miss** for named identity plus **expected
ambiguity** under semantic retrieval.

Recommendation: do not force field weights to make pFR-Luc rank first. Exact
named-record retrieval is an architecture requirement, such as lexical or
exact-name matching before semantic ranking.

### Query 19: pSB3 At Rank 3

Target: `genbank:PV135004.1`

The parser maps the request to `Saccharomyces cerevisiae`,
`yeast_shuttle_vector`, and yeast transformation. It drops exact
`Zygosaccharomyces rouxii`, `pSB3`, and ARS wording. The generic pRS415 and
pRS416 yeast shuttle documents therefore rank above pSB3.

Read-only probe:

| Query document variant | pSB3 raw rank |
| --- | ---: |
| Current composed query | `4` |
| Original user wording only | `1` |

Classification: **IntentParser miss** and downstream **semantic-ranking miss**.

Bounded recommendation: add `Zygosaccharomyces rouxii` to controlled organism
terms and preserve ARS/name constraints in the comparison-retrieval few-shot.

Biology flag: keep the gold rationale's comparison-only wording. Do not infer
that this native pSB3 row is a Saccharomyces engineering backbone.

## Clarification Case

Query 21 correctly asks for clarification for an underspecified viral vector
request. No tuning is warranted from this result. The rationale document also
correctly avoids fabricating lentiviral, retroviral, AAV, or CRISPR targets in
the current corpus.

## Bounded FIX-1 Plan

The following pass stays within controlled vocabulary, structured-filter
strictness, composer template/weighting, and few-shot prompt tuning:

1. Relax generic-shuttle missing-host rejection with explicit conflict
   safeguards and regression tests centered on pDL278.
2. Add calibrated controlled terms for `Aeromonas salmonicida`,
   `Zygosaccharomyces rouxii`, `sul1`, and `dfrA16`.
3. Preserve phagemid-specific and comparison-specific differentiators as
   constraints where existing fields cannot represent them.
4. Add few-shot examples for a phagemid query and a named natural-plasmid
   comparison query. Note that prompt changes affect the LLM parser path only;
   the current deterministic baseline also needs controlled-vocabulary or
   heuristic-preservation coverage.
5. Evaluate composer weighting that emphasizes explicit constraints and
   identity/organism/marker clauses, while capping or downweighting long
   payload lists for dense natural plasmids.
6. Rerun the 21-query gate and inspect not only top-5 but pDL278 inclusion,
   pRAS1 candidate-window entry, and pBluescript/pSB3 rank movement.

## Out Of Scope For FIX-1

Do not silently implement these as tuning:

- a direct plasmid-name lookup path or hybrid lexical/vector retriever;
- new structured schema fields for target plasmid name, provenance, origin,
  ARS, MCS, or arbitrary natural-plasmid feature requirements;
- generalized named-entity extraction for arbitrary organisms and markers;
- biology decisions that declare pSUP202 unsuitable for low-copy use, assert
  validated pDL278 host range from missing metadata, or treat pSB3 as a
  Saccharomyces engineering vector.

These require architecture or biology review rather than ranking guesses.

## Conclusion

A mid-tier `FIX-1` pass is warranted. The highest-value bounded change is the
pDL278 missing-host structured-filter correction. The pRAS1 miss also merits
bounded vocabulary and composer experiments, but robust named natural-plasmid
retrieval should be tracked as an architecture requirement rather than hidden
inside ranking weights.
