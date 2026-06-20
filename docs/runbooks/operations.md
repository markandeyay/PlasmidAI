# Operations Runbook

Routine commands assume the repository root as the working directory.

## Prerequisites

1. Start local services and install dependencies when setting up a fresh checkout:

```powershell
make setup
```

2. For normal maintenance, confirm Docker-backed services are reachable before long runs:

```powershell
python scripts/check_services.py
```

3. Use `MODE=offline` for retrieval commands when the embedding model is already cached and network access should not be used.

4. For API deployment or dependency refreshes, keep the backend on FastAPI `>=0.138` and Starlette `>=1.3.1,<2`. This explicit Starlette floor avoids the Starlette 0.51.0 malformed Host-header URL reconstruction vulnerability while keeping the API on the tested FastAPI/Starlette 1.x stack.

## Run Ingestion

Use the Makefile targets rather than calling implementation modules directly.

### Curated Seed

Run the curated manifest ingestion:

```powershell
make ingest-curated
```

Then parse a curated sample to confirm expected annotations are still being recognized:

```powershell
make parse-sample SOURCE=curated
```

### GenBank

Run a bounded GenBank development ingestion:

```powershell
make ingest-genbank MODE=dev N=20
```

Run a larger or mode-specific ingestion only after confirming the mode is intended for the current maintenance task:

```powershell
make ingest-genbank MODE=refseq_plasmid_broad N=50
```

`GENBANK_STALE_DAYS` defaults to `60`. Override it only when intentionally refreshing cached records:

```powershell
make ingest-genbank MODE=dev N=20 GENBANK_STALE_DAYS=0
```

### Addgene

The target exists, but Addgene ingestion is parked until partner access, terms, and commercial licensing are resolved:

```powershell
make ingest-addgene MODE=dev N=20
```

Do not use Addgene-derived entries for curated seeds or training data unless explicit provenance and legal approval has been recorded.

### Reprocess Existing Corpus

After parser or classifier changes, reprocess existing cached records instead of re-ingesting them:

```powershell
make reprocess MODE=all
```

Run the same command a second time to check idempotence. A clean repeat should report zero updates:

```powershell
make reprocess MODE=all
```

Useful scoped variants:

```powershell
make reprocess MODE=all SOURCE=curated
make reprocess MODE=all SOURCE=genbank BATCH_SIZE=50
make reprocess MODE=all PATTERN=pACYC184
```

## Run Validation

Run the deterministic validation engine against corpus/sample records:

```powershell
make validate-sample N=300
```

Run the curated validation gold baseline:

```powershell
make validate-sample MODE=gold
```

Regenerate the synthetic validation gold set only when intentionally updating the deterministic gold construction artifacts:

```powershell
make generate-validation-gold
```

Expected outputs are written under `data/eval/validation/`. The current gate-style report format includes:

- `Known-good cases`
- `Known-bad cases`
- `Accuracy`
- `Phase 3 gate met`
- `Misclassified cases`
- per-check accuracy for `codon_usage`, `regulatory_compatibility`, `repeat_and_instability`, and `restriction_site_conflicts`

Investigate any non-zero misclassification count before treating a validation run as a baseline.

## Run Quality Reports

Generate a corpus quality report after ingestion or reprocessing:

```powershell
make quality-report
```

Reports are written to `data/eval/quality/` as paired Markdown and JSON files named like:

```text
YYYY-MM-DD-HHMMSS-quality-report.md
YYYY-MM-DD-HHMMSS-quality-report.json
```

Read the top summary first:

- `Total records`: corpus size after the run.
- `Complete annotations`: records that satisfy profile-aware completeness.
- `Unclassified records`: records with `unknown` vector profile; track this because retrieval and training quality degrade when useful engineered vectors remain unknown.
- `Duplicate clusters`: exact-sequence duplicate clusters; expected to be small and explainable.
- `Parse errors`: should stay at zero for normal maintenance.

Then inspect profile completeness:

- Healthy engineered-vector profiles should have high completion rates.
- `unknown` should have `0` complete by definition; changes in this count usually indicate classifier or corpus-shape movement.
- Large drops in a known profile usually mean a parser/reference-matching regression or stale cached annotations.

Finally inspect distributions:

- Source counts should match the ingestion scope, for example curated seed records should remain `12` unless the curated manifest was intentionally changed.
- Marker and origin distributions should not suddenly gain obvious false positives such as short alias over-matches.
- Length ranges should match the source strategy; unexpected very short or missing sequences usually point to failed ORIGIN materialization.

For a normal maintenance checkpoint, run this sequence:

```powershell
make reprocess MODE=all
make reprocess MODE=all
make quality-report
```

Treat the second reprocess as an idempotence check. If it updates records, inspect the new reprocess report before publishing the quality report as a stable baseline.

## Add A Curated Seed Entry

Curated seeds live in `packages/data_pipeline/ingest/curated_seed_manifest.yaml`. The manifest currently admits only NCBI/GenBank full-sequence records with exact accessions. Addgene-only records, login-gated sequences, ambiguous vector-family names, and manufacturer pages without verified fetchable sequence endpoints are excluded unless policy changes.

1. Confirm the candidate has a precise plasmid variant, full sequence, and authoritative accession.

2. Add one object to the manifest `records` list with these fields:

```json
{
  "id": "stable-machine-id",
  "name": "Human-readable plasmid name",
  "category": "bacterial_cloning",
  "source": "ncbi",
  "accession": "ACCESSION.VERSION",
  "expected_length_bp": 1234,
  "expected_topology": "circular",
  "curation_notes": "Why this seed is useful and what features it should calibrate.",
  "citations": [
    "https://www.ncbi.nlm.nih.gov/nuccore/ACCESSION.VERSION"
  ]
}
```

3. Keep `id` stable because retrieval gold and reports refer to IDs such as `curated:pACYC184`.

4. Run curated ingestion and parser checks:

```powershell
make ingest-curated
make parse-sample SOURCE=curated
make reprocess MODE=all SOURCE=curated
make quality-report
```

5. If the seed is intended to affect retrieval, refresh embeddings and evaluation:

```powershell
make embed-corpus MODE=offline
make eval-retrieval MODE=offline
```

6. If the seed changes a retrieval expectation, update `data/eval/retrieval_gold.jsonl` with a rationale and source. Do not broaden acceptable IDs just to hide a regression; each acceptable ID needs specific evidence.

## Investigate Retrieval Regressions

Start by reproducing the current baseline:

```powershell
make eval-retrieval MODE=offline
```

If embeddings may be stale after ingestion, reprocessing, parser changes, or curated manifest changes, refresh them first:

```powershell
make embed-corpus MODE=offline
make eval-retrieval MODE=offline
```

Read the newest report in `data/eval/retrieval/`. The top summary shows:

- `Retrieval queries scored`
- `Clarification queries`
- `Top-1 hit rate`
- `Top-5 hit rate`
- `Clarification pass rate`
- `MRR`

Use per-query sections to identify whether the regression is:

- a top-1 ordering regression, where an acceptable answer is still in the top 5 but ranked lower;
- a top-5 miss, where no acceptable ID appears in the retrieved set;
- a clarification regression, where ambiguous prompts are answered instead of clarified;
- a gold-set issue, where the corpus now contains additional defensible answers not reflected in `data/eval/retrieval_gold.jsonl`.

For one suspect query, run it directly:

```powershell
make design MODE=offline TEXT="Recommend a low-copy bacterial cloning plasmid with chloramphenicol resistance."
```

Compare the direct output with the per-query evaluation section:

- Check the parsed intent fields, especially organism, vector type, markers, source, DOI, application, and constraints.
- Check whether exact-name lookup should have triggered. Exact named-record queries should retrieve the named plasmid before semantic ranking.
- Check whether structured filters are too broad or too narrow.
- Check whether the expected record has stale or weak embedding text, such as an engineered curated vector being composed as `Unclassified plasmid`.
- Check whether new corpus records are legitimate near-neighbors and should be added to the gold case with evidence.

When diagnosing a known regression pattern, write a small Markdown diagnostic under `data/eval/retrieval/` with:

- the query and branch;
- parsed intent;
- composed query document;
- exact-name lane result;
- structured filter behavior;
- semantic candidates before and after filters;
- local row or metadata observations;
- recommended minimal fix.

Use `data/eval/retrieval/2026-06-02-102439-pacyc184-regression-diagnostic.md` as the practical model for this format.

## Standard Maintenance Checkpoint

Use this command sequence after routine corpus maintenance:

```powershell
make ingest-curated
make ingest-genbank MODE=dev N=20
make reprocess MODE=all
make reprocess MODE=all
make quality-report
make embed-corpus MODE=offline
make eval-retrieval MODE=offline
make validate-sample MODE=gold
```

For final verification before handoff, run the full test suite:

```powershell
make test
```

Do not commit generated reports unless the maintenance task explicitly asks for a new baseline artifact.
