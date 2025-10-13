> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# Canonical Roadmap — SomaBrain (Expanded)

> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

This is the canonical, sprinted refactor roadmap for the SomaBrain repository. It contains:
- Guiding principles and program pillars
- Sprint-by-sprint deliverables and timelines
- A folder-by-folder analysis of the repository (counts and prioritized targets)
- Safety rules for numeric/algorithmic code and verification requirements

Use this document as the single source of truth for the repo refactor. Small, reversible PRs only. All algorithmic changes require regression proofs (golden tests + benchmarks).

## Guiding Principles (short)
- Strict Real: runtime must use real libraries and services; type-only stubs (.pyi) are allowed for typing only.
- Math-first: numeric functions must be treated as critical; no changes without tests and performance baselines.
- Ports & Adapters: domain logic is independent from adapters; use Protocols for DI and typed adapters for external libs.
- DTOs at boundaries: use Pydantic/dataclass DTOs at API/storage boundaries for validation and clear shapes.

## Sprint cadence and high level plan
- Sprint length: 1–2 weeks.
- Total program: Sprint 0 (prep) + Sprints 1–8 detailed below + ongoing maintenance.

### Sprint 0 — Preparation (Completed / baseline)
- Baseline mypy: 223 errors across 35 files (checked 135 files). Top offenders identified.
- Created `mypy.ini` and started local `stubs/` to reduce import-not-found noise.
- This canonical roadmap (this file) to be saved as authoritative plan.

### Sprint 1 — Noise reduction & observability adapter
- Goals: install official stubs where safe, extend local `.pyi` for opentelemetry and other missing libs, add typed tracing adapter.
- Outcome: remove import-not-found noise and resolve OTel attribute errors.

### Sprint 2 — Crypto adapter & typing fixes
- Goals: centralize cryptography use in a typed adapter, add sign/verify unit tests with known vectors; fix union-attr and call-arg typing issues.

### Sprint 3 — Repository adapters for DB
- Goals: add repositories returning DTOs instead of leaking SQLAlchemy `Column` into business logic; add SQLite integration tests.

### Sprint 4 — Memory & RAG pipeline stabilization
- Goals: align MemoryBackend Protocols, normalize memstore/etcd adapters (bytes/str), break down `rag_pipeline.py` into smaller modules.

### Sprint 5 — App refactor & routers
- Goals: decompose `app.py` into routers, DI composition, explicit Pydantic schemas for APIs.

### Sprint 6 — Numeric/quantum verification and hardening
- Goals: golden datasets, regression tests, Hypothesis invariants, benchmarks; do not change algorithms without proof.

### Sprints 7–8 — CI/CD, hardening, and launch readiness
- Goals: pipeline automation, blue/green deploys, chaos/load tests, runbooks and DR drills.

## Folder-by-folder repository analysis (scan results)

I scanned the repository and counted files in major directories to prioritize work. The scan was done programmatically and the file lists are included in the repository but summarized below.

- `somabrain/` (core app): ~145 Python files. This is the largest area and contains the primary business logic, API, services, math and quantum code. Highest priority targets: `somabrain/app.py`, `somabrain/services/rag_pipeline.py`, `somabrain/opa/signature.py`, `somabrain/math/*`, `somabrain/quantum*`.

- `common/` (utils & SDK): ~8 Python files. Includes `common/utils/trace.py` and `common/utils/etcd_client.py` — early adapter work here reduces a lot of type noise.

- `brain/` (adapters): 1 notable adapter file: `brain/adapters/memstore_adapter.py` — memstore HTTP adapter shows bytes/str usage to normalize.

- `services/` (service modules): ~14 files (plus subpackages). Includes `memory_service.py`, `rag_pipeline.py`, `memory_integrity_worker.py` — mid-priority.

- `tests/`: ~144 test files. Coverage is strong; we will use these to validate refactors and add golden tests.

- `docs/`: ~32 docs files. Many existing design documents and sprint notes — we will update/centralize them under `docs/sprints/` and `docs/shared_infra/`.

- `benchmarks/`: ~36 scripts. Useful for numeric/throughput verification and will be integrated into the verification plan.

- `scripts/`: ~11 scripts including CI helpers such as `scripts/ci/run_ci.sh`.

These counts reflect a snapshot and are intended to help prioritize which folders to focus on first.

## Current mypy top-offenders (from latest run)
- `somabrain/services/rag_pipeline.py` — 37 errors
- `somabrain/app.py` — 26 errors
- `somabrain/opa/signature.py` — 22 errors
- `somabrain/autonomous/coordinator.py` — 21 errors
- `somabrain/constitution/__init__.py` — 15 errors
- `somabrain/metrics.py` — 12 errors
- `somabrain/grpc_server.py` — 11 errors
- `somabrain/config.py` — 11 errors
- `somabrain/constitution/storage.py` — 10 errors
- `observability/provider.py` — 10 errors

These are the primary, high-impact files to triage after reducing stub/import noise.

## Safety rules for numeric and algorithmic modules
- No algorithm changes without: a golden test (exact output for representative inputs), a benchmark comparison (before/after), and a review sign-off.
- Any refactor that touches `somabrain/math/*`, `somabrain/quantum*`, or numerics in `rag_pipeline.py` must add tests in `tests/golden/` and pass them in CI.
- Performance regressions above a configurable tolerance (e.g., >5% slower on a benchmark harness) must block merges until analyzed.

## Verification & CI strategy
- Baseline: run `./scripts/ci/run_ci.sh` which executes ruff, mypy, pytest.
- Add golden tests in `tests/golden/` and Hypothesis-based property tests for invariants in numerics.
- Introduce a benchmarks job (optional) that runs on-demand or nightly to ensure no regression.

## Sprint-by-sprint deliverables (detailed)
- Sprint 0: Baseline mypy report; `mypy.ini` + `stubs/` prepared.
- Sprint 1: Observability adapter and expanded OTel stubs.
- Sprint 2: Crypto adapter and sign/verify unit vectors.
- Sprint 3: Repositories for constitution and DB-backed modules.
- Sprint 4: Memory & rag pipeline modularization and MemoryBackend stabilization.
- Sprint 5: API router extraction and DI composition.
- Sprint 6: Numeric verification, golden tests, benchmarks.
- Sprint 7–8: CI/CD pipelines, hardening, and launch-readiness.

## Immediate next steps (I will perform these if you confirm):
1. Persist this canonical roadmap to `docs/CANONICAL_ROADMAP.md` (done by this patch).
2. Wave 0→1: Install small set of official type stubs (where safe) and finish opentelemetry stubs.
3. Start observability adapter (small, safe change) and re-run mypy to measure delta.

## How I will report progress
- After each sprint wave I will provide a compact report with: changed files, tests added, mypy delta (errors before → after), and CI status (ruff + mypy + pytest).

## Appendices
1. Full folder scan (selected file lists written at time of scan) is available in the workspace under `docs/_scan/` (if you prefer I can write a machine-readable CSV there).

If this looks good I will now commit this file (already applied) and proceed with Wave 0→1 (stubs and observability adapter). Reply "start wave 0" to begin the automated changes and CI runs. If you want edits to the roadmap text before committing, tell me what to change.
