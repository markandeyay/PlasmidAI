.PHONY: setup test lint ingest-all eval-retrieval services-down

PYTHON ?= python

setup:
	powershell -NoProfile -ExecutionPolicy Bypass -Command "if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }"
	docker compose up -d

test:
	$(PYTHON) scripts/check_services.py
	$(PYTHON) -m pytest

lint:
	@echo "No lint configured yet."

ingest-all:
	@echo "TODO: run all Phase 0 ingestion jobs"

eval-retrieval:
	@echo "TODO: run Phase 1 retrieval evaluation"

services-down:
	docker compose down
