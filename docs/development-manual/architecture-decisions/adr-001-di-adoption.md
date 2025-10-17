> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# ADR-001: Adopt Dependency Injection for Runtime Construction

- **Status**: Proposed (Sprint 1)
- **Deciders**: Architecture Guild, Platform Engineering
- **Date**: 2025-10-11

## Context

`somabrain/app.py` currently constructs global singletons via `_patch_runtime_singletons`, relying on module import side effects and dummy fallbacks. This architecture complicates testing, encourages hidden state, and blocks parallel execution. Strict-real enforcement forbids dummy objects, so we need an explicit dependency injection (DI) mechanism.

## Decision

Adopt an application container that provides runtime dependencies via explicit providers. FastAPI `Depends` hooks will resolve components (memory API, planners, caches) from this container. `somabrain/app.py` will import router modules that express dependencies declaratively.

## Consequences

- **Positive**
  - Clear wiring of services, easier unit/integration tests.
  - Eliminates global mutation and dummy fallbacks.
  - Enables per-request overrides (multi-tenant, test doubles when explicitly allowed).
- **Negative**
  - Refactoring large portions of `somabrain/app.py` and dependent modules.
  - Tests must be updated to initialize the container before using clients.

## Implementation Plan

1. Create `somabrain/container.py` with provider registration and lifecycle hooks.
2. Extract domain routers into `somabrain/api/` packages referencing DI dependencies.
3. Update `tests/conftest.py` to bootstrap the container once per session.
4. Remove `_patch_runtime_singletons` and dummy classes from `somabrain/app.py`.
5. Document usage in the development manual and update CI scripts.

## Alternatives Considered

- **Keep runtime singletons**: Rejected; violates strict-real contract and preserves global state issues.
- **Service locator pattern**: Rejected; obscures dependencies and retains global lookups.

## Follow-up Tasks

- Track DI container performance under load.
- Provide overrides for local tooling (e.g., REPL) via explicit factory functions.
