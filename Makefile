SHELL := /bin/bash
.DEFAULT_GOAL := help
BACKEND := backend
FRONTEND := frontend
# Import from src directly; editable-install .pth files can be skipped when macOS marks .venv hidden.
export PYTHONPATH := src

.PHONY: help setup dev api web test test-backend test-frontend lint format seed screenshots qa clean

help: ## Show available targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: ## Install backend + frontend deps and seed the database
	cd $(BACKEND) && uv sync
	cd $(FRONTEND) && npm install
	$(MAKE) seed

dev: ## Run API (:8000) and web (:5173) together
	@trap 'kill 0' EXIT INT TERM; \
	  (cd $(BACKEND) && uv run uvicorn atc.api.main:app --reload --port 8000) & \
	  (cd $(FRONTEND) && npm run dev -- --port 5173) & \
	  wait

api: ## Run API only
	cd $(BACKEND) && uv run uvicorn atc.api.main:app --reload --port 8000

web: ## Run web only
	cd $(FRONTEND) && npm run dev -- --port 5173

seed: ## Generate synthetic data (seed 42) and the default baseline + ATC runs
	cd $(BACKEND) && uv run python -m atc.seed

test: test-backend test-frontend ## Run all tests

test-backend: ## Backend tests with coverage on the rules engine
	cd $(BACKEND) && uv run pytest --cov=atc --cov-report=term-missing && uv run coverage report --include='src/atc/engine/*' --fail-under=90

test-frontend: ## Frontend type check
	cd $(FRONTEND) && npm run typecheck

lint: ## Lint, format check and type check everything
	cd $(BACKEND) && uv run ruff check . && uv run ruff format --check . && uv run mypy
	cd $(FRONTEND) && npm run lint && npm run format:check && npm run typecheck

format: ## Auto-format everything
	cd $(BACKEND) && uv run ruff format . && uv run ruff check --fix .
	cd $(FRONTEND) && npm run format

screenshots: ## Capture dashboard screenshots at 1440px and 390px (needs `make dev` running)
	cd $(FRONTEND) && npm run screenshots

qa: ## Accessibility (axe WCAG 2.1 AA) and interaction checks (needs `make dev` running; adds a run, so reseed after)
	cd $(FRONTEND) && npm run qa

clean: ## Remove caches and the local database
	rm -rf $(BACKEND)/.pytest_cache $(BACKEND)/.mypy_cache $(BACKEND)/.ruff_cache $(BACKEND)/atc.db $(FRONTEND)/dist
