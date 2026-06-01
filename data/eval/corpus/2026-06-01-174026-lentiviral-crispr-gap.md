# Lentiviral and CRISPR corpus-gap diagnostic

Generated: 2026-06-01 17:40:26 America/New_York

## Scope

This RES-3 audit asks whether the current corpus gap for
`lentiviral_or_retroviral_transfer_vector` and `crispr_vector` is caused by:

1. eligible seed records omitted from the curated manifest;
2. records present in Postgres but misclassified; or
3. absent authoritative sequence/provenance under the existing seed policy.

The audit is diagnostic only. It does not add Addgene sequence content, inferred
component sequences, or family-name substitutions.

## Existing policy

`packages/data_pipeline/ingest/curated_seed_manifest.yaml` currently permits
NCBI/GenBank full-sequence records with exact accessions. It excludes
Addgene-only records, Addgene login-gated sequence records, ambiguous family
names, and manufacturer pages without a verified fetchable sequence endpoint.

That remains the correct boundary:

- Addgene's general site terms cover plasmid profiles and sequencing
  information and prohibit commercial use of site content and commercial
  scraping without explicit permission. [Addgene Terms of Use](https://www.addgene.org/terms-of-use/)
- Addgene now offers approved API and bulk-download access, but each requested
  API scope requires an accepted data-access license. [Addgene Developers Portal: Access Options](https://developers.addgene.org/access-options/)
- NCBI places no restrictions on use or distribution of GenBank data, but warns
  that submitters may claim patent, copyright, or other intellectual-property
  rights in submitted data. [NCBI GenBank Overview](https://www.ncbi.nlm.nih.gov/genbank/genbank/)

## Manifest audit

The curated manifest has 12 NCBI-backed records:

`pGEX-4T-1`, `pUC19`, `pUC18`, `pBR322`, `pBluescript II SK(+)`,
`pBluescript II SK(-)`, `pACYC184`, `pEGFP-N1`, `pGL3-Basic`,
`pGL4.10[luc2]`, `pRS415`, and `pRS416`.

It has no lentiviral, retroviral, shRNA, or CRISPR seed record. The parser
profiles list representative examples, but examples are taxonomy documentation,
not approved seed records:

- lentiviral/retroviral: `pLenti-CMV-Puro`, `pLKO.1`, `pLVX`, `pMSCV`
- CRISPR: `pX330`, `pX458`, `pX459`, `lentiCRISPR v2`, `lentiGuide-Puro`

## Read-only Postgres audit

The local Postgres corpus was inspected read-only on 2026-06-01. It contains 82
plasmids: 12 curated seed rows and 70 broad GenBank rows.

The current `plasmid_embeddings.metadata.vector_profile` distribution is:

| profile | rows |
| --- | ---: |
| `bacterial_cloning_vector` | 9 |
| `bacterial_expression_vector` | 3 |
| `general_shuttle_vector` | 7 |
| `mammalian_expression_vector` | 1 |
| `mammalian_reporter_vector` | 4 |
| `unknown` | 55 |
| `yeast_shuttle_vector` | 3 |

There are zero indexed `lentiviral_or_retroviral_transfer_vector` rows and zero
indexed `crispr_vector` rows.

A case-insensitive payload scan for lentiviral/CRISPR terms found four rows:

| id | observed text reason | disposition |
| --- | --- | --- |
| `genbank:AF216802.1` | `spectinomycin adenyltransferase` | bacterial shuttle vector; `ltr` is only a substring |
| `genbank:PZ407647.1` | `N-acetyltransferase-like` | unrelated partial bacterial sequence |
| `genbank:U07166.1` | `gentamycin acetyltransferase-3-1` | bacterial shuttle vector |
| `genbank:U07167.1` | `gentamycin acetyltransferase-3-1` | bacterial shuttle vector |

There are no Postgres name hits for the representative profile examples above.
The old `ltr`-inside-`transferase` false-positive path was already fixed by
token-boundary matching and corroborated viral-signal rules. The current index
does not show a lentiviral or CRISPR misclassification to repair.

## NCBI Entrez audit

NCBI Entrez Nucleotide was queried read-only on 2026-06-01 using the configured
NCBI contact email and `plasmid-design-agent` tool name.

Exact `[Title]` searches returned zero records for every representative example:

| query | exact-title count |
| --- | ---: |
| `pLenti-CMV-Puro` | 0 |
| `pLKO.1` | 0 |
| `pLVX` | 0 |
| `pMSCV` | 0 |
| `pX330` | 0 |
| `pX458` | 0 |
| `pX459` | 0 |
| `lentiCRISPR v2` | 0 |
| `lentiGuide-Puro` | 0 |

Broader `[All Fields]` searches do return records for some family names, but
they are derivatives or patent sequence records rather than an unambiguous
canonical backbone:

- `pLVX`: derivatives such as `MH325104.1` (`pLVX.TRE3G.eGFP`) and patent
  records.
- `pMSCV`: derivatives such as `MT612434.1`, `MT612433.1`, and `LT726944.1`.
- `pX330`: derivatives `KX151731.1` and `KX151730.1`, plus patent records.
- `pX458`: two patent records only.

These records may be useful candidates for a future reviewed derivative lane.
They do not justify silently substituting a derivative for a canonical seed or
importing patent-derived sequence into parser calibration without review.

## Biology classification status

The existing coarse profiles remain biologically defensible:

- Cong et al. establish Cas9 plus guide-RNA machinery for programmable
  CRISPR/Cas editing. [Cong et al., 2013](https://pmc.ncbi.nlm.nih.gov/articles/PMC3795411/)
- Sanjana et al. document `lentiCRISPR v2` and `lentiGuide-Puro`, including
  CRISPR and lentiviral-transfer elements such as psi, RRE, cPPT, and WPRE.
  [Sanjana et al., 2014](https://pubmed.ncbi.nlm.nih.gov/25075903/)
- Addgene's official `lentiCRISPR v2` page labels the deposited material as
  mammalian-expression, lentiviral, and CRISPR, and states that industry terms
  are not available for the material. [Addgene plasmid 52961](https://www.addgene.org/52961/)
- Addgene's official `pLKO.1` protocol documents the TRC cloning vector and
  lentiviral-particle workflow. [Addgene pLKO.1 protocol](https://www.addgene.org/protocols/plko/)

No new classifier rule is proposed. The current precedence of `crispr_vector`
over lentiviral delivery for multi-purpose constructs remains a documented
build inference, not a claim that delivery modality is biologically
unimportant.

## Verification

Focused parser classification tests pass without code changes:

```text
python -m pytest tests/data_pipeline/parse/test_classify.py \
  tests/data_pipeline/parse/test_classifier_regression.py \
  tests/data_pipeline/parse/test_classifier_shuttle_regression.py

56 passed
```

## Decision

Stop without implementation.

The genuine blocker is provenance/legal judgment, not a parser defect:

1. The current NCBI-only curated policy has no unambiguous canonical
   full-sequence accession for the representative lentiviral or CRISPR seeds.
2. Addgene has relevant official records and sequence-bearing pages, but site
   terms and scope-specific licensing prevent treating those sequences as
   commercial parser-calibration inputs without explicit approval.
3. GenBank family-name searches expose derivatives and patent records, but
   selecting any of them as a canonical calibration target requires a reviewed
   biology/provenance decision.

Do not modify the curated manifest, classifier, vector profiles, component
library, parser tests, or biology findings appendix until an approved sequence
source and intended-use policy are recorded for the exact vector variant.
