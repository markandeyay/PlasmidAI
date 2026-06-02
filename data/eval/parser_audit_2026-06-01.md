# Parser Audit 2026-06-01

## Audit Method

PARSE-1 reviewed the parser read-only on branch `phase0-corpus-expansion`.

Reviewed artifacts:

| Area | Files |
| --- | --- |
| Parser implementation | `packages/data_pipeline/parse/sequence_parser.py`, `classify.py`, `expression_evidence.py`, `viral_signals.py`, `origin_support.py`, `marker_support.py`, `text_signals.py` |
| Component references | `packages/data_pipeline/parse/references/component_library.json` |
| Profile definitions | `packages/data_pipeline/parse/vector_profiles.yaml` |
| Curated seed policy | `packages/data_pipeline/ingest/curated_seed_manifest.yaml` |
| Parser tests | `tests/data_pipeline/parse/*.py` |
| Quality report | `data/eval/quality/2026-06-01-214652-quality-report.json` |
| Parser/corpus reports | `data/eval/parser/*.txt`, `data/eval/corpus/2026-06-01-174026-lentiviral-crispr-gap.md` |

Read-only commands used for audit context:

```text
python scripts/parse_sample.py --limit 100 --source curated
python scripts/parse_sample.py --limit 100 --source genbank
```

No files, commits, pushes, or database writes were made during the audit.

## Current Metrics

From `data/eval/quality/2026-06-01-214652-quality-report.json`:

| Metric | Value |
| --- | ---: |
| Total records | 82 |
| Curated records | 12 |
| GenBank records | 70 |
| Complete annotations | 24/82 |
| Complete annotation rate | 29.2683% |
| Parse errors | 0 |
| Unknown profiles | 55 |
| Duplicate clusters | 2 |

Profile distribution:

| Profile | Records | Complete | Rate |
| --- | ---: | ---: | ---: |
| `unknown` | 55 | 0 | 0.0% |
| `bacterial_cloning_vector` | 9 | 9 | 100.0% |
| `general_shuttle_vector` | 7 | 6 | 85.7143% |
| `mammalian_reporter_vector` | 4 | 4 | 100.0% |
| `bacterial_expression_vector` | 3 | 2 | 66.6667% |
| `yeast_shuttle_vector` | 3 | 2 | 66.6667% |
| `mammalian_expression_vector` | 1 | 1 | 100.0% |

Null-rate highlights:

| Field | Null/empty | Rate |
| --- | ---: | ---: |
| `promoters` | 74 | 90.2439% |
| `markers` | 52 | 63.4146% |
| `vector_type` | 18 | 21.9512% |
| `publication_doi` | 82 | 100.0% |

Current parser samples show `curated` at 11/12 complete and `genbank` at 13/70 complete. Most incomplete GenBank records are natural or clinical plasmids with mostly CDS-like `GOI` annotations, so preserving `unknown` is often correct.

## Clean Engineered Records Still Incomplete

| Record ID | Name | Current profile | Current features | Why it matters |
| --- | --- | --- | --- | --- |
| `curated:pACYC184` | `pACYC184` | `unknown` | `ORI:1, marker:1` | Clean curated bacterial cloning vector with p15A origin and chloramphenicol/tetracycline resistance; should not be unknown if both markers are detected. |
| `genbank:AF147463.1` | `T7 Expression vector pNam, complete sequence` | `bacterial_expression_vector` | `GOI:3, MCS:1, marker:1, promoter:1, terminator:1` | Classified correctly but incomplete because no `ORI` is detected. |
| `genbank:AY180162.1` | `Shuttle vector pRHBR17, complete sequence` | `general_shuttle_vector` | `ORI:1, marker:2` | Engineered shuttle-vector metadata is recognized, but no MCS/GOI/promoter is detected. |
| `genbank:U07167.1` | `Cloning vector pUCP24, Escherichia-Pseudomonas shuttle vector ...` | `unknown` | `GOI:3, MCS:1, ORI:1, promoter:1` | Clean broad-host-range cloning/shuttle vector, but no marker is detected even though the title says gentamycin acetyltransferase `aacC1`. |
| `genbank:U47670.1` | `Cloning vector pJDC406, antisense expression vector for Escherichia coli` | `unknown` | `ORI:1, marker:1` | Engineered cloning/antisense vector lacks detected MCS or expression slot. |
| `genbank:U65078.1` | `Cloning shuttle vector pNF2214 with kanamycin resistance gene` | `unknown` | `GOI:1, MCS:1` | Engineered shuttle vector title says kanamycin resistance, but no marker or ORI is detected. |
| `genbank:AF097552.1` | `Expression vector unc-68:GFP(1-8), complete sequence` | `unknown` | `GOI:1, ORI:1, marker:1` | Expression-vector metadata and GFP payload are present, but no promoter/terminator/MCS evidence is detected. |
| `genbank:AF519766.1` | `Cloning vector pMAK705, complete sequence` | `unknown` | `GOI:1, MCS:1, marker:1, promoter:1` | Engineered cloning vector but no ORI is detected. |

## Main Parser Weaknesses

| Rank | Weakness | Impact |
| ---: | --- | --- |
| 1 | `sequence_parser.normalize_feature_type()` drops many meaningful feature annotations because only a small set of GenBank feature types/qualifiers map to component types. | LTRs, WPRE, IRES, 2A peptides, RBS, operators, enhancers, sgRNA scaffolds, and some RNA features can disappear before classification. |
| 2 | The component library is sparse and biased toward current curated seeds. | Engineered records with common modules but no exact reference entry remain unknown or incomplete. |
| 3 | Viral/CRISPR classifier tests use synthetic `other` features, but `sequence_parser.py` never emits `other` features. | Tests prove classifier behavior only after feature extraction; they do not prove real GenBank records with LTR/WPRE/sgRNA annotations will classify. |
| 4 | WPRE is only a text signal inside `viral_signals.py`; it is not emitted as a component type. | Lentiviral transfer vectors can lose one of the strongest post-transcriptional/viral-backbone signals during parsing. |
| 5 | PolyA signals are collapsed into generic `terminator`. | Completeness works for broad profiles, but downstream generation loses whether the terminator is mammalian polyadenylation or bacterial termination. |
| 6 | CRISPR evidence depends on text terms like `cas9`, `sgrna`, `guide rna`, and `grna`, but U6/H1 promoter plus sgRNA scaffold extraction is incomplete. | Guide-only CRISPR/shRNA vectors may remain unknown unless explicit names survive feature normalization. |
| 7 | Marker class normalization misses important antibiotic marker aliases. | Examples include gentamicin/gentamycin `aacC1`, kanamycin-only titles without marker feature capture, and pACYC184 incomplete two-marker support. |
| 8 | Origin support is conservative and reference-limited. | Several engineered vectors have markers/MCS/promoters but fail completeness only because origin evidence is absent. |

## Missing Component Types That Matter

| Component | Current handling | Recommended handling | Downstream reason |
| --- | --- | --- | --- |
| Mammalian polyA signal | Collapsed to `terminator` | Add `polyA_signal` as a distinct type or subtype, while allowing it to satisfy `terminator` requirements. | Mammalian expression generation needs explicit 3-prime module selection. |
| IRES | Usually dropped unless encoded as generic CDS/GOI text | Add `IRES` component type with aliases for internal ribosome entry site and EMCV IRES. | Multicistronic expression cassettes require IRES-aware design and ordering. |
| 2A self-cleaving peptide | Usually dropped or treated as generic CDS/GOI | Add `2A_peptide` component type with aliases `P2A`, `T2A`, `E2A`, `F2A`, `self-cleaving peptide`, and `2A peptide`. | 2A sites define multicistronic protein expression and payload boundaries. |
| WPRE | Recognized only if retained in feature text | Add `WPRE` or `post_transcriptional_regulatory_element` extraction. | WPRE is strong lentiviral-transfer-vector corroboration when paired with LTR or other transfer elements. |
| LTR | Recognized only if retained in feature text | Add `LTR` extraction with 5-prime and 3-prime naming. | LTRs are core transfer-vector evidence; classification should not depend on synthetic test-only features. |
| Psi packaging signal | Recognized only if retained in feature text | Add `packaging_signal` extraction. | Lentiviral/retroviral classification requires LTR plus packaging signal or both LTRs. |
| RRE and cPPT | Recognized only if retained in feature text | Add viral cis-element extraction. | RRE/cPPT are common lentiviral backbone elements and useful corroboration, but not sufficient alone. |
| U6/H1 Pol III promoter | H1 exists in library; U6 absent | Add U6 promoter reference and stronger RNA polymerase III promoter normalization. | U6/H1 promoter plus sgRNA/shRNA scaffold is key CRISPR/shRNA evidence. |
| sgRNA/shRNA scaffold | Usually dropped if `misc_RNA`, `ncRNA`, or `misc_feature` | Add `guide_rna_scaffold` extraction. | CRISPR/shRNA records need guide expression evidence distinct from Cas9 CDS. |
| RBS/Shine-Dalgarno | Usually ignored or dropped | Add `RBS` type or expression-cassette signal type. | Bacterial expression classification needs RBS evidence without relying on free-text survival. |
| Operator/regulatory sites | Usually dropped unless promoter | Add `operator` for lacO/tetO/araC-regulated systems. | T7/lac and inducible systems need operator evidence for expression confidence. |
| Enhancer | Usually dropped unless promoter text includes promoter | Add `enhancer` subtype. | CMV enhancer, SV40 enhancer, CAG architecture, and mammalian promoter strength matter for generation. |

## Classification Implications

| Signal | Classification effect |
| --- | --- |
| WPRE alone | Should not classify as lentiviral/retroviral. Current `test_wpre_alone_is_insufficient` is correct. |
| LTR alone | Should not classify as lentiviral/retroviral. Current single-LTR hardening is correct. |
| Both 5-prime and 3-prime LTRs | Should support `lentiviral_or_retroviral_transfer_vector`. |
| LTR plus psi packaging signal | Should support `lentiviral_or_retroviral_transfer_vector`. |
| LTR plus WPRE/RRE/cPPT/MSCV | Should support `lentiviral_or_retroviral_transfer_vector` only as corroborated viral-backbone evidence. |
| WPRE plus no LTR | Should remain non-lentiviral unless other reviewed viral-transfer evidence exists. |
| U6 or H1 promoter alone | Should not classify as CRISPR. Pol III promoters are also used for shRNA and other small RNA systems. |
| sgRNA scaffold alone | Should support CRISPR evidence but should not mark complete without ORI and marker under the current profile rule. |
| U6/H1 plus sgRNA scaffold | Should strongly support `crispr_vector` or shRNA/guide-vector evidence. |
| Cas9/Cas12 CDS | Should support `crispr_vector` when the term survives extraction. |
| IRES/2A | Should not by itself determine profile, but should improve expression-cassette architecture metadata. |
| polyA signal | Should satisfy mammalian expression/reporter termination requirements, but remain distinct from bacterial terminator semantics. |

## Molecular Biology References

Polyadenylation signals matter because mammalian mRNA 3-prime end formation depends on defined polyadenylation signals such as AAUAAA-like motifs and vector-specific SV40/BGH/rabbit beta-globin polyA modules. References: Proudfoot NJ and Brownlee GG, `3' non-coding region sequences in eukaryotic messenger RNA`, Nature 263, 1976; Wickens M and Stephenson P, `Role of the conserved AAUAAA sequence`, Science 226, 1984.

IRES elements matter because they permit cap-independent internal translation initiation and are commonly used in bicistronic vectors. References: Pelletier J and Sonenberg N, `Internal initiation of translation of eukaryotic mRNA directed by a sequence derived from poliovirus RNA`, Nature 334, 1988; Jang SK et al., `A segment of the 5' nontranslated region of encephalomyocarditis virus RNA directs internal entry of ribosomes`, Journal of Virology 62, 1988.

2A peptides matter because they mediate ribosome-skipping/self-cleaving multicistronic protein expression and define payload boundaries. References: Donnelly MLL et al., `Analysis of the aphthovirus 2A/2B polyprotein cleavage mechanism`, Journal of General Virology 82, 2001; Szymczak AL et al., `Correction of multi-gene deficiency in vivo using a single self-cleaving 2A peptide-based retroviral vector`, Nature Biotechnology 22, 2004.

WPRE matters because it is a post-transcriptional regulatory element from woodchuck hepatitis virus that enhances transgene expression and is common in lentiviral vectors. References: Zufferey R et al., `Woodchuck hepatitis virus posttranscriptional regulatory element enhances expression of transgenes delivered by retroviral vectors`, Journal of Virology 73, 1999; Zufferey R et al., `Multiply attenuated lentiviral vector achieves efficient gene delivery in vivo`, Nature Biotechnology 15, 1997.

LTRs, psi packaging signal, RRE, and cPPT matter because transfer vectors retain viral cis-elements while packaging genes are supplied separately. References: Addgene Lentiviral Guide, https://www.addgene.org/guides/lentivirus/; Zufferey R et al., Nature Biotechnology 15, 1997; Addgene Retroviral Guide, https://www.addgene.org/guides/retrovirus/.

U6/H1 promoters and sgRNA scaffolds matter because CRISPR plasmids often express guide RNAs from RNA polymerase III promoters, with Cas supplied on the same or separate vector. References: Cong L et al., `Multiplex genome engineering using CRISPR/Cas systems`, Science 339, 2013; Mali P et al., `RNA-guided human genome engineering via Cas9`, Science 339, 2013; Sanjana NE, Shalem O, Zhang F, `Improved vectors and genome-wide libraries for CRISPR screening`, Nature Methods 11, 2014.

## Ranked Parser Improvements For PARSE-2

| Rank | Improvement | Impact |
| ---: | --- | --- |
| 1 | Add extraction support for viral cis-elements in `sequence_parser.normalize_feature_type()`. | High; closes the gap where `viral_signals.py` is correct but real parsed records can drop LTR/WPRE/psi/RRE/cPPT before classification. |
| 2 | Add extraction-level tests that build real `SeqRecord` features for LTR, WPRE, psi, RRE, cPPT, U6, sgRNA, IRES, and 2A. | High; covers parser extraction rather than synthetic classifier features only. |
| 3 | Add `polyA_signal` as a distinct feature type or subtype while preserving compatibility with `terminator`. | High; improves mammalian expression/reporter generation metadata without weakening completeness rules. |
| 4 | Add WPRE, IRES, 2A, U6 promoter, BGH polyA, rabbit beta-globin polyA, and common sgRNA scaffold references with approved provenance. | High; use only accession-backed or otherwise approved public sources. |
| 5 | Expand marker alias support in `marker_support.py` and annotation normalization. | High; add gentamicin/gentamycin, `aacC1`, `aac(3)`, hygromycin/HygR, puromycin/PuroR, blasticidin/Bsd, zeocin/Sh ble, and nourseothricin/Nat where supported. |
| 6 | Fix `curated:pACYC184` detection. | High for corpus quality; this clean curated vector should not remain incomplete because only one marker is detected. |
| 7 | Add origin references or fallback text rules for engineered vector families that currently fail only on ORI. | Medium-high; examples include `genbank:AF147463.1`, `genbank:AF519766.1`, and `genbank:U65078.1`. |
| 8 | Add `guide_rna_scaffold` extraction for RNA/misc features containing `sgRNA`, `gRNA`, `guide RNA`, `tracrRNA`, `crRNA`, or `shRNA`. | Medium-high; improves CRISPR/shRNA detection while avoiding seed additions. |
| 9 | Add `RBS` and `operator` feature types or expression-support component subtypes. | Medium; improves bacterial expression confidence and reduces reliance on free-text survival. |
| 10 | Preserve high-impact dropped annotations as named `other` features only if a narrow allowlist is used. | Medium; explicit types are cleaner, but allowlisted `other` is a low-risk fallback if schema constraints remain narrow. |

## Implementation Recommendations

In `packages/data_pipeline/parse/sequence_parser.py`, add feature normalization branches for `repeat_region`, `regulatory`, `misc_feature`, `misc_recomb`, `misc_RNA`, `ncRNA`, `RNA`, `stem_loop`, `primer_bind`, `enhancer`, and `sig_peptide` where qualifier text has narrow, boundary-safe matches.

Keep token-boundary matching via `contains_signal()` and avoid substring regressions like `ltr` inside `transferase`.

Do not classify viral transfer vectors from a single generic `LTR`, `WPRE`, `RRE`, or `cPPT`; preserve the existing corroboration model from `viral_signals.py`.

In `packages/data_pipeline/parse/classify.py`, ensure new viral feature names and types are included in `FeatureContext` evidence text. Treat `guide_rna_scaffold` and explicit `sgRNA scaffold` as CRISPR evidence, but avoid treating U6/H1 alone as CRISPR.

In `packages/data_pipeline/parse/expression_evidence.py`, let `polyA_signal` satisfy mammalian terminator/polyA support. Let `RBS` and `operator` feature types satisfy bacterial expression corroboration instead of relying on feature-name text only. Do not let IRES/2A alone classify a vector as expression.

In `packages/data_pipeline/parse/references/component_library.json`, prioritize only references with approved provenance: BGH polyA, rabbit beta-globin polyA, U6 promoter, WPRE, EMCV IRES, P2A/T2A/E2A/F2A short sequences, and common sgRNA scaffold sequences.

In tests, add extraction-level tests in `tests/data_pipeline/parse/test_sequence_parser.py`, not only classifier-level synthetic tests. Include negative tests for `transferase` not emitting LTR, U6 alone not emitting CRISPR, WPRE alone not emitting lentiviral, and IRES/2A alone not emitting expression.

## Human-Judgment Caveats

- Do not add lentiviral or CRISPR seed records without human approval.
- Do not silently substitute derivative GenBank records for canonical lenti/CRISPR backbones.
- Do not weaken the viral classifier to make WPRE, LTR, RRE, cPPT, gag, pol, or env alone sufficient.
- Do not treat U6/H1 alone as CRISPR.
- Do not conflate `polyA_signal` and bacterial `terminator` in downstream generation, even if both satisfy a high-level completeness requirement.
- Do not overfit natural-plasmid GenBank records. Most of the 55 unknown records are not clean engineered vectors; preserving `unknown` is appropriate when profile-specific evidence is absent.

## Bottom Line

The highest-impact PARSE-2 work is making feature extraction preserve high-impact biological modules that the classifier already partly understands or that downstream generation needs: polyA signals, LTR/psi/WPRE/RRE/cPPT, U6/H1 plus sgRNA scaffolds, IRES, 2A peptides, RBS/operators, and missing marker/origin aliases.

The most concrete immediate corpus-quality target is `curated:pACYC184`: it is a clean engineered curated vector and should not remain incomplete because only one marker is detected.
