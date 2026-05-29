.PHONY: setup test lint ingest-all eval-retrieval services-down

PYTHON ?= python
MODE ?= dev
N ?= 10
ADDGENE_STALE_DAYS ?= 1

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
	$(PYTHON) -m packages.data_pipeline.ingest.addgene --mode $(MODE) --limit $(N) --stale-days $(ADDGENE_STALE_DAYS)

eval-retrieval:
	@echo "TODO: run Phase 1 retrieval evaluation"

services-down:
	docker compose down
