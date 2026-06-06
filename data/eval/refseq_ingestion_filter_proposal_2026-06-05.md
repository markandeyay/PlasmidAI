# RefSeq Ingestion Filter Proposal

## Summary

The `refseq_plasmid_broad` mode should remain available as a public natural-plasmid discovery lane, but it should not be treated as an engineered-vector generation corpus without additional filters. The Phase 2 unknown audit found that most new unknown records are natural isolate, mobile, AMR-heavy, unnamed, or sparse RefSeq plasmids. These records are real public plasmids, but they are poor templates for Phase 2 engineered-vector generation.

This document proposes future filters only. It does not delete or mutate existing corpus records.

## Proposed Future Modes

| Mode | Purpose | Default training use |
| --- | --- | --- |
| `refseq_plasmid_broad` | Broad public RefSeq plasmid discovery and comparative retrieval. | Excluded from generation targets unless explicitly allowed. |
| `refseq_plasmid_engineered_review` | Human-review queue for RefSeq records with engineered-vector signals. | Review required before training. |
| `genbank_engineered_vector_generation` | High-signal public GenBank engineered-vector lane. | Eligible after parser quality checks and provenance policy. |

## Proposed Exclusion Signals For Generation Targets

Exclude or route to a non-template lane when a record lacks explicit engineered-vector title terms and matches one or more of these patterns:

- Natural provenance title terms: `strain`, `isolate`, `unnamed`, `environmental`, `clinical`, `MAG`, `metagenome`.
- Low-confidence record status: `UNVERIFIED`, `partial sequence`, missing concrete `ORIGIN`, length outside configured plasmid target bounds.
- Mobility/conjugation dominance: `mob`, `relaxase`, `tra`, `virB`, `virD`, `type IV secretion`, `integrase`, `transposase`, `IS`, `toxin-antitoxin`, `partition`, `ParA`, `ParB`.
- Natural AMR or metal-resistance payload dominance: `blaZ`, `blaR1`, `blaI`, `GES`, `aadA`, `qnr`, `sul1`, `tetA`, `tetR`, `dfrA16`, `aacA`, `aphD`, `cadD`, `fexB`, `msr(A)`, `Mph(C)`, `VraH`.
- Sparse annotation: no engineered-vector title plus no parsed promoter/MCS/terminator and fewer than two informative non-hypothetical feature names.

## Required Inclusion Signals For Engineered-Vector Training Lanes

Require at least one trusted engineered-vector title term and at least two corroborating component classes:

- Title terms: `cloning vector`, `expression vector`, `reporter vector`, `shuttle vector`, `phagemid`, `plasmid vector`, or reviewed known-vector family names.
- Component classes: ORI, marker, promoter, MCS, terminator, reporter/payload, tag, yeast maintenance element, or reviewed shuttle-origin evidence.

## Guardrails

- Do not classify or include natural plasmids solely because they contain `rep`, `RepA`, `RepB`, `RepL`, or resistance genes.
- Do not treat AMR genes in natural isolate records as engineered selectable-marker evidence without engineered-vector metadata.
- Do not automatically delete existing records; route future records to lane-specific manifests and report counts.
- Keep unsupported/refused licensing sources outside ingestion until explicit terms are approved.

## Review Questions

- Should broad natural RefSeq records remain searchable for comparative retrieval while excluded from training manifests?
- Should AMR/mobile natural plasmids be hidden from product-facing retrieval, or only excluded from generation training?
- What sparse-annotation threshold should become enforceable: fewer than two informative non-hypothetical features, no promoter/MCS/terminator, or both?
