# Variables
PY?=python3
VENV?=.venv
PIP:=$(VENV)/bin/pip
PYBIN:=$(VENV)/bin/python
UVICORN:=$(VENV)/bin/uvicorn
PYTEST:=$(VENV)/bin/pytest
RUFF:=$(VENV)/bin/ruff
MYPY:=$(VENV)/bin/mypy

.PHONY: help venv install dev run test test-live lint typecheck fmt clean docker-build docker-run docker-build-prod docker-run-prod docker-push compose-build compose-up compose-down compose-restart compose-logs compose-ps compose-health compose-clean

help:
	@echo "Targets: venv | install | dev | run | test | lint | typecheck | fmt | docker-build | docker-run | clean"

venv:
	$(PY) -m venv $(VENV)
	$(PIP) install -U pip setuptools wheel

install: venv
	# Install this project only. External memory services are managed separately.
	$(PIP) install -e .

dev: venv
	# Dev: install project dependencies only. No bundled memory service is installed.
	$(PIP) install -e .[dev]

run:
	$(UVICORN) somabrain.app:app --reload

bench:
	PYTHONPATH=. MPLBACKEND=Agg $(PYBIN) benchmarks/cognition_core_bench.py

test:
	PYTHONPATH=. $(PYTEST) -q

.PHONY: test-live
test-live:
	SOMABRAIN_TEST_LIVE_STACK=1 SOMA_API_URL=$${SOMA_API_URL:-http://127.0.0.1:9696} PYTHONPATH=. $(PYTEST) -q

lint:
	$(RUFF) check .

typecheck:
	$(MYPY) somabrain || true

fmt:
	$(RUFF) format .

IMAGE?=somabrain
TAG?=local

docker-build:
	docker build -t $(IMAGE):$(TAG) .

docker-run:
	docker run --rm -p 9696:9696 -e SOMABRAIN_PORT=9696 $(IMAGE):$(TAG)

docker-build-prod:
	docker build -t $(IMAGE):prod .

docker-run-prod:
	docker run --rm -p 9696:9696 -e SOMABRAIN_PORT=9696 $(IMAGE):prod

docker-push:
	@echo "Use: make docker-build-prod IMAGE=your/repo && docker push your/repo:prod"

clean:
	rm -rf $(VENV) .pytest_cache .mypy_cache **/__pycache__
PY := .venv/bin/python

# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------
.PHONY: docs
# Build HTML documentation with Sphinx. Uses the ``docs/source`` configuration.
# The ``AUTOSUMMARY`` env var can be set to ``1`` to enable API autosummary.
# Example: ``AUTOSUMMARY=1 make docs``

docs:
	@echo "Building Sphinx documentation..."
	@AUTOSUMMARY=$(AUTOSUMMARY) sphinx-build -b html docs/source docs/build

# Consolidated test target – runs the full pytest suite (kept from earlier edit)
.PHONY: test
test:
	PYTHONPATH=. $(PYTEST) -q

# Keep the original docker build/run targets for backward compatibility
.PHONY: docker-build docker-run docker-build-prod docker-run-prod docker-push

# Generate Kubernetes ConfigMap from docs/operations/configuration.md
.PHONY: configmap
configmap:
	@python scripts/generate_configmap.py

# Convenience aliases for the two main startup scripts
.PHONY: dev-up local-up

dev-up:
	@echo "Starting Docker‑Compose development stack..."
	@./scripts/dev_up.sh

local-up:
	@echo "Starting pure‑Python local stack..."
	@./scripts/run_full_stack.sh

# Clean up virtual environment and caches (keeps existing behavior)
.PHONY: clean
clean:
	rm -rf $(VENV) .pytest_cache .mypy_cache **/__pycache__

# ---------------------------------------------------------------------------
# Docker Compose (single API service on 9696; external memory on 9595)
# ---------------------------------------------------------------------------
PROJECT?=somabrain
COMPOSE?=docker compose -p $(PROJECT)

.PHONY: compose-build compose-up compose-down compose-restart compose-logs compose-ps compose-health compose-clean

compose-build:
	$(COMPOSE) build somabrain

compose-up:
	$(COMPOSE) up -d somabrain
	@echo "Waiting for API health..."
	@for i in $$(seq 1 20); do \
		if curl -fsS http://127.0.0.1:9696/health >/dev/null; then \
			echo "API healthy on http://127.0.0.1:9696"; \
			exit 0; \
		fi; \
		sleep 1; \
	 done; \
	 echo "API did not become healthy in time"; exit 1

compose-down:
	$(COMPOSE) down --remove-orphans

compose-restart:
	$(COMPOSE) restart somabrain

compose-logs:
	$(COMPOSE) logs -f --tail=200 somabrain

compose-ps:
	$(COMPOSE) ps

compose-health:
	curl -fsS http://127.0.0.1:9696/health | jq . || curl -fsS http://127.0.0.1:9696/health || true

compose-clean:
	$(COMPOSE) down --remove-orphans
	- docker network rm $(PROJECT)_default 2>/dev/null || true
	@echo "Compose project cleaned."
