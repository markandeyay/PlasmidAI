# Generation Gold Set Rationale

This update expands `data/eval/generation_gold.jsonl` from a small FakeGenerator-oriented smoke set into a broader Phase 2 generation evaluation set for comparing FakeGenerator and future real generators. The rows use explicit `DesignSpec` JSON so EVAL-2 can evaluate generation and re-annotation rather than re-testing intent parsing. Supported rows stay within current parser/corpus profiles: bacterial cloning, bacterial expression, mammalian reporter/expression, yeast shuttle, and general shuttle. Two rows are explicitly `unsupported=true` and excluded from denominators.

## Denominator Policy

- Scored supported cases: 13.
- Unsupported/excluded cases: 2.
- Unsupported rows document future coverage for lentiviral/CRISPR and AAV-style requests but must not count against current FakeGenerator or real-generator baselines.
- Biological acceptability is described in `notes`; the current harness still scores only syntactic validity, requested/expected component recovery, stub constraints, and novelty.

## Case Rationale

### `gen-bacterial-cloning-puc`

Routine high-copy E. coli cloning remains the simplest parser-supported generation scenario. Expected components are a bacterial cloning profile, AmpR/bla marker evidence, bacterial origin, and MCS. pUC18 and pUC19 are both acceptable because the query does not constrain MCS orientation. This is suitable for FakeGenerator wiring and real-generator comparison because a real generator should preserve the core pUC-like acceptability criteria while avoiding verbatim template copying.

### `gen-bacterial-expression-gst`

This keeps the original GST-tagged E. coli expression scenario but makes promoter evidence explicit. Expected components are bacterial expression profile, AmpR, lac/IPTG-inducible promoter evidence, GST tag evidence, origin, marker, and GOI/tag region evidence. pGEX-4T-1 is the supported corpus anchor.

### `gen-yeast-shuttle-prs`

This generic yeast shuttle request tests whether generation preserves a yeast shuttle profile rather than returning a bacteria-only cloning vector. Expected evidence is yeast shuttle classification plus origin and marker features. pRS415, pRS416, and expanded yGALset-style yeast shuttle records are acceptable because the request asks for generic selectable yeast maintenance rather than a specific marker.

### `gen-known-backbone-marker-combo-pbr322`

This is the novel marker-combination-on-known-backbone scenario. pBR322 is a current curated parser-supported backbone with AmpR and TetR evidence. Successful generation should retain pMB1-family bacterial propagation and both selectable markers rather than simplifying to a pUC-style AmpR-only cloning plasmid.

### `gen-known-backbone-lowcopy-marker-combo-pacyc`

This covers a low-copy known-backbone marker-retention case without making chloramphenicol a hard parser-scored requirement. Project notes record that pACYC184 CAT CDS curation is deferred, so the row requires TetR and origin/marker evidence while documenting that the second bacterial marker region should become scoreable after parser support improves. This keeps the case biologically meaningful but avoids a known risky gold-label mismatch.

### `gen-promoter-swap-phagemid-t7t3`

This promoter-swap-style cloning case expects a pUC-family/phagemid cloning backbone whose insert site has T7/T3-style promoter evidence. pBluescript SK(+) and SK(-) are acceptable because both are parser-supported phagemid cloning vectors and orientation is not specified. It is useful for real-generator comparison because a real generator should satisfy the requested promoter-flanked MCS without losing AmpR and bacterial propagation.

### `gen-promoter-swap-mammalian-sv40`

This mammalian promoter-swap/expression case is grounded in the expanded-corpus pSI-style SV40 record. Expected components are mammalian expression profile, SV40 promoter/enhancer evidence, AmpR, origin, marker, and promoter features. It broadens the set beyond bacterial and yeast cases while staying in a current retrieved profile.

### `gen-new-cassette-egfp-cmv`

This is the new cassette insertion / mammalian reporter-expression case anchored on pEGFP-N1. Biological acceptability requires a coherent CMV-EGFP reporter cassette plus mammalian G418/NeoR and bacterial KanR/NeoR evidence. It tests whether a generator preserves both mammalian expression components and bacterial propagation/selection.

### `gen-new-cassette-luciferase-promoterless`

This reporter-assay case expects a promoterless or upstream-cloning-site luciferase reporter backbone. pGL3-Basic, pGL4.10[luc2], and pFR-Luc are acceptable anchors. The key biological point is that adding an unwanted constitutive mammalian promoter would be inappropriate because the assay is intended to test an inserted regulatory element upstream of luciferase.

### `gen-bacterial-expression-t7-amp`

This bacterial expression case uses expanded-corpus T7/AmpR records. Expected components are bacterial expression profile, T7 promoter evidence, AmpR, origin, marker, promoter, and MCS. It complements the GST case by testing promoter-driven bacterial expression without requiring a GST tag.

### `gen-bacterial-shuttle-broadhost-tet`

This supported edge case covers a broad-host-range bacterial shuttle profile, grounded in pUCP26 retrieval evidence. Expected components are general shuttle profile, TetR, origin, marker, and MCS. The case helps distinguish real generation from generic E. coli-only cloning vectors.

### `gen-yeast-shuttle-ura3-specific`

This yeast marker-specific case expects pRS416-like URA3 selection and yeast centromere/shuttle maintenance. It should not accept a LEU2-only vector. It is suitable for FakeGenerator and real-generator comparison because retrieval and generation must preserve the marker constraint.

### `gen-yeast-shuttle-leu2-specific`

This is the LEU2 companion to the URA3 yeast shuttle case. It expects yeast shuttle identity, LEU2 marker evidence, and bacterial propagation features. It checks whether marker-specific yeast shuttle requests are differentiated rather than collapsed into a generic pRS vector.

### `gen-unsupported-lentiviral-crispr-puro`

This row is deliberately unsupported and excluded from denominators. It records future desired coverage for lentiviral CRISPR transfer vectors with U6 sgRNA, Cas9, puromycin, and mammalian promoter requirements. Current project notes say lentiviral/CRISPR profile support is absent or deferred, so using it as a scored case would be misleading.

### `gen-unsupported-aav-packaging`

This row is also unsupported and excluded from denominators. It captures future AAV/ITR/CAG reporter expectations without requiring current parser or constraint support for AAV capacity, ITRs, or transfer-vector profile scoring.

## Suitability For Fake/Real Generator Comparison

FakeGenerator should still perform well on component recovery for many supported rows because it returns retrieved templates, but it should continue to fail novelty when compared against corpus/template sequences. A real generator can be compared against the same rows by checking whether it preserves the requested biological design criteria, avoids unsupported profile hallucination, and produces non-template-copy candidates that the parser can re-annotate.

EVAL-2 can run the baseline against this file as long as unsupported rows are excluded from scoring denominators per the existing harness policy.
