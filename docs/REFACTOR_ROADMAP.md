# SomaBrain Refactor & Architecture Roadmap

This document is the canonical roadmap for the ongoing refactor, typing, and architectural hardening work for the `soma_integration` branch.

Keep this file updated as sprints progress. It is intentionally pragmatic: small, verifiable steps, CI-driven, and reversible.

## Current status (snapshot)
- Branch: `soma_integration`
- Lint (ruff): passing
- Type-check (mypy): ~220 errors across the repo (post-memory-client cleanup)
- Key completed work: `somabrain/memory_client.py` refactor to strict `Tuple[float,float,float]` coordinates and protocol-driven MemoryBackend introduced.

## Goals
1. Make the memory layer (MemoryClient / MemoryBackend) production-ready, fully-typed, and robust.
2. Reduce CI noise (missing stubs / import-not-found), then systematically triage real mypy errors.
3. Introduce a small set of architectural improvements (clear interfaces, DI-friendly constructors, remove fragile global state) without rewriting numerical core algorithms.
4. Add tests and documentation so the system is maintainable and portable.

## High-level approach
- Work in small batches (module-scoped patches). Run CI after each batch.
- Use Protocols and Dependency Injection where it reduces coupling.
- Prefer adding types and small fixes over large rewrites. Where a larger redesign is necessary, create a dedicated PR with a migration plan and tests.
- Where third-party stubs are missing, prefer installing official stubs; if unavailable, add minimal local stubs under `stubs/` to unblock progress.

## Sprint cadence
- Sprint length: 1 week (or until the focused milestone is reached).
- Each sprint consists of:
  1. A clear sprint goal and acceptance criteria.
  2. A set of small issues/patches (1–6 changes) with CI validation.
  3. Tests + docs updates for any public API change.

## Sprint 1 — Stabilize typing and CI (started)
Goal: Remove import-not-found noise and stabilize module-level typing so mypy reports real type errors only.

Tasks:
- (T1) Install missing type stubs into the repo venv (requests, PyYAML, types-psycopg2, types-grpcio, scipy-stubs, types-hvac, types-boto3, types-requests). Run CI and record remaining missing imports.
- (T2) Create `stubs/` minimal shims for stubborn subpackages (e.g., `opentelemetry.*` paths) to silence import-not-found errors if no official stubs exist.
- (T3) Add a minimal mypy config tuning (incremental: permit --install-types or list of ignored-missing-imports) so we can focus on concrete typing problems.
- (T4) Confirm `somabrain/memory_client.py` is clean under mypy and add unit tests for critical edge paths.

Acceptance criteria:
- CI reports far fewer import-untyped/import-not-found messages (majority removed).
- MemoryClient unit tests pass locally and in CI.

## Sprint 2 — High-impact module triage
Goal: Address the top 10 mypy failure groups (by frequency) across the codebase.

Process:
- Produce an ordered list of the top files causing errors (mypy output aggregated).
- For each file: propose a minimal patch (type annotations, Optional guards, correct function signature) and run CI.

Typical fixes:
- Add missing variable annotations (e.g., `_history: list[...] = []`).
- Fix default arguments that are None but annotated non-Optional.
- Narrow union types or add narrow `# type: ignore` where annotations are expensive.
- Add small adapter/helpers (e.g., `dict_to_column(...)` wrappers) for SQLAlchemy typing mismatches.

## Sprint 3 — Architecture hardening
Goal: Introduce targeted architectural improvements: clear interfaces, DI, remove fragile module globals.

Example tasks:
- Replace module-level global mutable mirrors with a single injectable `MirrorStore` class passed to `MemoryService` under test/dev.
- Introduce Protocols for heavy external dependencies (embedder, vector_client) and add small runtime factories.
- Document the MemoryClient contract and the MemoryBackend Protocol in `docs/memory_architecture.md`.

## Tests & CI
- Use `./scripts/ci/run_ci.sh` for local verification.
- Add unit tests near code changes (pytest). Aim for focused tests per module.

How to run CI locally (macOS, zsh):
```bash
# from repo root
./scripts/ci/run_ci.sh
```

## Branching and PR workflow
- Work on feature branches named `sprint/<N>-<short-desc>`.
- Each logical change gets a small PR with a single purpose and CI green before merge.

## Communication and artifacts
- Keep this file up to date. Add `docs/memory_architecture.md` and update `README.md` with quickstart changes.
- Record test harness commands and any environment-specific instructions here.

## Next actions (automated)
1. Create `stubs/` directory with minimal pyi for opentelemetry subpackages that still produce mypy import errors.
2. Add/adjust mypy config (if approved) to enable incremental typing.
3. Start Sprint 1 tasks (T1–T4) and commit small patches with CI runs between each.

---
Created by the integration refactor agent on commit. Keep this file updated as we progress through each sprint.
