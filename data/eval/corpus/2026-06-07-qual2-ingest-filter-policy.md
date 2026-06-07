# QUAL-2 Ingest Filter Policy Follow-up

- Source audit: `data/eval/corpus/2026-06-07-132630-unknown-corpus-quality-audit.md`
- Scope: future GenBank ingestion into the engineered-vector corpus lane
- Data mutation: none; no existing corpus rows are deleted or rewritten

## Implemented Guard

`packages.data_pipeline.ingest.genbank.engineered_vector_filter_reason()` now routes obvious non-engineered GenBank records away from future engineered-vector upserts after the raw record has passed sequence/accession mapping checks.

Records are filtered, not treated as ingestion errors. The CLI reports filtered records in the JSON output while keeping the process success criteria tied to real errors.

The initial guard is intentionally conservative and covers only high-confidence cases from the audit:

- `UNVERIFIED` records
- `partial sequence` records
- records longer than the existing engineered-vector length window (`> 50,000 bp`)
- broad RefSeq natural-plasmid accessions (`NC_`, `NZ_`) unless the title explicitly names an engineered vector
- natural strain/isolate/chromosomal-context titles unless the title explicitly names an engineered vector

Trusted engineered-vector title terms currently include `cloning vector`, `expression vector`, `reporter vector`, `shuttle vector`, `lentiviral vector`, `retroviral vector`, `plasmid vector`, and `phagemid`.

## Parser Refinements Surfaced For Review

QUAL-1 found no current unknown records that should be promoted through parser changes. The five prior parser/classifier gap records are already no longer unknown in the latest reprocess snapshot.

Do not implement broad parser changes from natural plasmid signals. Specifically:

- Do not globally treat `rep`, `RepA`, `RepB`, or `RepL` as engineered ORI evidence.
- Do not globally treat natural AMR or metal-resistance genes as engineered selectable-marker evidence.
- Use weak vector-like signals in natural-isolate records as human-review flags, not automatic classifier evidence.

## Follow-up Candidates

Future work can split filtered records into a dedicated natural/reference plasmid lane instead of simply skipping engineered-vector upsert. That should be a separate branch because it needs schema/reporting decisions for lane membership.
