API_DIR := services/api
UV := cd $(API_DIR) && uv run

.PHONY: up down api-install migrate seed api worker web admin test lint fmt openapi tf-fmt tf-validate

up:
	docker compose up -d postgres minio minio-init localstack mailpit

down:
	docker compose down

api-install:
	cd $(API_DIR) && uv sync --all-extras

migrate:
	$(UV) alembic upgrade head

seed:
	$(UV) python scripts/seed_dev.py
	$(UV) python scripts/ingest_kb.py

api:
	$(UV) uvicorn complymate.main:app --reload --port 8000

worker:
	$(UV) python -m complymate.workers.entry --local

web:
	pnpm --filter @complymate/web dev

admin:
	pnpm --filter @complymate/platform-admin dev

lint:
	$(UV) ruff check src tests
	$(UV) mypy src

fmt:
	$(UV) ruff format src tests
	$(UV) ruff check --fix src tests

test: lint
	$(UV) pytest -q

openapi:
	$(UV) python scripts/export_openapi.py ../../docs/api/openapi.json
	pnpm --filter @complymate/api-types generate

tf-fmt:
	terraform fmt -recursive infra/terraform

tf-validate:
	cd infra/terraform/envs/aws-dev && terraform init -backend=false && terraform validate
