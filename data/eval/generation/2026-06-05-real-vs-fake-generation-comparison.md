# Real Vs Fake Generation Comparison

- Fake report: `data/eval/generation/2026-06-05-230925-generation-eval.{md,json}`
- Carbon report: `data/eval/generation/2026-06-05-230759-generation-eval.{md,json}`
- Gold set: `data/eval/generation_gold.jsonl`
- Gold cases: 15 total, 13 scored, 2 unsupported
- Constraint engine: stub, not gate-eligible

## Metrics

| Metric | FakeGenerator | Carbon-500M CPU spike | Delta |
| --- | ---: | ---: | ---: |
| Syntactic valid rate | 1.000 | 1.000 | 0.000 |
| Sane length rate | 1.000 | 1.000 | 0.000 |
| Component complete rate | 0.615 | 0.462 | -0.153 |
| Stub constraint pass rate | 1.000 | 1.000 | 0.000 |
| Novel rate | 0.000 | 1.000 | +1.000 |
| Phase 2 gate proxy rate | 0.615 | 0.462 | -0.153 |
| Strict generation success rate | 0.000 | 0.462 | +0.462 |

## Interpretation

Carbon-500M proves CPU real-model plumbing and produces non-template-copy sequences under the current novelty metric. It improves novelty from `0.000` to `1.000` because the spike generator replaces a short suffix of the retrieved template with a pretrained Carbon continuation.

Component completeness regresses from `0.615` to `0.462`. This is expected for an unfine-tuned model-backed spike: the current reannotation path cannot reuse trusted GenBank features after any sequence edit, and Carbon is not conditioned to preserve exact plasmid components. The Carbon output should not be treated as biologically valid design quality.

Both runs are non-gate-eligible because Phase 3 constraints are stubbed. The strict success rate for Carbon is a plumbing metric, not a Phase 2 gate claim.

## Improved

- Real pretrained inference is now exercised on CPU with Carbon-500M.
- Novelty is non-zero and exact-copy novelty checks distinguish Carbon from FakeGenerator.
- Syntax and length checks still pass on all scored cases because the spike preserves full template length and A/C/G/T normalization.

## Regressed

- Component recovery drops for cases where trusted template annotations were lost after sequence edits.
- Several marker-specific yeast and promoter-swap cases still fail because current generation is not instruction-following and reannotation is conservative.
- Carbon output quality is not evaluated beyond short suffix replacement; no fine-tuning, decoding policy search, or edit-distance-aware repair was attempted.

## Next Work

- Build a validation-aware edit generator or repair pass only after Phase 3 validation lands.
- Add a real model prompt format based on the 140 training triplets, but do not fine-tune without authorization.
- Add sequence-edit locality metrics so suffix-only edits are not over-counted as useful novelty.
- Decide whether GPU spend is authorized for Carbon-3B/Evo 2 benchmarking.
