Contributing to SomaBrain

Quick Start
- Python 3.10+
- Create venv: `python3 -m venv .venv && source .venv/bin/activate`
- Install deps: `python -m pip install -U pip setuptools wheel && python -m pip install somafractalmemory && python -m pip install numpy redis fakeredis qdrant-client networkx prometheus-client fastapi uvicorn httpx`
- Run API: `uvicorn somabrain.app:app --reload`

Tests
- Ad-hoc scripts:
  - `PYTHONPATH=. .venv/bin/python tests/test_endpoints_basic.py`
  - `PYTHONPATH=. .venv/bin/python tests/test_hrr_cleanup.py`
  - `PYTHONPATH=. .venv/bin/python tests/test_memory_client.py`
  - `PYTHONPATH=. .venv/bin/python tests/test_reflection_v2.py`
  - `PYTHONPATH=. .venv/bin/python tests/test_consolidation.py`
  - `PYTHONPATH=. .venv/bin/python tests/test_sleep_endpoint.py`
  - `PYTHONPATH=. .venv/bin/python tests/test_semantic_graph.py`
  - `PYTHONPATH=. .venv/bin/python tests/test_soft_salience.py`
  - `PYTHONPATH=. .venv/bin/python tests/test_supervisor.py`
  - `PYTHONPATH=. .venv/bin/python tests/test_planner.py`
  - `PYTHONPATH=. .venv/bin/python tests/test_microcircuits.py`
  - `PYTHONPATH=. .venv/bin/python tests/test_graph_reasoning.py`
  - `PYTHONPATH=. .venv/bin/python tests/test_personality.py`
  - `PYTHONPATH=. .venv/bin/python tests/test_predictor_budget.py`
  - `PYTHONPATH=. .venv/bin/python tests/test_migration.py`
- Or run all via Make: `make test`

Coding Guidelines
- Keep modules focused and biologically named where appropriate (Thalamus, Amygdala, BasalGanglia, Cerebellum, etc.).
- Favor deterministic, testable math primitives; instrument with Prometheus metrics.
- Multi-tenant safety first: enforce tenant scoping in state and memory namespaces.
- Keep configuration via Dynaconf/ENV with sensible defaults; document flags in README.

Math-first Engineering Checklist (required per PR)
- Define the contract: inputs/outputs, invariants (e.g., unit-norm, bounds, normalization), and error modes.
- Add or update property tests for math invariants when applicable (HRR, cosine, RWR, Oja, ring buffer).
- Show perf/space budget deltas (local and http mode if relevant) and confirm SLOs by mode.
- Update or add metrics/traces; avoid double-counting memory ops (SFM is canonical for memory metrics).
- Note risks and mitigations; link to the roadmap item or ADR.

AI co-development guidelines
- Use AI to scaffold, but validate math, contracts, and security yourself; cite references for algorithms.
- No secrets in code or docs; prefer env/secret manager. Keep diffs minimal and rationale clear in PRs.

Docs
- Update `docs/roadmap/progress.md` when adding features; keep `PROGRESS.md` for historical entries only.
- Add API notes to `README.md` sections (Configuration, HRR, Reflection, Migration).

Commit Hygiene
- Small, focused commits; reference sprint/milestone where applicable.
- Don’t introduce unrelated changes in a feature PR.
