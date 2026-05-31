# Retrieval Gold Expansion Rationale

## Scope

This expansion adds nine Phase 1 gold records to the existing 12-record starter set, bringing the total to 21. Eight new records target verified non-curated GenBank rows from the live local corpus. One record is an intentionally underspecified clarification case with no claimed target.

The live corpus was checked read-only on 2026-05-31 through local Postgres at `127.0.0.1:55432`. It contained 82 plasmids: 12 curated records and 70 GenBank records. Every retrieval target below was confirmed present in both `plasmids` and `plasmid_embeddings` before it was added.

## New Cases

| Query focus | Verified target | Indexed profile | Why it is included |
| --- | --- | --- | --- |
| Terse E. coli T7 expression request with AmpR and MCS | `genbank:AF147463.1` / pNam | `bacterial_expression_vector` | Exercises bacterial-expression, host, and marker filters with terse wording. |
| E. coli cloning backbone requiring ampicillin, tetracycline, and chloramphenicol resistance | `genbank:AY428809.1` / pSUP202 | `bacterial_cloning_vector` | Exercises conjunction of three hard marker filters and separates pSUP202 from two-marker backbones. |
| E. coli-Pseudomonas broad-host-range TetR shuttle vector with lacZ alpha | `genbank:U07168.1` / pUCP26 | `general_shuttle_vector` | Covers a real multi-host shuttle target and combines host intent with a hard tetracycline filter. |
| `E. coli SpecR shuttle vector.` | `genbank:AF216802.1` / pDL278 | `general_shuttle_vector` | Tests terse controlled-marker normalization and shuttle-profile filtering. |
| Mammalian pSI-style expression plasmid with SV40 enhancer/early promoter and AmpR | `genbank:U47121.2` / pSI | `mammalian_expression_vector` | Covers the available mammalian-expression profile and combines host, profile, and marker filters. |
| Researcher lookup for AmpR pFR-Luc mammalian luciferase reporter | `genbank:AF058756.1` / pFR-Luc | `mammalian_reporter_vector` | Extends reporter evaluation beyond curated seeds while preserving a realistic named-backbone request. |
| Yeast shuttle comparison using Zygosaccharomyces rouxii pSB3 with ARS | `genbank:PV135004.1` / pSB3 | `yeast_shuttle_vector` | Covers the available non-curated yeast-profile row without claiming it is a Saccharomyces engineering backbone. |
| Bacterial resistance-plasmid comparison using Aeromonas pRAS1_2402_89 | `genbank:PZ138287.1` / pRAS1_2402_89 | `unknown` | Forces retrieval over a broader natural GenBank row and retains the corpus label instead of fabricating a vector profile. |
| Underspecified viral vector with unspecified antibiotic resistance | none; `expected_clarification=true` | none | Retrieval should clarify viral system and marker rather than invent a target. |

## Coverage

Across the full 21-record set, supported indexed profiles exercised by labeled retrieval targets are:

- `bacterial_cloning_vector`
- `bacterial_expression_vector`
- `general_shuttle_vector`
- `mammalian_expression_vector`
- `mammalian_reporter_vector`
- `yeast_shuttle_vector`
- `unknown`, used only for an explicitly comparative natural-plasmid retrieval

The added records vary terse, direct, prose, and researcher-style requests. They deliberately stress the implemented hard structured filters for vector profile, host/organism bucket, and selectable marker. The pSUP202 request is the strongest conjunction case because all three requested antibiotic markers must match.

## Live Dry Run

A read-only live retrieval dry run after expansion scored 20 retrieval queries separately from the clarification-only case:

- Top-1 hit rate: `0.650`
- Top-5 hit rate: `0.900`
- MRR: `0.743`
- Clarification pass rate: `1.000`

Two new cases intentionally expose tuning work. The pDL278 query parses as `general_shuttle_vector`, `Escherichia coli`, and `spectinomycin`, but the current organism filter rejects the verified target because its indexed metadata lacks explicit bacterial-host evidence. The natural Aeromonas pRAS1_2402_89 comparison target also misses top-5 under current query composition and ranking. These labels remain useful because they represent real corpus rows and do not claim unsupported profiles.

## Corpus Gaps And Judgment Calls

The live 82-record corpus has no indexed `lentiviral_or_retroviral_transfer_vector` records and no indexed `crispr_vector` records. No lentiviral, retroviral, AAV, or CRISPR retrieval target is labeled in this expansion. The clarification-only viral query records the expected behavior for an underspecified request without fabricating a corpus target.

`genbank:PV135004.1` is a native Zygosaccharomyces rouxii plasmid with an indexed ARS region. It is included only as a yeast-shuttle comparison case. `genbank:PZ138287.1` is a natural Aeromonas resistance plasmid with `tetA`, `tetR`, `sul1`, and `dfrA16`; its indexed profile remains `unknown`, so the gold label is comparative retrieval rather than engineered-vector recommendation.

The broader corpus also contains source descriptions for pCI and pCI-neo mammalian expression vectors, but their current indexed profiles are `bacterial_cloning_vector`. They were not labeled as mammalian-expression targets here because doing so would hide an unresolved classification issue.
