# PlasmidAI

PlasmidAI is an AI-assisted plasmid design platform. A researcher describes an experimental goal in plain English, and the system is intended to produce a complete, annotated, synthesis-ready plasmid design: DNA sequence, labeled component map, validation report, primer designs, and export files for synthesis handoff.

## Project Status

The project is in **Phase 0: Foundations and Data Pipeline**. The local development stack, canonical schemas, NCBI GenBank ingestion, an NCBI-backed curated seed ingester, and the first profile-aware sequence parser are working. Parser completeness is now evaluated against vector-type-specific rules instead of a single universal rule. The next milestone is the baseline data-quality report, followed by continued corpus improvement and parser validation.

See [PROGRESS.md](PROGRESS.md) for the authoritative real-time build state and open questions.

## Repository Orientation

Two files keep the long-running build aligned:

- [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) is the immutable build specification and source of truth.
- [PROGRESS.md](PROGRESS.md) is the mutable session state: completed work, current phase, blockers, and the next task.

Phase R research lives under [`research/`](research/). The shareable research report is [`research/phase_r_report.pdf`](research/phase_r_report.pdf), with its LaTeX source beside it.

The main packages are:

- [`packages/core/`](packages/core/) - shared Pydantic domain schemas and canonical data contracts.
- [`packages/data_pipeline/`](packages/data_pipeline/) - Phase 0 ingestion, parsing, annotation, and data-quality jobs.
- [`packages/retrieval/`](packages/retrieval/) - Phase 1 intent parsing, embeddings, indexing, and template retrieval.
- [`packages/generation/`](packages/generation/) - Phase 2 model loading, training, and sequence generation.
- [`packages/validation/`](packages/validation/) - Phase 3 deterministic biological and synthesis constraint checks.
- [`packages/assembly/`](packages/assembly/) - annotated maps, export files, primers, and synthesis handoff artifacts.
- [`packages/feedback/`](packages/feedback/) - Phase 5 outcome capture and training feedback flow.

## Getting Started

Prerequisites: Git, Python, Docker Compose, and GNU Make.

```bash
git clone https://github.com/markandeyay/PlasmidAI.git
cd PlasmidAI
cp .env.example .env
# Set NCBI_EMAIL in .env to a real contact email before using NCBI Entrez.
make setup
make test
```

On PowerShell, use `Copy-Item .env.example .env` instead of `cp` if needed.

NCBI requires a real contact email for Entrez requests. `NCBI_API_KEY` is optional and increases the supported request rate. Bulk Addgene access is pending partner-program approval and commercial licensing review; do not add credentials or enable it unless that approval is in place.

## How the System Works

The `IntentParser` converts a plain-English research goal into a structured design specification. The `Retriever` finds relevant real plasmids and templates from the indexed corpus. The `SequenceGenerator` proposes candidate plasmid sequences from the specification and retrieved templates. The deterministic `ConstraintEngine` validates biological structure and synthesis constraints. The `Assembler` creates the annotated map, GenBank/FASTA exports, primers, and validation artifacts. `SynthesisHandoff` prepares order-ready files for the selected provider.

## Operating Notes

Development follows the phase gates in [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md). Every session starts from and ends by updating [PROGRESS.md](PROGRESS.md), and scientific uncertainty is logged for human review rather than resolved by guesswork.
