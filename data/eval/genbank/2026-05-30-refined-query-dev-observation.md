# Refined GenBank Query Dev Observation

## Run

- Local run: `make ingest-genbank MODE=dev N=20`
- Ingestion run ID: `4`
- Result: `20` records seen, `20` records upserted, `0` errors
- Completed at: `2026-05-31T01:42:41Z` (`2026-05-30` America/New_York)

## Query Shape

The default query is intentionally biased toward engineered-vector titles:

```text
("cloning vector"[Title] OR "expression vector"[Title] OR "reporter vector"[Title]
OR "shuttle vector"[Title] OR "lentiviral vector"[Title] OR "retroviral vector"[Title]
OR "plasmid vector"[Title] OR vector[Title])
AND ("complete sequence"[Title] OR "complete genome"[Title])
AND 1000:50000[SLEN] AND biomol_genomic[PROP] AND genbank[FILTER]
NOT gbdiv_con[PROP] NOT wgs[FILTER] NOT tsa[FILTER]
```

## Observed Composition

All 20 returned records were engineered-vector-titled entries. The sample included:

- cloning vectors such as pSUP202, pMAK705, pSI, pCI, pCI-neo, and pUCP18/pUCP20/pUCP22/pUCP24/pUCP26;
- expression vectors such as pNam and unc-68:GFP(1-8);
- shuttle vectors such as pDL278, pNF2176, pNF2214, and pRHBR17.

This is visibly more precise for engineered-vector discovery than the earlier broad sample, which was dominated by natural plasmids from clinical and environmental isolates. The refined query should remain the GenBank default.

## Limitations

Title precision does not prove annotation completeness. These records still need cache-first parsing and profile-aware quality reporting before they are considered training-eligible.
