# Curated Known-Bad Validation Uncertainty Log

The JSONL set intentionally excludes ambiguous or context-dependent biology that should not be treated as known-bad.

- Incidental restriction sites in Gibson/HiFi/LIC, Gateway/TOPO, or synthesis-only designs were excluded unless a named enzyme constraint made the site blocking.
- Missing downstream terminator/polyA cases were excluded from this blocking set because the current engine reports that path as WARN and cloning-only contexts can be valid without a terminator.
- Required viral LTR/ITR-like repeats were excluded because they can be biologically necessary even when they create propagation or synthesis review risk.
- CMV-context silencing, promoter strength, induction dose, and cell-line-specific expression concerns were excluded because they are advisory rather than deterministic FAIL criteria here.
- Broad-host-range origin interpretation outside the current calibrated bacterial/yeast/mammalian host classes was excluded.
