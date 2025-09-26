# Variables
PY?=python3
VENV?=.venv
PIP:=$(VENV)/bin/pip
PYBIN:=$(VENV)/bin/python
UVICORN:=$(VENV)/bin/uvicorn
PYTEST:=$(VENV)/bin/pytest
RUFF:=$(VENV)/bin/ruff
MYPY:=$(VENV)/bin/mypy

.PHONY: help venv install dev run test lint typecheck fmt clean docker-build docker-run docker-build-prod docker-run-prod docker-push

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

.PHONY: test
test:
	PYTHONPATH=. $(PY) tests/test_endpoints_basic.py
	PYTHONPATH=. $(PY) tests/test_hrr_cleanup.py
	PYTHONPATH=. $(PY) tests/test_memory_client.py
	PYTHONPATH=. $(PY) tests/test_reflection_v2.py
	PYTHONPATH=. $(PY) tests/test_graph_reasoning.py
	PYTHONPATH=. $(PY) tests/test_personality.py
	PYTHONPATH=. $(PY) tests/test_predictor_budget.py
	PYTHONPATH=. $(PY) tests/test_migration.py
