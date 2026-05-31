# Phase 1 Plasmid Retrieval Document Composer

Status: design decision for the Phase 1 embedding foundation.

## Decision

Index one concise natural-language document per plasmid for semantic retrieval. Compose the
document deterministically from normalized `Plasmid` metadata and the parser-produced
`AnnotatedSequence`. Store an audit payload beside the text so every emitted clause can be
traced to its source field or detected feature.

This implements SYSTEM_DESIGN Section 6.2: retrieval documents should resemble the way a
researcher states a goal, while structured metadata remains available for Section 6.4
pre-filtering. The document is a ranking input, not a biological validation result.

## Inputs

The composer consumes:

| Retrieval concept | Canonical input | Notes |
| --- | --- | --- |
| Vector profile | `AnnotatedSequence.vector_profile` | Use the parser profile, not the low-information `Plasmid.vector_type`. |
| Name | `Plasmid.name` | Required and always emitted. |
| Source description | Source-native description or curation note | Emit at most one preferred description. Do not guess one from unrelated fields. |
| Organism | `Plasmid.organism` | Label as an organism annotation, not as the experimental host. |
| Promoters | `Plasmid.promoters` plus detected `promoter` features | Merge metadata and detected features with provenance retained. |
| Markers | `Plasmid.markers` plus detected `marker` features | Merge metadata and detected features with provenance retained. |
| Origins | Detected `ORI` features | Keep replication-origin labels explicit. |
| Terminators | Detected `terminator` features | Includes polyadenylation signals normalized as terminators. |
| GOI and MCS | Detected `GOI` and `MCS` features | Render separately: payloads and cloning slots answer different goals. |
| Use cases | `Plasmid.use_cases` | Render selected non-duplicate values; preserve the full list in the audit payload. |
| Physical properties | `Plasmid.length`, `AnnotatedSequence.topology` | Always emitted. |
| Source | `Plasmid.source`, `Plasmid.id`, `Plasmid.raw_ref` | Emit source class in text. Keep ID and raw reference in audit metadata. |

`Plasmid.organism` is not a reliable target-host field. GenBank engineered vectors can carry
values such as `Cloning vector pSI`, while the current Addgene mapper selects an insert species.
The composer therefore says `Organism annotation:` and never rewrites this field as `for use
in ...`. Experimental host matching belongs in future Addgene context fields,
`ExperimentalContext`, and structured retrieval filters.

The current `use_cases` list is intentionally broad: it may contain curation categories,
curation notes, GenBank definitions or keywords, and Addgene purpose, description,
experimental-use, expression, or tag values. Keep this source fidelity, but record provenance
per value in the audit payload when implementing the composer. A later ingestion revision
should preserve `source_description` separately rather than requiring source-specific
recovery.

## Canonical Text Shape

Emit clauses in this order and omit optional clauses that have no values:

```text
{profile sentence}
Source description: {source_description}.
Organism annotation: {organism}.
Promoters: {promoters}.
Payloads: {gois}.
Cloning sites: {mcs_features}.
Terminators: {terminators}.
Selectable markers: {markers}.
Replication origins: {oris}.
Used for: {use_cases}.
{length} bp {topology} plasmid. Source: {source}.
```

Join the emitted clauses with one ASCII space. The line breaks above document clause
boundaries; they are not emitted. Use sentence case and terminal periods. Do not emit field
paths such as `Plasmid.raw_ref`, JSON, coordinates, confidence scores, raw references,
accession IDs, or placeholders inside the embedded text. The controlled natural-language
prefixes above are part of the template.

This ordering puts the goal-like facts first: vector purpose, source wording, organism
annotation, and expression or cloning architecture. Propagation details follow. Physical and
source facts close the document. A query such as "I need a CMV-driven EGFP reporter selectable
with neomycin" therefore shares nearby natural-language concepts with the document instead of
matching a bag of raw metadata labels.

### Profile Sentences

Use this fixed mapping:

| `vector_profile` | First sentence |
| --- | --- |
| `bacterial_cloning_vector` | `Bacterial cloning vector {name}.` |
| `bacterial_expression_vector` | `Bacterial expression vector {name}.` |
| `mammalian_expression_vector` | `Mammalian expression vector {name}.` |
| `mammalian_reporter_vector` | `Mammalian reporter vector {name}.` |
| `lentiviral_or_retroviral_transfer_vector` | `Lentiviral or retroviral transfer vector {name}.` |
| `crispr_vector` | `CRISPR vector {name}.` |
| `yeast_shuttle_vector` | `Yeast shuttle vector {name}.` |
| `general_shuttle_vector` | `General shuttle vector {name}.` |
| `unknown` or unrecognized value | `Unclassified plasmid {name}.` |

The profile sentence is conservative. Do not infer a payload, host, delivery mode, or
expression claim that the profile does not establish.

## Normalization And Rendering Rules

1. Normalize strings by trimming leading and trailing whitespace and collapsing internal
   whitespace runs to one ASCII space.
2. Treat blank strings and case-insensitive `none`, `null`, `n/a`, and `unknown` as absent,
   except that an unknown vector profile renders the explicit `Unclassified plasmid` sentence.
3. De-duplicate list values by normalized case-folded text while preserving the first display
   spelling. Do not collapse biological aliases such as `bla`, `AmpR`, and `beta-lactamase`
   until a versioned controlled vocabulary exists.
4. Merge metadata values before detected-feature values for promoters and markers. For
   detected features, sort by normalized label for stable document text. Preserve coordinates,
   strand, confidence, and original order in the audit payload.
5. Render detected features with confidence `>= 0.80` as ordinary labels. Render features with
   confidence `>= 0.50` and `< 0.80` with an explicit `candidate` qualifier unless the label
   already says `candidate`. Omit lower-confidence features from embedded text but retain them
   in the audit payload. This matches the current parser's trusted-annotation (`0.95`),
   reference-match (`>= 0.82`), and MCS motif-candidate (`0.55`) lanes.
6. De-duplicate source descriptions and use cases against the normalized plasmid name and each
   other. Prefer a curated curation note, then an Addgene purpose or description, then a
   GenBank definition. Emit at most one source description.
7. Render at most five goal-like use-case values after de-duplication. Keep all values in the
   audit payload. Prefer source order because ingestion already records source or curation
   priority. The versioned `v1` selector admits controlled category tokens and short phrases,
   but excludes values containing `complete sequence`, values already emitted as the source
   description, and low-information standalone terms such as `plasmid`, `vector`,
   `artificial sequence`, and `origin of replication`. Render controlled snake-case categories
   as plain English: for example, `bacterial_cloning` becomes `bacterial cloning`,
   `bacterial_expression` becomes `bacterial expression`, `reporter_fluorescent` becomes
   `fluorescent reporting`, and `yeast_shuttle` becomes `yeast shuttle cloning`.
8. Render list values as a comma-separated list with `and` before the final item. Do not add
   interpretive adjectives such as `high-copy`, `inducible`, or `host-compatible` unless those
   words occur in a source value.
9. Always emit length, topology, and source class. Use `topology unknown` only if a future
   schema permits a missing topology; the current `AnnotatedSequence` schema does not.
10. Version the output as `phase1-plasmid-document-v1`. Rebuild embeddings whenever the
    document version, parser version, or normalization rules change.

The audit payload should contain `document_version`, `plasmid_id`, `raw_ref`, parser profile,
annotation completeness, the emitted clauses, and every candidate value with its origin:
metadata field, source description, curated manifest note, or detected feature including
type, coordinates, strand, and confidence. The vector index is rebuildable derived state; the
source plasmid record and raw artifact remain canonical.

## Null Handling

- Omit optional clauses entirely when their normalized list is empty. Never emit `Promoters:
  none`, empty punctuation, or guessed defaults.
- Keep a promoterless reporter concise and truthful. For example, pGL3-Basic should omit the
  promoter clause rather than imply that annotation is incomplete; its curated description
  already says it is intentionally promoterless.
- Emit `Organism annotation:` only when a non-placeholder value exists. Keep values such as
  `synthetic construct` because they communicate that the record is engineered.
- Emit `Unclassified plasmid` for the conservative `unknown` profile. Unknown records remain
  retrievable for inspection without being presented as validated designs.
- Keep `annotation_complete` in the audit payload and structured filters, not in embedded
  prose. Completeness is a parser-quality state, not a researcher goal.

## Examples

These examples show the intended rendered shape using current Phase 0 seed evidence. They are
illustrative composer fixtures for implementation; the implementation should generate the
final byte-for-byte strings from normalized inputs and detected-feature provenance.

### Bacterial cloning: `curated:pUC19`

```text
Bacterial cloning vector pUC19c. Source description: High-copy cloning vector with lacZ alpha/MCS, AmpR, and pUC/pMB1-derived origin. Organism annotation: Cloning vector pUC19c. Promoters: lac promoter region. Cloning sites: pUC19 MCS. Selectable markers: AmpR/bla. Replication origins: pMB1/pUC origin. Used for: bacterial cloning. 2686 bp circular plasmid. Source: curated.
```

### Bacterial expression: `curated:pGEX-4T-1`

```text
Bacterial expression vector pGEX-4T-1. Source description: GST fusion bacterial expression backbone with tac/lac regulation and AmpR. Organism annotation: unidentified cloning vector. Promoters: tac promoter. Payloads: GST. Cloning sites: restriction-site dense MCS candidate. Selectable markers: bla. Replication origins: pMB1/pUC origin. Used for: bacterial expression. 4969 bp circular plasmid. Source: curated.
```

### Mammalian reporter and expression: `curated:pEGFP-N1`

```text
Mammalian reporter vector pEGFP-N1. Source description: CMV-driven C-terminal EGFP fusion vector with neomycin/G418 mammalian selectable marker and kanamycin bacterial marker. Organism annotation: Cloning vector pEGFP-N1. Promoters: CMV immediate-early enhancer/promoter. Payloads: EGFP. Cloning sites: restriction-site dense MCS candidate. Terminators: SV40 late polyA. Selectable markers: neomycin phosphotransferase and NeoR/KanR. Replication origins: pMB1/pUC origin. Used for: fluorescent reporting. 4733 bp circular plasmid. Source: curated.
```

### Yeast shuttle: `curated:pRS416`

```text
Yeast shuttle vector pRS416. Source description: Yeast centromere vector with URA3 marker; useful for yeast marker and CEN/ARS calibration, not expression-cassette completeness. Organism annotation: Cloning vector pRS416. Cloning sites: restriction-site dense MCS candidate. Selectable markers: URA3. Replication origins: ARSH4 and pMB1/pUC origin. Used for: yeast shuttle cloning. 4898 bp circular plasmid. Source: curated.
```

### General shuttle: `genbank:U07164.1`

```text
General shuttle vector Cloning vector pUCP18, Escherichia-Pseudomonas shuttle vector with beta-lactamase (bla) and LacZ alpha peptide (lacZ alpha) genes, complete sequence. Organism annotation: Cloning vector pUCP18. Payloads: LacZ alpha peptide and replication protein. Cloning sites: pUC19 MCS. Selectable markers: bla. Replication origins: pMB1/pUC origin. Used for: broad-host-range, blue/white screening, and replicon. 4557 bp circular plasmid. Source: genbank.
```

The general-shuttle example exposes one quality pressure: source-faithful names can be long.
If long GenBank names degrade retrieval evaluation, add a separate deterministic display-name
rule in `v2`; do not silently truncate names in `v1`.

## Why Raw DNA Is Excluded

Do not append raw DNA to the natural-language document.

- User goals are natural language. A biomedical text encoder should compare those goals with
  concise biological summaries, not thousands of `A`, `C`, `G`, and `T` characters.
- Raw sequence would dominate token count and dilute high-value concepts such as promoter,
  marker, reporter, host annotation, and use case.
- Circular plasmids have no biologically privileged text start, and reverse complements are a
  separate representation concern. Appending one source rotation creates arbitrary textual
  differences.
- Exact-base tasks require exact-base tooling. Restriction sites, reading frames, primers,
  overlaps, origin-spanning regions, and validation checks must operate on canonical DNA and
  coordinates rather than biomedical text embeddings.

Raw DNA remains canonical in `Plasmid.sequence` and the raw source artifact. Sequence-window
and component-level embeddings may be added as separate indexed representations, as proposed
in `research/findings/representation.md`; they must not be mixed into the Phase 1 composed
text document.

## Evidence And Follow-Up

- SYSTEM_DESIGN Section 6.2 explicitly requires a composed natural-language document per
  plasmid and Section 6.4 requires hybrid structured filtering plus semantic ranking.
- `research/SYNTHESIS.md` and `research/findings/representation.md` call for composed text,
  structured metadata, provenance-preserving component chunks, and separate sequence windows.
- `research/findings/data_sources.md` recommends Addgene context fields for retrieval and
  GenBank primarily for annotations plus linked context.
- The current quality report has 82 records but only 24 complete annotations; promoters are
  empty on 90.2% and markers on 63.4%. Omission-based null handling is therefore required.
- The current corpus contains two exact-sequence duplicate clusters. The indexer should
  preserve source records independently for audit, while retrieval evaluation should group or
  collapse exact-sequence duplicates so duplicated accessions do not inflate ranking quality.

Before implementation is considered complete, add byte-for-byte composer tests for each
profile family, promoterless reporters, unknown profiles, low-confidence MCS candidates,
alias-preserving de-duplication, long GenBank names, and exact-sequence duplicate records.
