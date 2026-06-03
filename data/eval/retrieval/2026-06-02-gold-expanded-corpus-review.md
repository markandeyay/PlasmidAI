# Expanded Corpus Gold-Set Review

- Branch: `phase0-retrieval-robustness`
- Scope: GOLD-1 review of broad descriptive retrieval queries after the corpus grew to 206 records.
- Gold file updated: `data/eval/retrieval_gold.jsonl`

## Updates Made

| Query | Added acceptable IDs | Rationale |
| --- | --- | --- |
| Simple high-copy E. coli cloning vector | `genbank:AF310245.1` | pGEM58ZNf(-) is indexed as an E. coli cloning vector with pUC/pGEM-family cloning evidence, MCS/lacZ, and AmpR. |
| Mammalian luciferase reporter assay | `genbank:AF058756.1` | pFR-Luc is indexed as a mammalian firefly-luciferase reporter backbone with AmpR and upstream cloning-site evidence. |
| Yeast shuttle vector with selectable marker | `genbank:AF041805.1`, `genbank:AF041806.1`, `genbank:AF041807.1` | yGALset983/984/985 are indexed as yeast shuttle/expression vectors with yeast maintenance and selectable-marker evidence. |
| Bacterial lacZ alpha pUC backbone | `genbank:L09130.1` | pUC13 is a pUC-family cloning vector with beta-galactosidase indicator, polylinker/MCS, and ampicillin-selection evidence. |
| High-copy ampicillin-resistant pUC plasmid | `genbank:L09130.1` | pUC13 is a pUC-family AmpR cloning plasmid, so it is acceptable when either MCS orientation is acceptable. |
| E. coli T7 expression vector, AmpR, MCS | `genbank:AF087042.1` | pCALnFLAG is indexed as an E. coli-maintained AmpR vector with T7 lac control and cloning/tag-region evidence. |

## Deliberately Not Changed

The low-copy chloramphenicol query remains single-target with `pACYC184`. Although `genbank:U80929.2` pBACe3.6 is a plausible chloramphenicol low-copy cloning record, this gold case is being retained as a canonical pACYC184 regression sentinel until the human decides whether to broaden the label or add copy-number/origin-aware retrieval.

Exact named, source-constrained, or comparison queries were not broadened.
