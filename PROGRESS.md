# PROGRESS â€” Build State (mutable)

## AT-A-GLANCE (update every session)
- **Current Phase:** Phase 0: Foundations and Data Pipeline
- **Next Concrete Task:** Create and run the Phase 0 data quality report job after publishing the private GitHub backup and project README.
- **Overall completion estimate:** 5%
- **Last session date:** 2026-05-29
- **Codebase known-good?** (tests passing) Yes - `C:\Program Files (x86)\GnuWin32\bin\make.exe test` verifies Docker Compose, Postgres with pgvector, MinIO, Redis, 7 schema tests, 7 fake-backed Addgene ingestion tests, 8 fake-backed GenBank ingestion tests, 13 vector-classifier tests, and 3 parser tests

## RESUME HERE (only if mid-task)
RESUME HERE: pACYC184 will remain incomplete until an exact CAT CDS source is approved; do not import the broad NCBI/NEB chloramphenicol-resistance region. Profile-aware completeness remains verified at `annotation_complete=11/12` on the curated sample. Current session is publishing the private GitHub backup and README, then building the Phase 0 quality report job. Do not bulk-parse yet.

## KNOWN ISSUES / BLOCKERS
- Phase 0 is authorized as of 2026-05-29; do not begin Phase 1 until the Phase 0 gate is met and reviewed.
- The GNU Make directory was added to the user PATH on 2026-05-29, but the current Codex host process has not inherited that PATH refresh. Use `C:\Program Files (x86)\GnuWin32\bin\make.exe` directly in this process if plain `make` is still unresolved; new user shells should pick up the user PATH.
- Addgene dev-mode ingestion is blocked pending Addgene partner-program response on API access, terms, and commercial licensing. This is not a quick local credential/config unblock; keep the existing ingester parked until the partner access path is resolved.
- Local gitignored `.env` uses `POSTGRES_PORT=55432` because a native Windows `postgres` process owns port `5432`; committed Docker defaults still use local-dev defaults and were not changed.
- NCBI GenBank dev-mode ingestion is verified on 10 real records after excluding `CON` division constructed records and adding post-fetch ORIGIN validation.
- Parser N=50 sample remains structurally sparse for Phase 0 completeness: the current GenBank query returns complete natural plasmids with many CDS/marker annotations but almost no source-labeled or reference-matched synthetic regulatory elements.
- Profile-aware curated seed sample is substantially improved: 12 NCBI-backed seed records loaded; `annotation_complete=11/12`; profile breakdown `bacterial_cloning_vector:5/6`, `bacterial_expression_vector:1/1`, `mammalian_reporter_vector:3/3`, `yeast_shuttle_vector:2/2`; report saved at `data/eval/parser/2026-05-29-223417-profile-aware-curated-sample.txt`.

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
- Should the GenBank corpus strategy shift from broad natural plasmid complete sequences toward named synthetic vectors/backbones, or should Phase 0 depend on Addgene/another vector-specific source for promoter/terminator-rich records?
- Which exact canonical variants should be approved for ambiguous elements not yet added to the reference library: EF1a, SV40 early, U6, tac, trc, araBAD, SV40 polyA, BGH polyA, rabbit beta-globin polyA, rrnB T1/T2, lambda T0, ZeoR, BSD, HygR, NeoR/G418, f1 origin, and 2-micron origin?
- Pending legal/provenance approval, may Addgene Vector Database free-to-view sequences be used for a small parser-calibration seed set in a commercial product, or should the seed set remain NCBI/manufacturer-only until explicit partner terms are in place?

## PHASE GATE STATUS
- [x] Phase R gate met (see SYSTEM_DESIGN 3.05) â€” artifacts reviewed and Phase 0 authorized by the human on 2026-05-29
- [ ] Phase 0 gate met (see SYSTEM_DESIGN 3.1)
- [ ] Phase 1 gate met
- [ ] Phase 2 gate met
- [ ] Phase 3 gate met
- [ ] Phase 4 gate met
- [ ] Phase 5 gate met

## MASTER CHECKLIST MIRROR

### 3.05 Phase R â€” Research & knowledge acquisition

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

### 3.1 Phase 0 â€” Foundations & data pipeline

- [x] Monorepo scaffolded with the structure in Section 4.2
- [x] Local dev environment reproducible (`make setup` brings up Postgres + object store + vector DB locally via Docker Compose)
- [ ] CI runs lint + tests on every commit
- [ ] Addgene ingestion job pulls plasmid metadata + sequences into the canonical `plasmids` table (Section 12.1)
- [x] NCBI GenBank ingestion job pulls plasmid-annotated sequences
- [ ] Literature/context extraction job populates the `experimental_contexts` table (Section 12.2)
- [ ] Sequence parser normalizes every sequence into canonical annotated form (Section 12.3) with component detection (ORI, promoter, GOI, marker, MCS, terminator)
- [ ] Data quality report job produces counts, null-rates, and dedup stats
- [ ] **GATE:** â‰¥ 50,000 fully-parsed, component-annotated plasmid records exist in the database and pass schema validation; a single CLI command reproduces the whole pipeline from empty DB.

### 3.2 Phase 1 â€” Retrieval layer (MVP)

- [ ] Embedding service wraps a biomedical encoder (Section 6.2) behind the `Embedder` interface
- [ ] Every plasmid record embedded and indexed in the vector DB
- [ ] NLU parser converts free-text experimental goals into the structured `DesignSpec` (Section 12.4) via an LLM behind the `IntentParser` interface
- [ ] Retrieval service returns top-K relevant plasmids for a `DesignSpec`, with hybrid (semantic + structured-filter) search
- [ ] Recommendation generator produces a plain-English, ranked explanation of how to adapt each retrieved plasmid
- [ ] Evaluation harness measures retrieval quality against a hand-labeled gold set (Section 6.6)
- [ ] **GATE:** Given 20 realistic natural-language queries, the system returns relevant plasmids with a top-5 hit rate â‰¥ 80% on the gold set, end-to-end, via a single function call.

### 3.3 Phase 2 â€” Sequence generation

- [ ] Base DNA language model selected and loaded behind the `SequenceGenerator` interface (Section 7.2)
- [ ] Training data formatter produces (context, template, target) examples from Phase 0 data (Section 7.3)
- [ ] Fine-tuning pipeline runs on managed GPUs and checkpoints to object storage
- [ ] Inference service generates a candidate full-length plasmid sequence from a `DesignSpec` + retrieved templates
- [ ] Generated sequences are re-annotated by the Phase 0 parser to confirm component structure
- [ ] Generation evaluation: % of generations that are syntactically valid DNA, contain the requested components, and pass basic feasibility (Section 7.6)
- [ ] **GATE:** â‰¥ 70% of generations for the gold-set queries are syntactically valid, contain all requested components, and pass the Phase 3 constraint engine.

### 3.4 Phase 3 â€” Constraint & validation engine

- [ ] Restriction-site conflict checker
- [ ] Repeat / instability checker
- [ ] Codon optimization scorer for the target organism
- [ ] Regulatory-element compatibility checker (promoter/host, marker presence, ORI/host)
- [ ] Optional therapeutic-compliance checks (flagged, not blocking, for gene-therapy contexts)
- [ ] Validation report object (Section 12.5) with PASS / WARN / FAIL per check and actionable messages
- [ ] Engine runs deterministically and is unit-tested against known-good and known-bad constructs
- [ ] **GATE:** Engine correctly classifies a curated set of â‰¥ 50 known-good and â‰¥ 50 known-bad constructs with â‰¥ 95% accuracy.

### 3.5 Phase 4 â€” Application layer

- [ ] FastAPI backend exposes the API contract in Section 13
- [ ] Session + conversation persistence (refinement loop) works end-to-end
- [ ] Plasmid map visualizer renders circular + linear maps in the frontend (Section 9.4)
- [ ] Chat-style iterative design UI (describe â†’ design â†’ refine â†’ validate)
- [ ] Export to GenBank / FASTA and primer-design output
- [ ] Synthesis-order handoff (file generation + provider redirect/stub) (Section 9.6)
- [ ] AuthN/AuthZ, rate limiting, usage metering
- [ ] **GATE:** A new user can sign up, type a goal in plain English, receive a validated design with a rendered map, refine it conversationally, and export synthesis-ready files â€” all through the deployed UI.

### 3.6 Phase 5 â€” Feedback flywheel

- [ ] Outcome-capture flow (did the construct validate? sequencing + expression data) (Section 10.2)
- [ ] Outcome data stored as labeled training signal
- [ ] Scheduled re-training / fine-tuning pipeline consumes new outcomes
- [ ] Model registry + versioning + safe rollout (shadow â†’ canary â†’ full) (Section 10.4)
- [ ] Offline eval gate prevents regressions before any model promotion
- [ ] **GATE:** A full loop runs automatically â€” a captured outcome flows into the next scheduled fine-tune, the new model is evaluated offline, and is promoted only if it beats the incumbent on the eval set.

## BUILD LOG (append-only, newest at top)
- 2026-05-30 - Human decided pACYC184 must remain incomplete until an exact CAT CDS source is approved. Do not import the broad NCBI/NEB chloramphenicol-resistance region under uncertainty.
- 2026-05-29 - Replaced universal parser completeness with vector-profile-aware completeness. Added `packages/data_pipeline/parse/vector_profiles.yaml`, `AnnotatedSequence.vector_profile`, a deterministic rule-cascade classifier, classifier tests for the 12 curated seed vectors, and parser wiring that evaluates completeness per profile.
- 2026-05-29 - Expanded the parser reference library with NCBI-backed profile-specific elements from curated seed records: p15A origin, Tet marker, f1 origin, NeoR/KanR, EGFP, luc+/luc2, SV40 late polyA, pGL3 MCS, tac promoter, GST, and ARSH4; deferred gated or ambiguous viral/CRISPR/U6/PuroR/yeast-expression elements.
- 2026-05-29 - Ran `make parse-sample N=12 SOURCE=curated` after profile-aware completeness. Result: `annotation_complete=11/12`; pACYC184 remains incomplete pending a precise second-marker reference; report saved at `data/eval/parser/2026-05-29-223417-profile-aware-curated-sample.txt`.
- 2026-05-29 - Updated `research/findings/plasmid_biology.md` to document vector-type taxonomy and the rationale for profile-aware completeness.
- 2026-05-29 - Added an NCBI-only curated seed manifest after provenance review excluded Addgene-only/login-gated/ambiguous sequence sources pending explicit commercial-use approval.
- 2026-05-29 - Built `packages/data_pipeline/ingest/curated_seed.py`, wired `make ingest-curated`, added fake-backed curated ingestion tests, and extended `parse-sample` with `SOURCE=curated`.
- 2026-05-29 - Refined the default GenBank query to bias toward engineered vector titles rather than broad natural complete plasmids.
- 2026-05-29 - Ran `make ingest-curated`: 12 curated seed records seen, 12 upserted, no errors; raw GenBank blobs cached under `raw/curated/`.
- 2026-05-29 - Ran `make parse-sample N=50 SOURCE=curated`: 12 records parsed, promoter/MCS/ORI/marker/terminator annotations present, but `annotation_complete=0/12`; report saved at `data/eval/parser/2026-05-29-curated-seed-sample.txt`.
- 2026-05-29 â€” Expanded the parser reference library with provenance-backed CMV, CAG, PGK, H1, T7, T3, and SP6 promoter references plus a T7 terminator reference; left ambiguous element variants out rather than guessing.
- 2026-05-29 â€” Tuned Tier 2 reference matching thresholds to 85% identity over 70% reference coverage, then added k-mer seeded local alignment so parser samples remain fast after the reference library expansion.
- 2026-05-29 â€” Ran `make ingest-genbank MODE=dev N=50`: 50 records seen, 50 records upserted, no errors.
- 2026-05-29 â€” Ran `make parse-sample N=50` after reference expansion and threshold tuning. Report: 50 records parsed, 670 high-confidence features, `annotation_complete=0/50`; detected almost entirely GOI/CDS and marker features, one ORI, and no promoter/terminator calls. This points to current GenBank corpus shape rather than parser execution failure.
- 2026-05-29 â€” Ran `make parse-sample N=10` on the 10 verified real GenBank records. Report: 10 records parsed, 126 high-confidence features, `annotation_complete=0/10`; detected mostly GOI/CDS and marker annotations, with one ORI and no promoter/terminator calls in this sample.
- 2026-05-29 â€” Confirmed `make test` passes after parser sample work: 25 tests pass plus Docker service connectivity checks.
- 2026-05-29 â€” Implemented the Phase 0 sequence parser/component detector with trusted GenBank annotation normalization, reference-component matching, conservative MCS motif detection, a versioned seed component library, pUC19 fixture tests with coordinate assertions, and a `make parse-sample N=10` target. Unit tests pass.
- 2026-05-29 â€” Refined the GenBank query to require genomic GenBank plasmid records while excluding `CON`, WGS, and TSA records; added post-fetch validation that rejects cached GenBank blobs without concrete ORIGIN sequence content before upsert.
- 2026-05-29 â€” Verified real `make ingest-genbank MODE=dev N=10` after query refinement: 10 records seen, 10 records upserted, 10 raw blobs in MinIO under `raw/genbank/`, and latest `ingestion_runs` row `genbank,dev,10,10,0`.
- 2026-05-29 â€” Diagnosed the failed GenBank dev run: 9 failing cached records were `CON` division constructed records with plasmid LOCUS/DEFINITION text and `CONTIG join(...)` pointers but no concrete `ORIGIN` sequence; the single successful record had a normal `ORIGIN` block.
- 2026-05-29 â€” Resolved the local Postgres auth mismatch: `docker-compose.yml` and `.env` credentials matched, but a native Windows `postgres` process owned host port 5432; updated gitignored `.env` to map Docker Postgres to host port 55432 and confirmed `make test` plus direct `psycopg` connectivity pass.
- 2026-05-29 â€” Ran real `make ingest-genbank MODE=dev N=10`; the job reached NCBI and cached 10 raw GenBank blobs in MinIO, but failed verification because only 1 record upserted and 9 records reported undefined sequence content. Latest `ingestion_runs` row: source `genbank`, mode `dev`, records_seen `10`, records_upserted `1`, errors `9`.
- 2026-05-29 â€” Updated gitignored local `.env` with the real NCBI contact email and confirmed no tracked file changed.
- 2026-05-29 â€” Attempted `make ingest-genbank MODE=dev N=10`; it failed before any NCBI network request because `psycopg` could not authenticate to local Postgres using the configured `DATABASE_URL`.
- 2026-05-29 â€” Built the NCBI GenBank ingestion job at `packages/data_pipeline/ingest/genbank.py` with Entrez/SeqIO, cache-first raw GenBank text storage under `raw/genbank/<accession>.gb`, NCBI-aware rate limits, exponential backoff, idempotent Postgres upserts, `ingestion_runs` logging, dev/bulk/refresh modes, and a `make ingest-genbank MODE=dev N=10` entrypoint.
- 2026-05-29 â€” Added fake-backed GenBank tests and fixture records covering minimal annotations, rich annotations, multiple feature types, unusual organism, short/long sequences, cache-before-network behavior, and idempotent upserts.
- 2026-05-29 â€” Attempted real NCBI dev mode for 10 records; blocked before network access because `.env` still has placeholder `NCBI_EMAIL=researcher@example.com`.
- 2026-05-29 â€” Pivoted Phase 0 ingestion work from Addgene to NCBI GenBank because Addgene API access requires partner-program approval; re-read `PROGRESS.md`, SYSTEM_DESIGN Section 5.2, and the NCBI portions of `research/findings/data_sources.md`; confirmed `make test` passes before coding.
- 2026-05-29 â€” Built the Addgene ingestion job at `packages/data_pipeline/ingest/addgene.py` with cache-first raw JSON storage under `raw/addgene/<id>.json`, conservative rate limiting/backoff, idempotent Postgres upserts, `ingestion_runs` logging, dev/bulk/refresh modes, and a `make ingest-addgene MODE=dev N=10` entrypoint.
- 2026-05-29 â€” Added fake-backed Addgene tests and fixture blobs covering minimal metadata, missing sequence, multiple markers/promoters, unusual organism, cache-before-network behavior, idempotent upsert behavior, and structured mapping-error logging.
- 2026-05-29 â€” Attempted real Addgene dev mode for 10 records; blocked before network access because approved Addgene credentials and explicit data-license acceptance are not configured in `.env`.
- 2026-05-29 â€” Started the Addgene ingestion session: re-read `PROGRESS.md`, SYSTEM_DESIGN Section 5.2, and `research/findings/data_sources.md`; confirmed the existing `make test` target passes before coding.
- 2026-05-29 â€” Completed Phase 0 milestone 2: defined canonical Pydantic schemas for `Plasmid`, `ExperimentalContext`, `AnnotatedSequence`, `DesignSpec`, `ValidationReport`, and supporting types; added representative schema tests; confirmed `make test` passes.
- 2026-05-29 â€” Completed Phase 0 milestone 1: added Docker Compose services for Postgres/pgvector, MinIO, and Redis; wired `make setup` to create `.env` and start the stack; wired `make test` to verify connectivity to each service; confirmed the stack is running locally.
- 2026-05-29 â€” Completed the Phase 0 startup ritual: re-read the Phase 0/system schema specs, re-read the Phase R data-source and plasmid-biology findings, confirmed the current stub `make test` target passes, and moved the active phase to Phase 0.
- 2026-05-29 â€” Generated consolidated Phase R report source at `research/phase_r_report.tex` from existing `research/findings/`, `research/SYNTHESIS.md`, `research/bibliography.md`, and `PROGRESS.md` questions without modifying the source research files.
- 2026-05-29 â€” Compiled `research/phase_r_report.pdf` with `pdflatex` run twice; transient LaTeX aux/out/toc artifacts were removed.
- 2026-05-29 â€” Installed GNU Make via winget (`GnuWin32.Make`), added it to the user PATH, and confirmed the installed GNU Make executable passes the current stub `test` target. Machine PATH update was denied by Windows registry permissions.
- 2026-05-24 â€” Completed Phase R research tracks A-J in `research/findings/`: plasmid biology, design rules, sequence models, prior art, data sources, representation, validation tooling, visualization, architecture patterns, and biosecurity.
- 2026-05-24 â€” Wrote `research/SYNTHESIS.md` answering all SYSTEM_DESIGN Section 4.5.2 questions and recording build decisions.
- 2026-05-24 â€” Wrote `research/bibliography.md` with an annotated source list grouped by research track.
- 2026-05-24 â€” Logged Phase R human-review questions and stopped before Phase 0.
- 2026-05-24 â€” Created initial monorepo skeleton directories under `packages/`, `services/`, `apps/`, `research/`, `tests/`, and `infra/`; added `.gitignore`, `.env.example`, and stub `Makefile`.
- 2026-05-24 â€” Attempted `make test`; blocked because `make` is not installed in the current shell.
- 2026-05-24 â€” Created PROGRESS.md from SYSTEM_DESIGN Section 1 and mirrored the Section 3 checklist.
