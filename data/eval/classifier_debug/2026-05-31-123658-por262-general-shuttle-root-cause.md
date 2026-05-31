# Classifier Debugging Report: pOR262 / U40578.1 General-Shuttle False Positive

Generated: 2026-05-31 12:36:58 America/New_York

## Scope

This is a read-only DEBUG-2 investigation of `genbank:U40578.1` / `pOR262`.
It traces the current parser and classifier from the cached raw GenBank blob,
audits executable classifier and completeness rules for related raw-count
proxies, and scans the current cached corpus for exposure. No production code,
tests, cache objects, or reprocess artifacts were modified.

Inputs inspected:

- cached MinIO blob `raw/genbank/U40578.1.gb`
- `packages/data_pipeline/parse/sequence_parser.py`
- `packages/data_pipeline/parse/classify.py`
- `packages/data_pipeline/parse/expression_evidence.py`
- `packages/data_pipeline/parse/references/component_library.json`
- `packages/data_pipeline/parse/vector_profiles.yaml`
- `tests/data_pipeline/parse/test_classify.py`
- `tests/data_pipeline/parse/test_classifier_regression.py`
- current 82-record Postgres corpus and its cached raw blobs
- protected parent-review artifact
  `data/eval/reprocess/2026-05-31-021412-reprocess-all.json`

## Executive Summary

`pOR262` is deterministically misclassified as `general_shuttle_vector` because
the generic shuttle rule treats a raw count of two `ORI` features as evidence
of multiple hosts:

```python
if context.count("ORI") >= 2 and context.has("marker"):
    return ClassificationResult(
        "general_shuttle_vector",
        0.68,
        ("multiple origins", "selectable marker"),
    )
```

The two ORI calls do not establish host diversity. Tier 1 preserves the cached
GenBank annotation `pBR322 origin of replication (ROP protein).`; Tier 2 adds a
`pMB1/pUC origin` reference match. Both are bacterial-backbone signals. Neither
feature names a second host or a second-host maintenance system.

The false shuttle profile also changes `annotation_complete` from `false` to
`true`. The matching completeness rule repeats the ORI-count assumption and is
satisfied by the same two ORI calls, one marker, and the record's promoter or
generic CDS-derived `GOI` features.

The audit found one other raw-count proxy family: bacterial-cloning admission
and completeness use `marker >= 2` as an alternative to `marker + MCS`. That is
a count of detected marker annotations, not proof of distinct marker classes
or an equivalent insert-disruption structure.

## Cached Source Record

| Field | Value |
| --- | --- |
| Cache key | `raw/genbank/U40578.1.gb` |
| Accession | `U40578.1` |
| LOCUS | `CVU40578`, 9476 bp, circular, synthetic |
| DEFINITION | `Cloning vector pOR262, pINIIIompA3-rat P450 reductase expression vector, complete sequence` |
| SOURCE | `Cloning vector pOR262` |

Relevant raw GenBank features:

| Raw feature | GenBank coordinates | Relevant qualifier |
| --- | --- | --- |
| `regulatory` | `1..391 +` | `lpp-lac fusion promoter.` |
| `CDS` | `392..>454 +` | `ompA`; E. coli outer-membrane signal peptide |
| `CDS` | `<455..2515 +` | `NADPH-cytochrome P450 reductase` |
| `regulatory` | `2928..3209 +` | `lpp (lipoprotein) gene transcription terminators.` |
| `CDS` | `3882..4964 +` | `lacI`; `lac repressor` |
| `rep_origin` | `7064..7255 +` | `pBR322 origin of replication (ROP protein).` |
| `CDS` | `complement(8442..9302)` | `beta-lactamase`; ampicillin selection |

The cached source itself identifies an expression vector and provides a
bacterial `lpp-lac` promoter. It does not identify a second host.

## Detected Features

Parser output from the current code, using zero-based coordinates:

| Tier | Type | Coordinates | Confidence | Name |
| --- | --- | --- | --- | --- |
| Tier 1 trusted annotation | `promoter` | `0..391 +` | `0.9500` | `lpp-lac fusion promoter.` |
| Tier 1 trusted annotation | `GOI` | `391..454 +` | `0.9500` | `ompA` |
| Tier 1 trusted annotation | `GOI` | `454..2515 +` | `0.9500` | `NADPH-cytochrome P450 reductase` |
| Tier 1 trusted annotation | `terminator` | `2927..3209 +` | `0.9500` | `lpp (lipoprotein) gene transcription terminators.` |
| Tier 1 trusted annotation | `GOI` | `3881..4964 +` | `0.9500` | `lacI` |
| Tier 1 trusted annotation | `ORI` | `7063..7255 +` | `0.9500` | `pBR322 origin of replication (ROP protein).` |
| Tier 2 reference match | `ORI` | `7682..8271 +` | `0.8275` | `pMB1/pUC origin` |
| Tier 1 trusted annotation | `marker` | `8441..9302 -` | `0.9500` | `beta-lactamase` |

No Tier 3 motif feature was emitted.

Final raw feature counts:

| Type | Count |
| --- | ---: |
| `GOI` | 3 |
| `ORI` | 2 |
| `marker` | 1 |
| `promoter` | 1 |
| `terminator` | 1 |

### How The Second ORI Appears

`features_from_annotations()` maps the raw `rep_origin` feature to `ORI`.
`features_from_reference_matches()` then searches the component library and
retains a separate `pMB1/pUC origin` match. The Tier 1 name is not an exact
`names_match()` match for the Tier 2 reference name or its aliases, and the two
coordinate spans do not overlap enough for `overlaps_existing()` to suppress
the reference feature.

The resulting two ORI objects are distinct parser features, but the classifier
does not establish that they represent origins for distinct hosts.

## Exact Classifier Cascade

`classify()` evaluates rules in this order and returns the first match:

| Order | Rule | Result | Reason |
| ---: | --- | --- | --- |
| 1 | `crispr_vector` | no match | No CRISPR term |
| 2 | `lentiviral_or_retroviral_transfer_vector` | no match | No corroborated viral-transfer signal |
| 3 | `yeast_shuttle_vector` | no match | No boundary-safe yeast term |
| 4 | `mammalian_reporter_vector` | no match | No reporter term |
| 5 | `mammalian_expression_vector` | no match | No supported mammalian promoter with oriented slot |
| 6 | `bacterial_expression_vector` | no match | `lpp-lac` is not one of the supported promoter aliases |
| 7 | `general_shuttle_vector` | **match** | `ORI=2` and `marker=1` |
| 8 | `bacterial_cloning_vector` | not reached | First-match cascade already returned |

The exact winning result is:

```text
ClassificationResult(
  profile='general_shuttle_vector',
  confidence=0.68,
  signals=('multiple origins', 'selectable marker'),
)
```

Direct evaluation of the bacterial-expression evidence helper returns:

```text
ExpressionEvidence(
  qualifies=False,
  confidence=0.0,
  signals=(),
  reasons=('generic CDS/GOI annotation alone is not expression-purpose evidence',),
)
```

The conservative generic-CDS rule is working as designed: a generic `GOI`
annotation alone should not imply expression purpose. The pOR262 miss occurs
because the helper does not recognize the source's `lpp-lac` promoter name, and
the later general-shuttle fallback is allowed to interpret two ORI features as
multi-host evidence.

Direct evaluation of the lower-priority bacterial-cloning rule would also
return no match for this record: pOR262 has one marker and no detected MCS.
`general_shuttle_vector` is therefore the first and only current admission
rule that accepts it.

## Completeness Side Effect

The executable completeness rule is:

```python
if profile == "general_shuttle_vector":
    return (
        context.count("ORI") >= 2
        and context.has("marker")
        and context.has_any("MCS", "GOI", "promoter")
    )
```

For pOR262:

| Predicate | Value | Evidence |
| --- | --- | --- |
| `count("ORI") >= 2` | `true` | Tier 1 `pBR322 origin`; Tier 2 `pMB1/pUC origin` |
| `has("marker")` | `true` | Tier 1 `beta-lactamase` |
| `has_any("MCS", "GOI", "promoter")` | `true` | Tier 1 promoter and three generic CDS-derived `GOI` calls |

The protected run-4 parent artifact records the resulting database delta:

```text
genbank:U40578.1 annotation_complete false -> true
vector_profile=general_shuttle_vector
```

## Raw-Count Proxy Audit

The executable classifier and completeness implementation contains two
feature-count proxy families. `vector_profiles.yaml` mirrors both rules as
policy documentation.

| Proxy | Executable locations | YAML mirror | Semantic gap |
| --- | --- | --- | --- |
| `ORI >= 2` | `classify.py:70`, `classify.py:230` | `vector_profiles.yaml:116` | Raw ORI count stands in for host diversity. It does not require distinct host context, distinct origin families, or a second-host maintenance element. |
| `marker >= 2` | `classify.py:55`, `classify.py:223` | `vector_profiles.yaml:23` | Raw marker count stands in for a cloning-vector equivalent to `marker + MCS`. It does not require distinct marker classes, distinct names, distinct loci, or evidence that insertion disrupts a marker. |

No other executable classifier or completeness rule uses a raw feature count
as host-diversity or class-diversity evidence.

`classify.py:164` uses `len(signals) >= 2` only to adjust CRISPR confidence after
CRISPR admission. It is not a host-diversity or class-diversity gate.
Tier 3 MCS detection also counts restriction sites, but that count detects one
component candidate rather than inferring host or marker diversity.

## Current Corpus Exposure

A read-only scan parsed all 82 current database records from cached blobs and
evaluated the two count predicates.

### ORI-Count Shuttle Predicate

The direct `general_shuttle_vector()` predicate fires on 11 records. Six are
protected by higher-priority profiles. Five currently land in
`general_shuttle_vector`:

| Record | Current final profile | Counted ORIs | Why this demonstrates exposure |
| --- | --- | --- | --- |
| `curated:pBluescript-II-SK-minus` | `general_shuttle_vector` | `f1 origin`; `pMB1/pUC origin` | Phagemid origins are counted as multi-host shuttle evidence. |
| `curated:pBluescript-II-SK-plus` | `general_shuttle_vector` | `f1 origin`; `pMB1/pUC origin` | Same phagemid path as the minus variant. |
| `genbank:U40578.1` / `pOR262` | `general_shuttle_vector` | `pBR322 origin`; `pMB1/pUC origin` | Same bacterial-backbone family is counted as multi-host evidence. |
| `genbank:U47119.2` / `pCI` | `general_shuttle_vector` | `phage f1 region`; `pMB1/pUC origin` | Cached DEFINITION calls this a mammalian expression vector. |
| `genbank:U47120.2` / `pCI-neo` | `general_shuttle_vector` | `phage f1 region`; `SV40 minimum origin`; `pMB1/pUC origin` | Cached DEFINITION calls this a mammalian expression vector. |

The six higher-priority records on which the same direct predicate fires are
`curated:pEGFP-N1`, `curated:pGL3-Basic`, `curated:pGL4-10-luc2`,
`curated:pRS415`, `curated:pRS416`, and `genbank:U47121.2`. Their final profile
is determined before the generic shuttle fallback runs.

### Marker-Count Cloning Predicate

Three current cached records have `ORI`, no detected `MCS`, and at least two
marker calls, so they use or are exposed to the marker-count cloning fallback:

| Record | Marker calls |
| --- | --- |
| `curated:pBR322` | `tet`; `bla` |
| `genbank:AY180162.1` / `pRHBR17` | `tetracycline resistance protein`; `AmpR/bla` |
| `genbank:AY428809.1` / `pSUP202` | `tet`; `bla`; `cat` |

The current corpus examples have visibly distinct marker names, so this scan
does not demonstrate a current marker-count false positive. The rule remains a
raw-count proxy and does not enforce the class diversity or structural
equivalence that its cloning fallback assumes.

## Test Coverage Observation

The regression matrix includes a synthetic general-shuttle fixture with:

```text
ORI: ColE1 E. coli origin
ORI: second-host replication origin
marker: AmpR/bla
MCS: multiple cloning site
```

That fixture verifies the current ORI-count behavior when its feature names are
semantically curated. It does not test same-family bacterial origins, phagemid
`f1 + pMB1` combinations, or explicit second-host-context requirements.

The curated-seed unit tests model pBluescript with one pUC origin, so they
continue to expect `bacterial_cloning_vector`. The cached curated pBluescript
records include both `f1 origin` and `pMB1/pUC origin`, reach the generic
shuttle rule, and currently classify as `general_shuttle_vector`.

## Root Cause Statement

The pOR262 failure is caused by semantic overreach in the generic shuttle
fallback and its matching completeness rule. The parser emits two legitimate
ORI features from a bacterial expression-vector backbone, but
`general_shuttle_vector` equates raw ORI multiplicity with multi-host
capability. Because pOR262 is not admitted by the narrower expression helper,
that fallback becomes the first matching classifier rule and incorrectly marks
the record as both a shuttle vector and annotation-complete.

No fixes were written as part of this investigation.
