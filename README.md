# PlasmidAI

PlasmidAI is an AI-assisted plasmid design platform. A researcher describes an experimental goal in plain English, and the system is intended to produce a complete, annotated, synthesis-ready plasmid design: DNA sequence, labeled component map, validation report, primer designs, and export files for synthesis handoff.

## Project Status

The consolidated `master` baseline is known-good at **305+ tests**. Phase 1 retrieval and Phase 3 validation have met their gates. Phase 4 API and frontend foundations are implemented, but the Phase 4 gate is still open because deployed sign-up/auth, full synthesis-ready export, primer design, and synthesis handoff are not complete. Phase 5 foundation work is in progress on a separate Codex branch and is not gated.

See [PROGRESS.md](PROGRESS.md) for the authoritative real-time build state and open questions.

## Phase Status

- **Phase R - Research:** gate met; research findings and synthesis are under [`research/`](research/).
- **Phase 0 - Foundations and data pipeline:** core schemas, local services, NCBI/curated ingestion, parser, reprocess, and data-quality reports are in place. Gate is **not met**: corpus scale remains far below 50,000 fully parsed component-annotated plasmids, Addgene access is pending, and literature/context extraction is incomplete.
- **Phase 1 - Retrieval MVP:** gate met. The retrieval layer includes intent parsing, embeddings, hybrid structured/vector retrieval, recommendations, and evaluation. Latest robustness baseline reports top-5 `1.000` with clarification pass rate `1.000`.
- **Phase 2 - Sequence generation:** scaffolding and real-model plumbing exist, including training-data formatting, deterministic fake generation, Carbon-500M CPU spike support, generation evaluation, model registry, and fine-tuning prep. Gate is **not met**: there is no authorized fine-tune, no GPU benchmark, and no biological validation of generated sequences.
- **Phase 3 - Constraint and validation:** gate met under the approved curated-quality policy. The deterministic engine covers restriction sites, repeats/instability, codon usage, regulatory compatibility, and validation reports; curated baseline accuracy is `1.000` on 31 known-good plus 52 known-bad records.
- **Phase 4 - Application layer:** FastAPI backend, session/refinement/job persistence, export codecs, OpenAPI docs, Next.js frontend, chat workflow, and seqviz maps are implemented. Gate is **not met**: auth, deployment, primer-design output, complete synthesis handoff, and production readiness remain open.
- **Phase 5 - Feedback flywheel:** foundation work is in progress in Codex's separate branch. Gate is **not met**: automated outcome capture, retraining, offline promotion, and safe rollout are not complete.

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
- Export codecs and application-layer design artifacts currently live under [`packages/application/`](packages/application/) and `services/api/`; a separate assembly package has not landed yet.
- Phase 5 feedback-flywheel implementation is in progress on a separate Codex branch and is not part of the current `master` package set.
- [`services/api/`](services/api/) - FastAPI application, API stores, jobs, and export endpoints.
- [`apps/web/`](apps/web/) - Phase 4 Next.js design workspace with chat and plasmid-map UI.

## Architecture

The system is layered around explicit interfaces. The `IntentParser` converts plain-English goals into a structured design specification. The `Retriever` searches the indexed plasmid corpus using hybrid semantic and structured filters. The `SequenceGenerator` interface supports deterministic fake generation and real-model plumbing, but production generation remains gated. The Phase 3 `ConstraintEngine` deterministically validates biological and synthesis constraints. The application layer exposes this flow through FastAPI and a Next.js frontend, with persisted sessions, turns, jobs, designs, and export artifacts.

Local infrastructure uses Docker Compose for Postgres with pgvector, Redis, and object storage. Python packages share canonical schemas through `packages/core`, while the web app is a separate npm workspace under `apps/web`.

## Contributor Worktrees

Multiple agents may work in parallel from separate worktrees. Use the path assigned in the prompt and do not switch branches inside another agent's worktree.

- Codex main worktree: `C:\Users\yalam\PMR`
- OpenCode auxiliary worktree: `C:\Users\yalam\PMR-opencode`

The OpenCode worktree may use a gitignored `.env` with alternate service ports so its Docker Compose stack can run beside the main worktree. Keep worktree-local `.env` files uncommitted.

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

If plain `make` is unavailable in the current shell on Windows, use `C:\Program Files (x86)\GnuWin32\bin\make.exe`.

NCBI requires a real contact email for Entrez requests. `NCBI_API_KEY` is optional and increases the supported request rate. Bulk Addgene access is pending partner-program approval and commercial licensing review; do not add credentials or enable it unless that approval is in place.

## Run Commands

Common root commands:

```bash
make setup
make test
make quality-report
make eval-retrieval
make validate-sample MODE=gold
make serve-api
```

Run a retrieval-only design query:

```bash
make design MODE=offline TEXT="I need a yeast centromere shuttle plasmid selected by URA3."
```

Run the web app:

```bash
cd apps/web
npm ci
npm run dev
```

The API defaults to `http://127.0.0.1:8000`; the web app defaults to `http://127.0.0.1:3000`. Set `NEXT_PUBLIC_API_URL` if the frontend should target a different API URL.

For frontend verification, run `npm run build` and `npm run test:e2e` sequentially because both use `.next`.

## Current Flow

The `IntentParser` converts a plain-English research goal into a structured design specification. The `Retriever` finds relevant real plasmids and templates from the indexed corpus. The `SequenceGenerator` proposes candidate plasmid sequences from the specification and retrieved templates. The deterministic `ConstraintEngine` validates biological structure and synthesis constraints. The application layer persists sessions, jobs, and design artifacts, and the current export codecs produce GenBank/FASTA payloads. Primer output and synthesis-provider handoff remain future Phase 4/5 work.

## Operating Notes

Development follows the phase gates in [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md). `PROGRESS.md` is the authoritative mutable state file for current branch state, blockers, and gate decisions. Scientific uncertainty is logged for human review rather than resolved by guesswork.
