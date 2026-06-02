# Phase 2 Generation Plumbing Spike Report

- Generated at: `2026-06-01-181237`
- Branch: `phase2-spike`
- Scope: bounded offline plumbing spike only
- Generator: `fake-template-generator-v1`
- Constraint engine: `stub-constraint-engine-v0` (`PASS` unconditionally; no biological validation)
- Corpus: existing 82-record retrieval index
- Model spend: none
- GPU spend: none

## Summary

`make spike-generation MODE=offline TEXT="..."` ran end to end for three profile-covering queries: bacterial cloning, bacterial expression, and yeast shuttle.

Each run completed this path:

1. Parse natural-language query into `DesignSpec` using the deterministic existing `IntentParser` implementation.
2. Retrieve one template via the existing hybrid retriever over pgvector.
3. Generate one candidate sequence with `FakeGenerator`, which returns the top retrieved template unchanged.
4. Re-annotate the generated sequence with the Phase 0 parser using the cached GenBank source when it matches the generated sequence.
5. Pass through the Phase 2 spike stub constraint engine.
6. Emit an `AnnotatedSequence` that validates against the canonical schema.

This report makes no sequence-quality, wet-lab feasibility, synthesis-readiness, fine-tuning, or Phase 2 gate claim.

## Run 1 - Bacterial Cloning

- Command: `make spike-generation MODE=offline TEXT="I need a simple high-copy cloning vector for routine plasmid cloning in E. coli."`
- Parsed profile intent: `bacterial_cloning_vector`
- Retrieved template: `curated:pUC19` / pUC19c
- Generated candidate: exact template copy from `FakeGenerator`
- Generated length: `2686 bp`
- Re-annotated profile: `bacterial_cloning_vector`
- Re-annotated feature count: `4`
- Component checks: `bacterial_cloning_vector` matched from re-annotated profile
- Stub validation: `PASS`
- Spike result: `PASS`

Feature summary:

- promoter `lac promoter region` 237-395 confidence `0.83`
- MCS `pUC19 MCS` 395-452 confidence `0.83`
- ORI `pMB1/pUC origin` 866-1455 confidence `0.83`
- marker `AmpR/bla` 1628-2417 confidence `0.83`

## Run 2 - Bacterial Expression

- Command: `make spike-generation MODE=offline TEXT="Which curated plasmid would you use for GST-tagged bacterial protein expression in E. coli?"`
- Parsed profile intent: `bacterial_expression_vector`
- Retrieved template: `curated:pGEX-4T-1` / pGEX-4T-1
- Generated candidate: exact template copy from `FakeGenerator`
- Generated length: `4969 bp`
- Re-annotated profile: `bacterial_expression_vector`
- Re-annotated feature count: `8`
- Component checks: `bacterial_expression_vector` matched from re-annotated profile; `GST` matched via `glutathione S-transferase` feature evidence
- Stub validation: `PASS`
- Spike result: `PASS`

Feature summary:

- promoter `tac promoter for inducible expression of glutathione S-transferase` 182-211 confidence `0.95`
- GOI `glutathione S-transferase` 257-977 confidence `0.95`
- MCS `Multiple Cloning Site (MCS); contains the unique restriction sites BamHI, EcoRI, SmaI, SalI, XhoI, and NotI; The EcoRI site of pGEX-4T1 is in frame with the EcoRI site of lambda gt11` 929-966 confidence `0.95`
- promoter `bla` 1306-1335 confidence `0.95`
- marker `bla` 1306-2237 confidence `0.95`
- ORI `base 2995 represents the first base of the newly synthesized single strand` 2994-2995 confidence `0.95`
- GOI `lacIq` 3317-4400 confidence `0.95`
- promoter `lac promoter region` 4542-4700 confidence `0.83`

## Run 3 - Yeast Shuttle

- Command: `make spike-generation MODE=offline TEXT="I need a yeast shuttle vector with a selectable marker for yeast transformation and maintenance."`
- Parsed profile intent: `yeast_shuttle_vector`
- Retrieved template: `curated:pRS415` / pRS415
- Generated candidate: exact template copy from `FakeGenerator`
- Generated length: `6021 bp`
- Re-annotated profile: `yeast_shuttle_vector`
- Re-annotated feature count: `7`
- Component checks: `yeast_shuttle_vector` matched from re-annotated profile
- Stub validation: `PASS`
- Spike result: `PASS`

Feature summary:

- ORI `f1 origin` 2473-2929 confidence `0.83`
- promoter `lac promoter region` 2932-3090 confidence `0.83`
- MCS `restriction-site dense MCS candidate (8 sites)` 3126-3210 confidence `0.55`
- promoter `T3 promoter` 3247-3265 confidence `0.83`
- ORI `pMB1/pUC origin` 3687-4276 confidence `0.83`
- marker `AmpR/bla` 4449-5238 confidence `0.83`
- ORI `ARSH4` 5565-5929 confidence `0.83`

## Implementation Notes

- `FakeGenerator` is deterministic and returns the top retrieved template unchanged. This satisfies the authorized spike exit criterion and avoids unsupported sequence-quality claims.
- The spike re-annotator first parses the cached source GenBank record when the fake-generated sequence exactly matches the retrieved template sequence, then falls back to sequence-only Phase 0 parser re-annotation.
- The constraint engine is intentionally a PASS-only stub. Real validation checks remain Phase 3 scope.
- During the bacterial-expression run, the parser needed one small controlled-vocabulary hygiene fix: `bacterial protein expression` now maps to `bacterial_expression_vector`, and generic context words such as `bacterial` are no longer accepted as tagged gene symbols.

## Exit Criteria Status

- `make spike-generation TEXT="<query>"` runs end to end: met.
- One parsed `DesignSpec`: met.
- One retrieved template from the existing corpus: met.
- One generated candidate sequence via `SequenceGenerator`: met using `FakeGenerator`.
- Stub `ConstraintEngine` pass: met.
- Re-annotated `AnnotatedSequence` schema-valid and component-confirmed: met for all three report runs.
- No fine-tuning, GPU spend, generation eval gate, model registry, or biological quality claim: met.
