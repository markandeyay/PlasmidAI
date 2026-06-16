# PlasmidAI

PlasmidAI is a research prototype for AI-assisted plasmid design: a user describes an experimental goal, the system retrieves relevant public/curated plasmid templates, produces or simulates a candidate design through the current generation interface, validates it with deterministic biological checks, renders an annotated map, exports GenBank/FASTA, and captures lab outcome feedback for future training signals.

## Current Status

`PROGRESS.md` is the authoritative live state file. At the current consolidated baseline, local verification passes:

- `make test`: 342 passed, 1 skipped, 8 warnings
- `npm run build` in `apps/web`: passing
- `npm run test:e2e` in `apps/web`: 3 passed
- `make e2e-test`: 1 API-backed Playwright fixture passed

Current capabilities:

- Local Docker Compose services for Postgres/pgvector, Redis, and object storage.
- NCBI/curated plasmid ingestion, parsing, reprocessing, and quality reports.
- Hybrid retrieval from indexed plasmid records with evaluation reports.
- Deterministic validation for restriction sites, repeats/instability, codon usage, and regulatory compatibility.
- FastAPI sessions, jobs, design/refine flow, export endpoints, outcome endpoints, rate limiting, and structured errors.
- Next.js design workspace with chat/refine flow, seqviz map, validation/retrieval evidence, export controls, outcome prompts, local outcome history, and visual/accessibility/loading polish.
- Phase 2 scaffolding: fake generation, Carbon-500M CPU plumbing, training-data formatting, registry, shadow comparison, rollout policy evaluation, and fake-backed canary support.
- Phase 5 foundation: outcome capture, consent-gated training-signal derivation, and feedback-flywheel documentation.

## Phase Status

| Phase | Status | Notes |
| --- | --- | --- |
| Phase R - Research | Gate met | Findings and synthesis are under `research/`. |
| Phase 0 - Data foundation | Foundation built, gate open | Corpus is 256 records with 141 complete annotations, far below the formal 50,000-record gate. Addgene/legal access and literature/context extraction remain open. |
| Phase 1 - Retrieval MVP | Gate met | Retrieval robustness baseline reached top-5 `1.000` and clarification pass `1.000`. |
| Phase 2 - Sequence generation | Scaffolded, gate open | Real Carbon-3B fine-tuning and biological validation are deferred pending cloud account setup and explicit spend authorization. |
| Phase 3 - Validation | Gate met | Curated baseline is 31 known-good plus 52 known-bad records with accuracy `1.000`. |
| Phase 4 - Application | Local foundation built, gate open | API and frontend work locally; production auth, deployment, primer design, complete synthesis handoff, and product hardening remain deferred. |
| Phase 5 - Feedback flywheel | Foundation built, gate open | Outcome capture and training-signal derivation exist; scheduled retraining and automatic model promotion do not. |

## Getting Started

Prerequisites: Git, Python, Docker Compose, Node/npm, and GNU Make.

```bash
git clone https://github.com/markandeyay/PlasmidAI.git
cd PlasmidAI
cp .env.example .env
# Set NCBI_EMAIL in .env before using NCBI Entrez ingestion.
make setup
make test
```

On PowerShell, use `Copy-Item .env.example .env` instead of `cp` if needed. If plain `make` is unavailable on Windows, use `C:\Program Files (x86)\GnuWin32\bin\make.exe`.

NCBI requires a real contact email for Entrez requests. `NCBI_API_KEY` is optional. Addgene credentials should not be added unless partner-program access and commercial-use terms are approved.

## Demo And Verification

Run the deterministic API-backed demo fixture:

```bash
make demo
```

`make demo` currently aliases `make e2e-test`, which runs the full-stack Playwright fixture against the API-backed deterministic path. This is the reliable demo check today. A live external demo using real queued design jobs still needs a worker, fake queue path, seeded completed result, or explicit demo runner decision.

Useful commands:

```bash
make setup
make test
make quality-report
make eval-retrieval
make validate-sample MODE=gold
make shadow-eval
make e2e-test
make serve-api
make serve-web
```

Run a retrieval-only query:

```bash
make design MODE=offline TEXT="I need a yeast centromere shuttle plasmid selected by URA3."
```

Run frontend checks sequentially because Next build output and Playwright dev server both use `.next`:

```bash
cd apps/web
npm ci
npm run build
npm run test:e2e
```

The API defaults to `http://127.0.0.1:8000`; the web app defaults to `http://127.0.0.1:3000`. Set `NEXT_PUBLIC_API_URL` if the frontend should target a different API URL.

## Architecture Summary

The system follows the phase-gated design in `SYSTEM_DESIGN.md`:

- `packages/core/`: shared Pydantic schemas and canonical contracts.
- `packages/data_pipeline/`: ingestion, parsing, annotation, reprocessing, and corpus-quality jobs.
- `packages/retrieval/`: intent parsing, embeddings, vector/structured retrieval, recommendation, and retrieval evaluation.
- `packages/generation/`: sequence-generation interface, fake generator, Carbon CPU plumbing, training-data formatting, fine-tuning smoke path, registry, shadow, canary, and rollout evaluation.
- `packages/validation/`: deterministic biological and synthesis constraint checks.
- `packages/application/`: application-layer services and export codecs.
- `packages/feedback/`: outcome-to-training-signal derivation.
- `services/api/`: FastAPI application, stores, jobs, design/refine/export/outcome endpoints, and API safeguards.
- `apps/web/`: Next.js design workspace and Playwright tests.

`SYSTEM_DESIGN.md` is the original build specification. `PROGRESS.md` is the mutable state file and should be treated as the source of truth for what is actually done, deferred, blocked, or pending human review. Known drift between the two is tracked in `research/findings/system_design_drift.md`.

## Contributor Notes

Two files keep long-running work aligned:

- `SYSTEM_DESIGN.md`: original architecture and phase-gate contract.
- `PROGRESS.md`: current state, verification, blockers, deferred work, and pending decisions.

Multiple agents may use separate worktrees. Use the path assigned in the prompt and do not switch branches in another agent's worktree.

- Codex main worktree: `C:\Users\yalam\PMR`
- OpenCode auxiliary worktree: `C:\Users\yalam\PMR-opencode`

Worktree-local `.env` files may use alternate service ports so Docker Compose stacks can coexist. Keep `.env` uncommitted.

## Known Limitations And Deferred Work

- The corpus is small and does not meet the formal Phase 0 scale gate.
- Addgene and other non-NCBI source use remain blocked on licensing/provenance decisions.
- Phase 2 real fine-tuning has not run; no generated sequence quality claim is made.
- Carbon-500M support is CPU plumbing only, not a validated design model.
- Production auth, authorization, usage metering, deployment, primer design, and synthesis-provider handoff are not complete.
- Full Phase 5 automation is not active: outcomes do not yet trigger scheduled fine-tuning and model promotion.
- Dependency vulnerabilities are documented in `data/audits/dependencies_2026-06-13.md`; upgrades are deferred to a dedicated review branch.
- `SYSTEM_DESIGN.md` has documented drift and should not be edited without explicit human authorization.

For current review state, pending human decisions, and the latest verification results, read `PROGRESS.md` first.
