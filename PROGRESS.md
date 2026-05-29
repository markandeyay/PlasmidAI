# PROGRESS — Build State (mutable)

## AT-A-GLANCE (update every session)
- **Current Phase:** Phase 0: Foundations and Data Pipeline
- **Next Concrete Task:** Human review of the `make parse-sample N=10` output quality before scaling parser work or broadening the reference library
- **Overall completion estimate:** 5%
- **Last session date:** 2026-05-29
- **Codebase known-good?** (tests passing) Yes — `C:\Program Files (x86)\GnuWin32\bin\make.exe test` verifies Docker Compose, Postgres with pgvector, MinIO, Redis, 7 schema tests, 7 fake-backed Addgene ingestion tests, and 7 fake-backed GenBank ingestion tests

## RESUME HERE (only if mid-task)
Parser checkpoint ready for human review. `make parse-sample N=10` ran on the 10 verified real GenBank records and produced a clean report, but no records were annotation-complete yet because the current sample mostly contains CDS/marker annotations and lacks promoter/terminator labels. Resume by reviewing output quality and deciding whether to broaden the reference library/heuristics before parsing at scale.

## KNOWN ISSUES / BLOCKERS
- Phase 0 is authorized as of 2026-05-29; do not begin Phase 1 until the Phase 0 gate is met and reviewed.
- The GNU Make directory was added to the user PATH on 2026-05-29, but the current Codex host process has not inherited that PATH refresh. Use `C:\Program Files (x86)\GnuWin32\bin\make.exe` directly in this process if plain `make` is still unresolved; new user shells should pick up the user PATH.
- Addgene dev-mode ingestion is blocked pending Addgene partner-program response on API access, terms, and commercial licensing. This is not a quick local credential/config unblock; keep the existing ingester parked until the partner access path is resolved.
- Local gitignored `.env` uses `POSTGRES_PORT=55432` because a native Windows `postgres` process owns port `5432`; committed Docker defaults still use local-dev defaults and were not changed.
- NCBI GenBank dev-mode ingestion is verified on 10 real records after excluding `CON` division constructed records and adding post-fetch ORIGIN validation.

## QUESTIONS FOR THE HUMAN
- Which synthesis provider profile should be the default for "synthesis-ready" when no provider is selected: conservative cross-provider, Twist, IDT, GenScript, or user-selected only?
- Should the first product only score codon usage, or may it automatically rewrite coding sequences after explicit user consent?
- For commercial use, can Addgene-derived records be used for model training under the eventual approved data access license, or only for retrieval/display?
- Should GenBank-derived records be treated as commercially trainable by default, or should submitter-IP caveats require legal review before training?
- Should Evo 2 7B be the first generation candidate, with Carbon-3B as fallback, pending infrastructure and license review?
- Should the platform operate as a regulated-like biosecurity checkpoint before provider handoff, even where direct legal duties attach primarily to synthesis providers or procurement?
- What is the current controlling U.S. nucleic-acid screening framework after the May 5, 2025 Executive Order directive to revise or replace the 2024 framework?
- For circular plasmids, where should canonical base 1 be placed in generated designs: source record origin, ORI start, MCS/cloning site, or synthesis-provider convention?
- Should the MVP map be read-only, or should browser-side feature/sequence editing be in scope?
- Which vector types are in the first supported validity profile set: generic mammalian expression, lentiviral, AAV, bacterial expression, CRISPR/shRNA, or another subset?

## PHASE GATE STATUS
- [x] Phase R gate met (see SYSTEM_DESIGN 3.05) — artifacts reviewed and Phase 0 authorized by the human on 2026-05-29
- [ ] Phase 0 gate met (see SYSTEM_DESIGN 3.1)
- [ ] Phase 1 gate met
- [ ] Phase 2 gate met
- [ ] Phase 3 gate met
- [ ] Phase 4 gate met
- [ ] Phase 5 gate met

## MASTER CHECKLIST MIRROR

### 3.05 Phase R — Research & knowledge acquisition

- [x] Research workspace created at `research/` with the structure in Section 4.5
- [x] Subagents dispatched across all research tracks (Section 4.5.3) and their findings written to `research/findings/`
- [x] Plasmid biology synthesized into `research/findings/plasmid_biology.md` (structure, components, design rules)
- [x] Sequence-generation landscape synthesized into `research/findings/sequence_models.md` (DNABERT-2, Nucleotide Transformer, Evo, GenSLM, etc., with licenses)
- [x] Existing tools & prior art synthesized into `research/findings/prior_art.md` (OriGen, PlasmidGPT, Benchling, SnapGene, VectorBuilder, etc.)
- [x] Data sources synthesized into `research/findings/data_sources.md` (Addgene, NCBI, access methods, licensing, formats)
- [x] Validation/constraint rules synthesized into `research/findings/design_rules.md` (restriction sites, codon optimization, regulatory compatibility)
- [x] Visualization approaches synthesized into `research/findings/visualization.md` (seqviz, circular/linear map rendering)
- [x] An annotated bibliography (`research/bibliography.md`) lists every paper/source read, with a one-line takeaway and citation
- [x] A consolidated `research/SYNTHESIS.md` distills everything into the decisions that affect the build, with open questions flagged for the human
- [x] **GATE:** Every research track has a findings file with cited sources; `research/SYNTHESIS.md` exists and explicitly answers the "questions the build needs answered" list (Section 4.5.2); any unresolved biological questions are logged under "Questions for the human" in `PROGRESS.md`. Human reviewed Phase R and authorized Phase 0 on 2026-05-29.

### 3.1 Phase 0 — Foundations & data pipeline

- [x] Monorepo scaffolded with the structure in Section 4.2
- [x] Local dev environment reproducible (`make setup` brings up Postgres + object store + vector DB locally via Docker Compose)
- [ ] CI runs lint + tests on every commit
- [ ] Addgene ingestion job pulls plasmid metadata + sequences into the canonical `plasmids` table (Section 12.1)
- [x] NCBI GenBank ingestion job pulls plasmid-annotated sequences
- [ ] Literature/context extraction job populates the `experimental_contexts` table (Section 12.2)
- [ ] Sequence parser normalizes every sequence into canonical annotated form (Section 12.3) with component detection (ORI, promoter, GOI, marker, MCS, terminator)
- [ ] Data quality report job produces counts, null-rates, and dedup stats
- [ ] **GATE:** ≥ 50,000 fully-parsed, component-annotated plasmid records exist in the database and pass schema validation; a single CLI command reproduces the whole pipeline from empty DB.

### 3.2 Phase 1 — Retrieval layer (MVP)

- [ ] Embedding service wraps a biomedical encoder (Section 6.2) behind the `Embedder` interface
- [ ] Every plasmid record embedded and indexed in the vector DB
- [ ] NLU parser converts free-text experimental goals into the structured `DesignSpec` (Section 12.4) via an LLM behind the `IntentParser` interface
- [ ] Retrieval service returns top-K relevant plasmids for a `DesignSpec`, with hybrid (semantic + structured-filter) search
- [ ] Recommendation generator produces a plain-English, ranked explanation of how to adapt each retrieved plasmid
- [ ] Evaluation harness measures retrieval quality against a hand-labeled gold set (Section 6.6)
- [ ] **GATE:** Given 20 realistic natural-language queries, the system returns relevant plasmids with a top-5 hit rate ≥ 80% on the gold set, end-to-end, via a single function call.

### 3.3 Phase 2 — Sequence generation

- [ ] Base DNA language model selected and loaded behind the `SequenceGenerator` interface (Section 7.2)
- [ ] Training data formatter produces (context, template, target) examples from Phase 0 data (Section 7.3)
- [ ] Fine-tuning pipeline runs on managed GPUs and checkpoints to object storage
- [ ] Inference service generates a candidate full-length plasmid sequence from a `DesignSpec` + retrieved templates
- [ ] Generated sequences are re-annotated by the Phase 0 parser to confirm component structure
- [ ] Generation evaluation: % of generations that are syntactically valid DNA, contain the requested components, and pass basic feasibility (Section 7.6)
- [ ] **GATE:** ≥ 70% of generations for the gold-set queries are syntactically valid, contain all requested components, and pass the Phase 3 constraint engine.

### 3.4 Phase 3 — Constraint & validation engine

- [ ] Restriction-site conflict checker
- [ ] Repeat / instability checker
- [ ] Codon optimization scorer for the target organism
- [ ] Regulatory-element compatibility checker (promoter/host, marker presence, ORI/host)
- [ ] Optional therapeutic-compliance checks (flagged, not blocking, for gene-therapy contexts)
- [ ] Validation report object (Section 12.5) with PASS / WARN / FAIL per check and actionable messages
- [ ] Engine runs deterministically and is unit-tested against known-good and known-bad constructs
- [ ] **GATE:** Engine correctly classifies a curated set of ≥ 50 known-good and ≥ 50 known-bad constructs with ≥ 95% accuracy.

### 3.5 Phase 4 — Application layer

- [ ] FastAPI backend exposes the API contract in Section 13
- [ ] Session + conversation persistence (refinement loop) works end-to-end
- [ ] Plasmid map visualizer renders circular + linear maps in the frontend (Section 9.4)
- [ ] Chat-style iterative design UI (describe → design → refine → validate)
- [ ] Export to GenBank / FASTA and primer-design output
- [ ] Synthesis-order handoff (file generation + provider redirect/stub) (Section 9.6)
- [ ] AuthN/AuthZ, rate limiting, usage metering
- [ ] **GATE:** A new user can sign up, type a goal in plain English, receive a validated design with a rendered map, refine it conversationally, and export synthesis-ready files — all through the deployed UI.

### 3.6 Phase 5 — Feedback flywheel

- [ ] Outcome-capture flow (did the construct validate? sequencing + expression data) (Section 10.2)
- [ ] Outcome data stored as labeled training signal
- [ ] Scheduled re-training / fine-tuning pipeline consumes new outcomes
- [ ] Model registry + versioning + safe rollout (shadow → canary → full) (Section 10.4)
- [ ] Offline eval gate prevents regressions before any model promotion
- [ ] **GATE:** A full loop runs automatically — a captured outcome flows into the next scheduled fine-tune, the new model is evaluated offline, and is promoted only if it beats the incumbent on the eval set.

## BUILD LOG (append-only, newest at top)
- 2026-05-29 — Ran `make parse-sample N=10` on the 10 verified real GenBank records. Report: 10 records parsed, 126 high-confidence features, `annotation_complete=0/10`; detected mostly GOI/CDS and marker annotations, with one ORI and no promoter/terminator calls in this sample.
- 2026-05-29 — Confirmed `make test` passes after parser sample work: 25 tests pass plus Docker service connectivity checks.
- 2026-05-29 — Implemented the Phase 0 sequence parser/component detector with trusted GenBank annotation normalization, reference-component matching, conservative MCS motif detection, a versioned seed component library, pUC19 fixture tests with coordinate assertions, and a `make parse-sample N=10` target. Unit tests pass.
- 2026-05-29 — Refined the GenBank query to require genomic GenBank plasmid records while excluding `CON`, WGS, and TSA records; added post-fetch validation that rejects cached GenBank blobs without concrete ORIGIN sequence content before upsert.
- 2026-05-29 — Verified real `make ingest-genbank MODE=dev N=10` after query refinement: 10 records seen, 10 records upserted, 10 raw blobs in MinIO under `raw/genbank/`, and latest `ingestion_runs` row `genbank,dev,10,10,0`.
- 2026-05-29 — Diagnosed the failed GenBank dev run: 9 failing cached records were `CON` division constructed records with plasmid LOCUS/DEFINITION text and `CONTIG join(...)` pointers but no concrete `ORIGIN` sequence; the single successful record had a normal `ORIGIN` block.
- 2026-05-29 — Resolved the local Postgres auth mismatch: `docker-compose.yml` and `.env` credentials matched, but a native Windows `postgres` process owned host port 5432; updated gitignored `.env` to map Docker Postgres to host port 55432 and confirmed `make test` plus direct `psycopg` connectivity pass.
- 2026-05-29 — Ran real `make ingest-genbank MODE=dev N=10`; the job reached NCBI and cached 10 raw GenBank blobs in MinIO, but failed verification because only 1 record upserted and 9 records reported undefined sequence content. Latest `ingestion_runs` row: source `genbank`, mode `dev`, records_seen `10`, records_upserted `1`, errors `9`.
- 2026-05-29 — Updated gitignored local `.env` with the real NCBI contact email and confirmed no tracked file changed.
- 2026-05-29 — Attempted `make ingest-genbank MODE=dev N=10`; it failed before any NCBI network request because `psycopg` could not authenticate to local Postgres using the configured `DATABASE_URL`.
- 2026-05-29 — Built the NCBI GenBank ingestion job at `packages/data_pipeline/ingest/genbank.py` with Entrez/SeqIO, cache-first raw GenBank text storage under `raw/genbank/<accession>.gb`, NCBI-aware rate limits, exponential backoff, idempotent Postgres upserts, `ingestion_runs` logging, dev/bulk/refresh modes, and a `make ingest-genbank MODE=dev N=10` entrypoint.
- 2026-05-29 — Added fake-backed GenBank tests and fixture records covering minimal annotations, rich annotations, multiple feature types, unusual organism, short/long sequences, cache-before-network behavior, and idempotent upserts.
- 2026-05-29 — Attempted real NCBI dev mode for 10 records; blocked before network access because `.env` still has placeholder `NCBI_EMAIL=researcher@example.com`.
- 2026-05-29 — Pivoted Phase 0 ingestion work from Addgene to NCBI GenBank because Addgene API access requires partner-program approval; re-read `PROGRESS.md`, SYSTEM_DESIGN Section 5.2, and the NCBI portions of `research/findings/data_sources.md`; confirmed `make test` passes before coding.
- 2026-05-29 — Built the Addgene ingestion job at `packages/data_pipeline/ingest/addgene.py` with cache-first raw JSON storage under `raw/addgene/<id>.json`, conservative rate limiting/backoff, idempotent Postgres upserts, `ingestion_runs` logging, dev/bulk/refresh modes, and a `make ingest-addgene MODE=dev N=10` entrypoint.
- 2026-05-29 — Added fake-backed Addgene tests and fixture blobs covering minimal metadata, missing sequence, multiple markers/promoters, unusual organism, cache-before-network behavior, idempotent upsert behavior, and structured mapping-error logging.
- 2026-05-29 — Attempted real Addgene dev mode for 10 records; blocked before network access because approved Addgene credentials and explicit data-license acceptance are not configured in `.env`.
- 2026-05-29 — Started the Addgene ingestion session: re-read `PROGRESS.md`, SYSTEM_DESIGN Section 5.2, and `research/findings/data_sources.md`; confirmed the existing `make test` target passes before coding.
- 2026-05-29 — Completed Phase 0 milestone 2: defined canonical Pydantic schemas for `Plasmid`, `ExperimentalContext`, `AnnotatedSequence`, `DesignSpec`, `ValidationReport`, and supporting types; added representative schema tests; confirmed `make test` passes.
- 2026-05-29 — Completed Phase 0 milestone 1: added Docker Compose services for Postgres/pgvector, MinIO, and Redis; wired `make setup` to create `.env` and start the stack; wired `make test` to verify connectivity to each service; confirmed the stack is running locally.
- 2026-05-29 — Completed the Phase 0 startup ritual: re-read the Phase 0/system schema specs, re-read the Phase R data-source and plasmid-biology findings, confirmed the current stub `make test` target passes, and moved the active phase to Phase 0.
- 2026-05-29 — Generated consolidated Phase R report source at `research/phase_r_report.tex` from existing `research/findings/`, `research/SYNTHESIS.md`, `research/bibliography.md`, and `PROGRESS.md` questions without modifying the source research files.
- 2026-05-29 — Compiled `research/phase_r_report.pdf` with `pdflatex` run twice; transient LaTeX aux/out/toc artifacts were removed.
- 2026-05-29 — Installed GNU Make via winget (`GnuWin32.Make`), added it to the user PATH, and confirmed the installed GNU Make executable passes the current stub `test` target. Machine PATH update was denied by Windows registry permissions.
- 2026-05-24 — Completed Phase R research tracks A-J in `research/findings/`: plasmid biology, design rules, sequence models, prior art, data sources, representation, validation tooling, visualization, architecture patterns, and biosecurity.
- 2026-05-24 — Wrote `research/SYNTHESIS.md` answering all SYSTEM_DESIGN Section 4.5.2 questions and recording build decisions.
- 2026-05-24 — Wrote `research/bibliography.md` with an annotated source list grouped by research track.
- 2026-05-24 — Logged Phase R human-review questions and stopped before Phase 0.
- 2026-05-24 — Created initial monorepo skeleton directories under `packages/`, `services/`, `apps/`, `research/`, `tests/`, and `infra/`; added `.gitignore`, `.env.example`, and stub `Makefile`.
- 2026-05-24 — Attempted `make test`; blocked because `make` is not installed in the current shell.
- 2026-05-24 — Created PROGRESS.md from SYSTEM_DESIGN Section 1 and mirrored the Section 3 checklist.
