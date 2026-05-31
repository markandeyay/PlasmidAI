.PHONY: setup test lint ingest-all eval-retrieval services-down ingest-addgene ingest-genbank ingest-curated parse-sample quality-report

PYTHON ?= python
MODE ?= dev
N ?=
ADDGENE_STALE_DAYS ?= 1
GENBANK_STALE_DAYS ?= 60

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

eval-retrieval:
	@echo "TODO: run Phase 1 retrieval evaluation"

services-down:
	docker compose down
