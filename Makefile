# Utility: dump drift state baselines and last_drift timestamps
.PHONY: drift-dump
drift-dump:
	@echo "Dumping drift state (set SOMABRAIN_DRIFT_STORE or enable detector)..."
	@ENABLE_DRIFT_DETECTION?=0 \
	python somabrain/scripts/drift_dump.py

# Focused test targets
.PHONY: test-strict
test-strict:
	pytest -q tests/invariants/test_strict_mode.py

.PHONY: test-drift
test-drift:
	pytest -q tests/monitoring/test_drift_persistence.py tests/monitoring/test_drift_integration.py

.PHONY: test-context
test-context:
	pytest -q tests/context/test_context_builder_alignment.py
# Variables
PY?=python3
VENV?=.venv
PIP:=$(VENV)/bin/pip
PYBIN:=$(VENV)/bin/python
UVICORN:=$(VENV)/bin/uvicorn
PYTEST:=$(VENV)/bin/pytest
RUFF:=$(VENV)/bin/ruff
MYPY:=$(VENV)/bin/mypy

.PHONY: help venv install dev run test test-live lint typecheck fmt clean docker-build docker-run docker-build-prod docker-run-prod docker-push compose-build compose-up compose-down compose-restart compose-logs compose-ps compose-health compose-clean up-dev up-prod-like down-prod-like ps-prod-like logs-prod-like

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

.PHONY: bench-diffusion
bench-diffusion:
	PYTHONPATH=. MPLBACKEND=Agg $(PYBIN) benchmarks/diffusion_predictor_bench.py

.PHONY: bench-recall
bench-recall:
	PYTHONPATH=. $(PYBIN) benchmarks/recall_latency_bench.py

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
	@echo "Delegating to Docker‑Compose dev stack (dev_up.sh)"
	@./scripts/dev_up.sh

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

# Run an end-to-end smoke test: POST reward and verify it's in the Kafka topic.
.PHONY: smoke-e2e
smoke-e2e:
	@echo "Running end-to-end smoke (POST reward -> verify event)"
	@sh ./scripts/e2e_smoke.sh

# Top-level start: build image, bring up full prod-like stack, run smoke test
.PHONY: start-servers
start-servers:
	@echo "Building image and starting full stack..."
	@$(COMPOSE_CMD) build
	@$(PORT_OVERRIDES) $(COMPOSE_CMD) up -d
	@echo "Waiting for API health..."
	@for i in $$(seq 1 40); do \
		if curl -fsS http://127.0.0.1:9696/health >/dev/null; then \
			echo "API healthy"; \
			break; \
		fi; \
		sleep 1; \
		done
	@$(MAKE) smoke-e2e

# ---------------------------------------------------------------------------
# Two canonical modes: dev (embedded small services) and prod-like (full stack)
# ---------------------------------------------------------------------------

# Force port normalization regardless of host env noise (standardize on 9696)
PORT_OVERRIDES=REDIS_HOST_PORT=30100 KAFKA_EXPORTER_HOST_PORT=30103 PROMETHEUS_HOST_PORT=30105 POSTGRES_EXPORTER_HOST_PORT=30107 SOMABRAIN_HOST_PORT=9696

# Use a stable compose project name without port suffix
COMPOSE_CMD=docker compose --env-file ./.env -p somabrain

up-prod-like:
	@echo "Starting full prod-like stack (all services, real infra)..."
	@$(PORT_OVERRIDES) $(COMPOSE_CMD) up -d
	@echo ""
	@echo "Prod-like URLs:"
	@echo "- API:            http://127.0.0.1:9696/health"
	@echo "- Redis:          redis://127.0.0.1:30100"
	@echo "- Kafka broker:   127.0.0.1:30102 (internal clients should use somabrain_kafka:9092)"
	@echo "- OPA:            http://127.0.0.1:30104/health"
	@echo "- Prometheus:     http://127.0.0.1:30105"
	@echo "- Postgres:       127.0.0.1:30106"
	@echo "- SchemaRegistry: http://127.0.0.1:30108"
	@echo "- Reward Prod:    http://127.0.0.1:30183/health"
	@echo "- Learner Online: http://127.0.0.1:30184/health"

down-prod-like:
	@$(COMPOSE_CMD) down --remove-orphans

ps-prod-like:
	@$(COMPOSE_CMD) ps

logs-prod-like:
	@$(COMPOSE_CMD) logs -f --tail=200

up-dev:
	@echo "Starting simplified dev mode (embed reward+learner under main API)..."
	@SOMABRAIN_MODE=dev SOMABRAIN_EMBED_DEV_SERVICES=1 $(PORT_OVERRIDES) $(COMPOSE_CMD) up -d --remove-orphans somabrain_redis somabrain_kafka somabrain_opa somabrain_postgres somabrain_app
	@echo "Dev URLs:"
	@echo "- API:            http://127.0.0.1:9696/health"
	@echo "- Reward:         http://127.0.0.1:9696/reward/health"
	@echo "- Learner:        http://127.0.0.1:9696/learner/health"

# (Removed) cognition overlay and Linux host-gateway helpers to keep a single compose entrypoint
