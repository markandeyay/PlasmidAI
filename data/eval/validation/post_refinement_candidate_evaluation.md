# Post-Refinement Candidate Evaluation

- Generated at: `2026-06-18T02:14:27.722538+00:00`
- Candidate count: `13`
- Outcome counts: `{'FAIL': 8, 'PASS': 1, 'WARN': 4}`

| Candidate | Profile | Overall | Failing checks | Warning checks | Defensible now? |
| --- | --- | --- | --- | --- | --- |
| `AF013597.1` | `bacterial_cloning_vector` | `PASS` | `-` | `-` | `True` |
| `AF403427.1` | `bacterial_cloning_vector` | `FAIL` | `repeat_and_instability, regulatory_compatibility` | `-` | `False` |
| `AF519766.1` | `bacterial_cloning_vector` | `FAIL` | `regulatory_compatibility` | `repeat_and_instability` | `False` |
| `AY219701.1` | `bacterial_cloning_vector` | `FAIL` | `repeat_and_instability` | `-` | `False` |
| `U26464.1` | `bacterial_cloning_vector` | `FAIL` | `repeat_and_instability, regulatory_compatibility` | `-` | `False` |
| `AF050464.1` | `bacterial_expression_vector` | `FAIL` | `regulatory_compatibility` | `-` | `False` |
| `U07168.1` | `general_shuttle_vector` | `FAIL` | `repeat_and_instability` | `regulatory_compatibility` | `False` |
| `AF216802.1` | `general_shuttle_vector` | `FAIL` | `repeat_and_instability` | `regulatory_compatibility` | `False` |
| `U47121.2` | `mammalian_expression_vector` | `WARN` | `-` | `repeat_and_instability` | `True` |
| `AF058756.1` | `mammalian_reporter_vector` | `FAIL` | `repeat_and_instability, codon_usage, regulatory_compatibility` | `-` | `False` |
| `AF041805.1` | `yeast_shuttle_vector` | `WARN` | `-` | `repeat_and_instability` | `True` |
| `AF041806.1` | `yeast_shuttle_vector` | `WARN` | `-` | `repeat_and_instability` | `True` |
| `AF041807.1` | `yeast_shuttle_vector` | `WARN` | `-` | `repeat_and_instability` | `True` |

## Check Details

### `AF013597.1`

- `restriction_site_conflicts` `PASS`: No restriction-enzyme cloning context was specified.
- `repeat_and_instability` `PASS`: No blocking repeat, homopolymer, or GC-instability pattern detected.
- `codon_usage` `PASS`: No intended payload GOI was annotated; skipped source-vector context CDS ('lacI, lacZ').
- `regulatory_compatibility` `PASS`: Regulatory elements are compatible with the requested host context.

### `AF403427.1`

- `restriction_site_conflicts` `PASS`: No restriction-enzyme cloning context was specified.
- `repeat_and_instability` `FAIL`: 100 bp window has extreme GC content (19%); redesign this region for synthesis.
- `codon_usage` `PASS`: No GOI coding region was annotated; codon-usage scoring skipped.
- `regulatory_compatibility` `FAIL`: No origin or maintenance element compatible with bacterial host context was detected.

### `AF519766.1`

- `restriction_site_conflicts` `PASS`: No restriction-enzyme cloning context was specified.
- `repeat_and_instability` `WARN`: Homopolymer run of 8 or more bases should be reviewed.
- `codon_usage` `PASS`: No intended payload GOI was annotated; skipped source-vector context CDS (rep).
- `regulatory_compatibility` `FAIL`: No origin or maintenance element compatible with bacterial host context was detected.

### `AY219701.1`

- `restriction_site_conflicts` `PASS`: No restriction-enzyme cloning context was specified.
- `repeat_and_instability` `FAIL`: inverted repeat of at least 40 bp may promote recombination or synthesis instability.
- `codon_usage` `PASS`: No intended payload GOI was annotated; skipped source-vector context CDS (lacZ-alpha fusion protein).
- `regulatory_compatibility` `PASS`: Regulatory elements are compatible with the requested host context.

### `U26464.1`

- `restriction_site_conflicts` `PASS`: No restriction-enzyme cloning context was specified.
- `repeat_and_instability` `FAIL`: direct repeat of at least 40 bp may promote recombination or synthesis instability.
- `codon_usage` `PASS`: No intended payload GOI was annotated; skipped source-vector context CDS (repE, sopA, sopB...).
- `regulatory_compatibility` `FAIL`: No origin or maintenance element compatible with bacterial host context was detected.

### `AF050464.1`

- `restriction_site_conflicts` `PASS`: No restriction-enzyme cloning context was specified.
- `repeat_and_instability` `PASS`: No blocking repeat, homopolymer, or GC-instability pattern detected.
- `codon_usage` `PASS`: No intended payload GOI was annotated; skipped source-vector context CDS (ccdB, lacIq).
- `regulatory_compatibility` `FAIL`: No origin or maintenance element compatible with bacterial host context was detected.

### `U07168.1`

- `restriction_site_conflicts` `PASS`: No restriction-enzyme cloning context was specified.
- `repeat_and_instability` `FAIL`: inverted repeat of at least 40 bp may promote recombination or synthesis instability.
- `codon_usage` `PASS`: No intended payload GOI was annotated; skipped source-vector context CDS (rep, lacZ alpha).
- `regulatory_compatibility` `WARN`: GOI lacks an annotated downstream terminator; expression cassette may be incomplete.

### `AF216802.1`

- `restriction_site_conflicts` `PASS`: No restriction-enzyme cloning context was specified.
- `repeat_and_instability` `FAIL`: 100 bp window has extreme GC content (17%); redesign this region for synthesis.
- `codon_usage` `PASS`: No intended payload GOI was annotated; skipped source-vector context CDS (unknown protein, beta-galactosidase alpha peptide).
- `regulatory_compatibility` `WARN`: GOI 'beta-galactosidase alpha peptide' has no downstream terminator annotation.

### `U47121.2`

- `restriction_site_conflicts` `PASS`: No restriction-enzyme cloning context was specified.
- `repeat_and_instability` `WARN`: direct repeat of at least 40 bp may promote recombination or synthesis instability. Biological context note: this repeat overlaps reviewed intentional vector architecture but still needs synthesis and stable-propagation review.
- `codon_usage` `PASS`: No GOI coding region was annotated; codon-usage scoring skipped.
- `regulatory_compatibility` `PASS`: Regulatory elements are compatible with the requested host context.

### `AF058756.1`

- `restriction_site_conflicts` `PASS`: No restriction-enzyme cloning context was specified.
- `repeat_and_instability` `FAIL`: direct repeat of at least 40 bp may promote recombination or synthesis instability.
- `codon_usage` `FAIL`: GOI codon adaptation score is low for mammalian expression (0.49).
- `regulatory_compatibility` `FAIL`: No origin or maintenance element compatible with mammalian host context was detected.

### `AF041805.1`

- `restriction_site_conflicts` `PASS`: No restriction-enzyme cloning context was specified.
- `repeat_and_instability` `WARN`: direct repeat of at least 40 bp may promote recombination or synthesis instability. Biological context note: this repeat overlaps reviewed intentional vector architecture but still needs synthesis and stable-propagation review.
- `codon_usage` `PASS`: No GOI coding region was annotated; codon-usage scoring skipped.
- `regulatory_compatibility` `PASS`: Regulatory elements are compatible with the requested host context.

### `AF041806.1`

- `restriction_site_conflicts` `PASS`: No restriction-enzyme cloning context was specified.
- `repeat_and_instability` `WARN`: direct repeat of at least 40 bp may promote recombination or synthesis instability. Biological context note: this repeat overlaps reviewed intentional vector architecture but still needs synthesis and stable-propagation review.
- `codon_usage` `PASS`: No GOI coding region was annotated; codon-usage scoring skipped.
- `regulatory_compatibility` `PASS`: Regulatory elements are compatible with the requested host context.

### `AF041807.1`

- `restriction_site_conflicts` `PASS`: No restriction-enzyme cloning context was specified.
- `repeat_and_instability` `WARN`: direct repeat of at least 40 bp may promote recombination or synthesis instability. Biological context note: this repeat overlaps reviewed intentional vector architecture but still needs synthesis and stable-propagation review.
- `codon_usage` `PASS`: No GOI coding region was annotated; codon-usage scoring skipped.
- `regulatory_compatibility` `PASS`: Regulatory elements are compatible with the requested host context.
