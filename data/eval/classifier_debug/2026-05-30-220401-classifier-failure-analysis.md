# Classifier Failure Analysis: pDL278 and pUCP26

Generated: 2026-05-30 22:04:01 America/New_York

## Scope

This is a read-only debugging report for the profile classifier and sequence parser. It traces the two flagged records from cached MinIO blobs, audits the implementation for related failure patterns, and recommends fix boundaries. No production code or tests were changed while producing this report.

Inputs inspected:

- `raw/genbank/AF216802.1.gb` (`pDL278`)
- `raw/genbank/U07168.1.gb` (`pUCP26`)
- `packages/data_pipeline/parse/classify.py`
- `packages/data_pipeline/parse/sequence_parser.py`
- `packages/data_pipeline/marker_terms.py`
- the current 82-record Postgres corpus and its cached raw blobs

## Executive Summary

Both failures are deterministic classifier bugs.

1. `pDL278` is classified as `lentiviral_or_retroviral_transfer_vector` because `FeatureContext.terms()` uses unbounded substring matching and finds `ltr` inside `spectinomycin adenyltransferase`. A single viral-term hit is sufficient to win the second classifier rule in the cascade. The same bug currently misclassifies at least five additional natural GenBank records containing `acetyltransferase` or `glucosyltransferase`.
2. `pUCP26` is classified as `bacterial_expression_vector` because Tier 2 adds an SP6 promoter and Tier 1 maps all non-marker CDS annotations to `GOI`. The bacterial-expression rule correctly recognizes SP6 as a weak sequencing-class signal, but its guard only rejects weak-only hits when no `GOI` exists. Generic CDS annotations for `rep` and `lacZ alpha` therefore bypass the guard. The expression rule precedes the cloning rule and wins.

The classifier needs token-boundary matching with explicit aliases, corroborated viral signals, and an explicit expression-cassette predicate that does not treat sequencing promoters or generic CDS annotations as expression evidence.

## Failure 1: pDL278

### Source Record

| Field | Value |
| --- | --- |
| Cache key | `raw/genbank/AF216802.1.gb` |
| Accession | `AF216802.1` |
| LOCUS | `AF216802`, 6733 bp, linear, synthetic |
| DEFINITION | `Shuttle vector pDL278, complete sequence.` |

Relevant GenBank source annotations:

| Source feature | Coordinates | Name |
| --- | --- | --- |
| `CDS` | `1681..2449 +` | `spectinomycin adenyltransferase` |
| `CDS` | `4638..4878 -` | `unknown protein` |
| `regulatory` | `5041..6183 -` | `rrnB T1T2 terminator` |
| `CDS` | `6182..6422 -` | `beta-galactosidase alpha peptide` |

Current parser output:

| Type | Coordinates | Confidence | Name | Tier |
| --- | --- | --- | --- | --- |
| `ORI` | `236..825 +` | `0.8273` | `pMB1/pUC origin` | Tier 2 reference match |
| `marker` | `1681..2449 +` | `0.95` | `spectinomycin adenyltransferase` | Tier 1 trusted annotation |
| `GOI` | `4638..4878 -` | `0.95` | `unknown protein` | Tier 1 generic CDS fallback |
| `terminator` | `5041..6183 -` | `0.95` | `terminator` | Tier 1 trusted annotation |
| `GOI` | `6182..6422 -` | `0.95` | `beta-galactosidase alpha peptide` | Tier 1 generic CDS fallback |
| `promoter` | `6190..6348 +` | `0.8272` | `lac promoter region` | Tier 2 reference match |
| `MCS` | `6348..6405 +` | `0.8275` | `pUC19 MCS` | Tier 2 reference match |

### Exact Classification Trace

`FeatureContext.text` contains:

```text
... pmb1/puc origin spectinomycin adenyltransferase unknown protein ...
```

`FeatureContext.terms("ltr", ...)` uses:

```python
term.lower() in self.text
```

The term `ltr` matches the highlighted substring:

```text
spectinomycin adeny[ltr]ansferase
```

Classifier cascade:

| Rule | Result | Signals | Why |
| --- | --- | --- | --- |
| `crispr_vector` | no match | none | No CRISPR term |
| `lentiviral_or_retroviral_transfer_vector` | **match** | `["ltr"]` | Raw substring match inside `adenyltransferase` |
| lower-priority rules | not reached by `classify()` | n/a | First-match cascade returns immediately |

Directly evaluating the lower-priority cloning rule shows that it would otherwise classify this record as `bacterial_cloning_vector` with signals `["puc", "pmb1"]`.

The false viral profile also makes completeness true:

```text
ORI + marker + (GOI or MCS) + has_viral_signal()
```

All operands are satisfied, but `has_viral_signal()` is satisfied only by the false `ltr` substring.

### Root Cause

The direct cause is unbounded textual matching in `FeatureContext.terms()` at `packages/data_pipeline/parse/classify.py:82-83`. The viral rule at `packages/data_pipeline/parse/classify.py:168-173` also accepts one signal with no corroboration and assigns confidence `0.82`.

## Failure 2: pUCP26

### Source Record

| Field | Value |
| --- | --- |
| Cache key | `raw/genbank/U07168.1.gb` |
| Accession | `U07168.1` |
| LOCUS | `U07168`, 4977 bp, circular, synthetic |
| DEFINITION | `Cloning vector pUCP26, Escherichia-Pseudomonas shuttle vector with tetracycline efflux protein (tet) and LacZ alpha peptide (lacZ alpha) genes, complete sequence.` |

Relevant GenBank source annotations:

| Source feature | Coordinates | Name |
| --- | --- | --- |
| `CDS` | `410..1244 +` | `replication protein` (`rep`) |
| `CDS` | `1240..1495 -` | `LacZ alpha peptide` |
| `misc_feature` | `1424..1481 +` | `polylinker` |
| `CDS` | `3302..4493 -` | `tetracycline efflux protein` (`tet`) |

Current parser output:

| Type | Coordinates | Confidence | Name | Tier |
| --- | --- | --- | --- | --- |
| `GOI` | `410..1244 +` | `0.95` | `rep` | Tier 1 generic CDS fallback |
| `GOI` | `1240..1495 -` | `0.95` | `lacZ alpha` | Tier 1 generic CDS fallback |
| `promoter` | `1270..1421 +` | `0.8253` | `lac promoter region` | Tier 2 reference match |
| `MCS` | `1424..1481 +` | `0.95` | `MCS` | Tier 1 trusted annotation |
| `ORI` | `1892..2481 +` | `0.8275` | `pMB1/pUC origin` | Tier 2 reference match |
| `marker` | `3302..4504 -` | `0.95` | `tet` | Tier 1 trusted annotation |
| `promoter` | `4947..4965 +` | `0.8275` | `SP6 promoter` | Tier 2 reference match |

### Exact Classification Trace

The bacterial-expression rule sees:

```text
signals = ["sp6"]
strong_expression_signals = []
```

The existing weak-signal guard is:

```python
if not strong_expression_signals and context.has("MCS") and not context.has("GOI"):
    return None
```

It does not reject `pUCP26` because Tier 1 converted `rep` and `lacZ alpha` CDS annotations into `GOI`, so `not context.has("GOI")` is false.

The following predicate is also satisfied:

```python
context.has_all("ORI", "marker", "promoter")
```

The rule returns:

```text
bacterial_expression_vector, confidence=0.86, signals=["sp6"]
```

The lower-priority cloning rule would otherwise return:

```text
bacterial_cloning_vector, confidence=0.84, signals=["puc", "pmb1", "lacz"]
```

### Root Causes

There are two coupled causes:

1. `packages/data_pipeline/parse/sequence_parser.py:125-126` maps every non-marker CDS to `GOI`, including backbone maintenance genes and screening fragments. A generic CDS is not evidence of an expression payload.
2. `packages/data_pipeline/parse/classify.py:202-228` includes `t7`, `t3`, and `sp6` as bacterial-expression signals. Although the code attempts to treat them as weak, it allows generic `GOI` annotations to promote a weak-only record into `bacterial_expression_vector`.

The product decision supplied after this failure is the correct classifier boundary: SP6, T7, and T3 alone are sequencing or in-vitro-transcription signals, not in-vivo bacterial expression evidence. A cloning shuttle should remain cloning-class unless explicit expression-cassette evidence is present.

## Corpus-Wide Boundary Audit

I parsed all 82 cached records and compared the classifier's raw substring hits against token-boundary matches. The scan found these current-corpus cases where a signal exists only as an unbounded substring.

### Harmful Current Misclassifications

| Record | Current profile | Group | False term | Actual containing text |
| --- | --- | --- | --- | --- |
| `genbank:AF216802.1` | `lentiviral_or_retroviral_transfer_vector` | viral | `ltr` | `adenyltransferase` |
| `genbank:CP190864.1` | `lentiviral_or_retroviral_transfer_vector` | viral | `ltr` | `n-acetyltransferase` |
| `genbank:CP190865.1` | `lentiviral_or_retroviral_transfer_vector` | viral | `ltr` | `n-acetyltransferase` |
| `genbank:CP190867.1` | `lentiviral_or_retroviral_transfer_vector` | viral | `ltr` | `n-acetyltransferase` |
| `genbank:CP190868.1` | `lentiviral_or_retroviral_transfer_vector` | viral | `ltr` | `n-acetyltransferase` |
| `genbank:CP191069.1` | `lentiviral_or_retroviral_transfer_vector` | viral | `ltr` | `alpha-glucosyltransferase` |
| `genbank:CP190857.1` | `yeast_shuttle_vector` | yeast | `ars` | `arsR/smtB family transcriptional regulator` |
| `genbank:CP191060.1` | `yeast_shuttle_vector` | yeast | `ars` | `arsR/smtB family transcriptional regulator` |
| `genbank:CP191063.1` | `yeast_shuttle_vector` | yeast | `ars` | `arsR/smtB family transcriptional regulator` |

### Legitimate Nested Aliases That Need Explicit Handling

Token-boundary hardening must preserve intentional aliases rather than treating every nested occurrence as invalid.

| Record | Group | Nested term | Intended larger alias |
| --- | --- | --- | --- |
| `curated:pEGFP-N1` | reporter | `gfp` | `egfp` |
| `curated:pRS415` | yeast | `ars` | `ARSH4` |
| `curated:pRS416` | yeast | `ars` | `ARSH4` |
| `genbank:AF519766.1` | cloning | `puc` | `pUC19` |

### Harmless Today but Fragile

| Record | Group | False term | Actual containing text | Why currently harmless |
| --- | --- | --- | --- | --- |
| `curated:pGL3-Basic` | mammalian expression | `tre` | `upstream` | Reporter rule has higher precedence and returns first |

This is still a classifier bug. A future non-reporter record containing `upstream` could receive a mammalian-expression signal.

## Static Audit of Systemic Weaknesses

### 1. All Classifier Term Groups Use Raw Substrings

`FeatureContext.terms()` is shared by every profile classifier. Every term below is currently matched with `term in self.text`, not token boundaries or structured aliases.

| Group | Terms with elevated risk |
| --- | --- |
| Viral | `ltr`, `psi`, `rre` |
| Yeast | `ars`, `cen` |
| Mammalian expression | `tre`, `cag` |
| Bacterial expression | `t7`, `t3`, `tac`, `trc`, `gst`, `mbp`, `rbs` |
| Cloning backbone | `puc`, `lacz` |
| Reporter | `gfp` requires deliberate nested-alias handling for `egfp` |

Recommendation: replace raw substring matching with a term matcher that uses alphanumeric token boundaries by default and an explicit alias allowlist for intended families such as `EGFP`, `ARSH4`, `pUC19`, and `lacZ alpha`.

### 2. Viral Classification Has No Corroboration Requirement

`lentiviral_or_retroviral_transfer_vector()` returns a profile for any one hit among `ltr`, `long terminal repeat`, `psi`, `packaging signal`, `rre`, `cppt`, `wpre`, or `mscv`.

Recommendation: require structured corroboration, such as:

- both 5-prime and 3-prime LTR annotations;
- LTR plus psi/packaging signal; or
- LTR plus a known transfer-vector element such as RRE, WPRE, or cPPT.

A lone `LTR` token should not classify a vector as viral, even after boundary hardening.

### 3. Generic CDS Features Become `GOI`

`normalize_feature_type()` returns `GOI` for every CDS that is not recognized as a marker. This causes replication proteins, recombinases, toxins, screening fragments, and hypothetical proteins to look like payload genes.

Recommendation: preserve generic CDS as a distinct neutral type or metadata attribute. Expression classification should require a known payload, a host-appropriate promoter driving an oriented CDS, or another explicit expression-cassette pattern. A generic `GOI` flag from CDS fallback must not serve as expression-purpose evidence.

### 4. Sequencing-Class Promoters Are Expression Signals

The bacterial-expression term list includes `t7`, `t3`, and `sp6`. These are valid sequence features but not sufficient evidence of an in-vivo bacterial expression vector.

Recommendation: encode two promoter sets:

- strong bacterial-expression evidence: `tac`, `trc`, `araBAD`/`pBAD`, and `T7` only with corroborating expression context such as `lacO`, RBS, affinity tag, or an oriented payload cassette;
- sequencing/in-vitro-transcription only unless corroborated: `SP6`, `T3`, and lone `T7`.

### 5. Parser Text Normalization Still Uses Substring Predicates

`sequence_parser.py` contains several text checks that should be normalized consistently:

| Location | Existing predicate | Risk |
| --- | --- | --- |
| `normalize_feature_type()` | `"pmb1" in text`, `"cole1" in text` | Unbounded named-origin aliases |
| `normalize_feature_type()` | `"promoter" in text` | Lower risk, but should use normalized tokens |
| `normalize_feature_type()` | `"terminator" in text`, `"polya" in text`, `"polyadenylation" in text` | `polya` alias needs explicit normalization |
| `normalize_feature_type()` | `"mcs" in text` | Short token should use boundaries |
| `ingest/genbank.py:620-623` | `"promoter" in text` | Same normalization consistency issue in metadata extraction |

The DNA reference matcher itself is not subject to this text-substring problem. Exact nucleotide lookup and alignment in `find_reference_match()` are expected behavior. `names_match()` is also exact after normalization.

### 6. Marker Matching Is Improved but Gene-Family Regex Remains Broad

`contains_marker_term()` now uses token-boundary patterns and fixes the earlier `cat`-inside-`replication` bug. However:

```python
(?:bla|tet)[a-z0-9-]*
```

accepts any token beginning with `bla` or `tet`, not only known resistance-gene aliases. That can admit unrelated words such as `blast...` or `tetra...`.

Recommendation: replace the open-ended family suffix with an explicit allowlist of validated marker-gene aliases or require gene/qualifier context.

### 7. First-Match Precedence Amplifies Weak Signals

The cascade intentionally returns the first matching profile. That is reasonable only when high-priority rules have strong admission criteria. Today, a weak false viral or yeast term prevents lower-priority cloning classification.

Recommendation: retain precedence, but make high-priority rules evidence-based and return a structured reasoning trace that names both matched aliases and source features.

## Test Gaps

The existing classifier tests cover curated happy paths and one unknown case. They do not cover:

- `ltr` inside `adenyltransferase`;
- `ars` inside `arsR/smtB`;
- `tre` inside `upstream`;
- SP6/T3/lone-T7 cloning vectors with generic CDS features;
- a valid lentiviral transfer vector requiring corroborated signals;
- legitimate nested aliases such as `EGFP`, `ARSH4`, and `pUC19` after token-boundary hardening;
- marker-family false positives for unrelated `bla...` and `tet...` words.

## Recommended Fix Sequence

1. Introduce one shared token-boundary matcher with explicit aliases and use it throughout `classify.py`.
2. Harden the viral rule to require corroboration and add `pDL278` plus the five additional transferase records as negative regression cases.
3. Split sequencing-class promoters from expression evidence. Require explicit expression-cassette corroboration and add `pUCP26` as a cloning-vector regression case.
4. Stop treating generic CDS fallback as payload evidence for classification, either by adding a neutral feature type or by marking CDS provenance and excluding fallback CDS from expression inference.
5. Apply consistent token normalization to parser text predicates and tighten the marker family regex.
6. Add regression cases for `arsR/smtB`, `upstream`, valid nested aliases, and the existing curated vectors.

## Conclusion

The two flagged vectors are not isolated anomalies. They reveal two systemic issues: unbounded lexical matching and semantic overloading of generic CDS annotations. The fixes should be made centrally rather than patched record-by-record. Cached raw records are sufficient to validate the changes offline with the reprocessor.
