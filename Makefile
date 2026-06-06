.PHONY: build-training-data design embed-corpus eval-generation eval-retrieval finetune-smoke generate-validation-gold ingest-addgene ingest-all ingest-curated ingest-genbank lint parse-sample quality-report reprocess serve-api serve-web services-down setup spike-generation test validate-sample

PYTHON ?= python
MODE ?= dev
N ?=
ADDGENE_STALE_DAYS ?= 1
GENBANK_STALE_DAYS ?= 60
BATCH_SIZE ?= 100
FAKE ?= 0
TOP_K ?= 5
API_HOST ?= 127.0.0.1
API_PORT ?= 8000
EVAL_GOLD ?= data/eval/retrieval_gold.jsonl
EVAL_OUT ?= data/eval/retrieval
TRAINING_OUT ?= data/training/phase2
TRAINING_SNAPSHOT ?=
GENERATION_GOLD ?= data/eval/generation_gold.jsonl
GENERATION_OUT ?= data/eval/generation
GENERATION_TOP_K ?= 1
VALIDATION_GOLD ?= data/eval/validation/validation_gold.jsonl
VALIDATION_OUT ?= data/eval/validation
GENERATION_GENERATOR ?= fake
CARBON_MAX_NEW_TOKENS ?= 4
FINETUNE_OUTPUT ?= packages/generation/models/finetune-smoke

setup:
	$(PYTHON) -m pip install -r requirements.txt
	powershell -NoProfile -ExecutionPolicy Bypass -Command "if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }"
	docker compose up -d

test:
	$(PYTHON) scripts/check_services.py
	$(PYTHON) -m pytest

lint:
	@echo "No lint configured yet."

ingest-all:
	@echo "TODO: run all Phase 0 ingestion jobs"

ingest-addgene:
	$(PYTHON) -m packages.data_pipeline.ingest.addgene --mode $(MODE) $(if $(N),--limit $(N),) --stale-days $(ADDGENE_STALE_DAYS)

ingest-genbank:
	$(PYTHON) -m packages.data_pipeline.ingest.genbank --mode $(MODE) $(if $(N),--limit $(N),) --stale-days $(GENBANK_STALE_DAYS)

parse-sample:
	$(PYTHON) scripts/parse_sample.py $(if $(N),--limit $(N),) $(if $(SOURCE),--source $(SOURCE),)

ingest-curated:
	$(PYTHON) -m packages.data_pipeline.ingest.curated_seed

quality-report:
	$(PYTHON) -m packages.data_pipeline.quality_report

reprocess:
	$(PYTHON) -m packages.data_pipeline.reprocess --mode $(MODE) $(if $(BEFORE),--before $(BEFORE),) $(if $(SOURCE),--source $(SOURCE),) $(if $(PATTERN),--pattern $(PATTERN),) --batch-size $(BATCH_SIZE)

eval-retrieval:
	$(PYTHON) -m packages.retrieval.eval --gold-path $(EVAL_GOLD) --output-dir $(EVAL_OUT) --top-k $(TOP_K) $(if $(filter 1 true TRUE yes YES,$(FAKE)),--fake-embedder,) $(if $(filter offline OFFLINE,$(MODE)),--local-files-only,)

embed-corpus:
	$(PYTHON) -m packages.retrieval.embed_corpus --batch-size $(BATCH_SIZE) $(if $(N),--limit $(N),) $(if $(filter 1 true TRUE yes YES,$(FAKE)),--fake,) $(if $(filter offline OFFLINE,$(MODE)),--local-files-only,)

design:
	$(PYTHON) -m packages.retrieval.pipeline --text "$(TEXT)" --k $(TOP_K) $(if $(filter 1 true TRUE yes YES,$(FAKE)),--fake-embedder,) $(if $(filter offline OFFLINE,$(MODE)),--local-files-only,)

spike-generation:
	$(PYTHON) -m packages.generation.spike --text "$(TEXT)" $(if $(filter 1 true TRUE yes YES,$(FAKE)),--fake-embedder,) $(if $(filter offline OFFLINE,$(MODE)),--local-files-only,)

build-training-data:
	$(PYTHON) -m packages.generation.training_data --output-root $(TRAINING_OUT) $(if $(TRAINING_SNAPSHOT),--snapshot-id $(TRAINING_SNAPSHOT),)

eval-generation:
	$(PYTHON) -m packages.generation.eval --gold-path $(GENERATION_GOLD) --output-dir $(GENERATION_OUT) --top-k $(GENERATION_TOP_K) --generator $(GENERATION_GENERATOR) --carbon-max-new-tokens $(CARBON_MAX_NEW_TOKENS) $(if $(filter 1 true TRUE yes YES,$(FAKE)),--fake-embedder,) $(if $(filter offline OFFLINE,$(MODE)),--local-files-only,)

finetune-smoke:
	$(PYTHON) -m packages.generation.finetune --smoke --output-dir $(FINETUNE_OUTPUT) --max-train-examples 5 --max-eval-examples 2 --max-steps 1 --max-length 96

validate-sample:
	$(if $(filter gold GOLD,$(MODE)),$(PYTHON) -m packages.validation.eval --gold-path $(VALIDATION_GOLD) --output-dir $(VALIDATION_OUT),$(PYTHON) -m packages.validation.engine $(if $(N),--limit $(N),))

generate-validation-gold:
	$(PYTHON) -m packages.validation.gold --gold-path $(VALIDATION_GOLD) --doc-path $(VALIDATION_OUT)/gold_set_construction.md

serve-api:
	$(PYTHON) -m uvicorn services.api.app:app --host $(API_HOST) --port $(API_PORT)

serve-web:
	cd apps/web && npm run dev

services-down:
	docker compose down
