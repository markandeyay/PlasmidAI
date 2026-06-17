# Known-Good Expansion Analysis

Date: 2026-06-17
Branch: `validation-deepening`

## Summary

No new records were promoted to `curated_known_good.jsonl` in this pass.

VAL-C1 identified 13 plausible public GenBank candidates, but the curated-quality policy requires a complete source-backed annotated payload plus a current ConstraintEngine outcome of `PASS` or justified non-blocking `WARN`. Direct NCBI rehydration and current validation dry-run found that all 13 candidates still trigger at least one `FAIL` under the current Phase 3 rules.

The existing curated set remains 31 known-good and 52 known-bad records. A fresh baseline was written after the restriction/repeat refinements:

- `data/eval/validation/2026-06-17-171814-validation-baseline.json`
- `data/eval/validation/2026-06-17-171814-validation-baseline.md`

Result: accuracy remains `1.000` on 83 curated cases.

## Procedure

- Confirmed `data/eval/validation/curated_known_good.jsonl` currently contains 31 records.
- Confirmed none of VAL-C1's candidate accessions already exist as complete curated JSONL entries.
- Attempted the existing local builder, `python tools_curate_known_good.py`; it failed before writing because the connected database does not contain the `plasmids` table.
- Rehydrated the 13 candidate accessions directly from public NCBI GenBank text and parsed them with `parse_genbank_text`.
- Evaluated each parsed record with `ConstraintEngine` using profile-derived host/spec context.
- Promoted no candidates because each current report contained at least one `FAIL`.

## Candidate Outcomes

| Candidate | Parsed profile | Current outcome | Blocking signal |
| --- | --- | --- | --- |
| `AF013597.1` pATCH1 | `bacterial_cloning_vector` | `FAIL` | Codon usage fails on parsed `lacI`/`lacZ'` GOI fragments. |
| `AF403427.1` pRL1342 | `bacterial_cloning_vector` | `FAIL` | 100 bp local GC extreme plus missing compatible origin/maintenance annotation. |
| `AF519766.1` pMAK705 | `bacterial_cloning_vector` | `FAIL` | Parsed `rep` coding region fails codon usage; origin/maintenance compatibility also fails. |
| `AY219701.1` pAZ1 | `bacterial_cloning_vector` | `FAIL` | Inverted repeat failure plus codon usage failure on parsed lacZ-alpha region. |
| `U26464.1` pZC320 | `bacterial_cloning_vector` | `FAIL` | Direct repeat failure, codon usage failure on maintenance genes, and missing compatible origin/maintenance annotation. |
| `AF050464.1` pKIL-HIS3 | `bacterial_expression_vector` | `FAIL` | Codon usage failure on parsed source-vector GOI plus origin/maintenance compatibility failure. |
| `U07168.1` pUCP26 | `general_shuttle_vector` | `FAIL` | Inverted repeat failure plus codon usage failure on parsed shuttle/vector genes. |
| `AF216802.1` pDL278 | `general_shuttle_vector` | `FAIL` | Local GC extreme plus codon usage failure; regulatory compatibility emits non-blocking WARN. |
| `U47121.2` pSI | `mammalian_expression_vector` | `FAIL` | Direct repeat failure plus T7 promoter flagged as incompatible with mammalian host context. |
| `AF058756.1` pFR-Luc | `mammalian_reporter_vector` | `FAIL` | Direct repeat failure, luciferase codon usage failure, and missing mammalian-compatible origin/maintenance annotation. |
| `AF041805.1` yGALset983 | `yeast_shuttle_vector` | `FAIL` | Direct repeat failure plus T7 promoter flagged as incompatible with yeast host context. |
| `AF041806.1` yGALset984 | `yeast_shuttle_vector` | `FAIL` | Direct repeat failure plus T7 promoter flagged as incompatible with yeast host context. |
| `AF041807.1` yGALset985 | `yeast_shuttle_vector` | `FAIL` | Direct repeat failure plus T7 promoter flagged as incompatible with yeast host context. |

## Interpretation

These outcomes are useful validation signals, not reasons to weaken the known-good bar. Most failures appear to reflect Phase 3 rule limitations rather than obvious biological unsuitability of the source records:

- Codon usage currently treats many parsed source-vector coding regions as de novo GOIs.
- Regulatory compatibility currently treats helper promoters such as T7 in shuttle/expression vectors as host-incompatible rather than context-dependent auxiliary elements.
- Repeat checks still block non-viral engineered vectors with long exact repeats unless a specific biological-context downgrade is implemented.
- Several candidate records parse as annotation-incomplete or lack origin/maintenance evidence that the current parser can classify confidently.

## Decision

Do not append candidates to `curated_known_good.jsonl` in this session. Keep the existing 31-record curated known-good set unchanged until the relevant codon/regulatory/parser limitations are addressed or a human explicitly approves a narrower known-good admission policy for source-vector maintenance cassettes and auxiliary promoters.
