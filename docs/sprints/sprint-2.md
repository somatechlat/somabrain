> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# Sprint 2 (Application Core Extraction)

- **Cadence:** Oct 18 – Oct 31, 2025
- **Goal:** Break the FastAPI monolith into modular routers and establish the dependency injection container with zero reliance on runtime singletons.

## Backlog

| ID | Work Item | Owner | Status | Notes |
| --- | --- | --- | --- | --- |
| S2-01 | Scaffold `somabrain/container.py` DI provider | Architecture | ⏳ Planned | Use FastAPI `Depends` + provider registry |
| S2-02 | Extract public API routers into `somabrain/api/` | Application Team | ⏳ Planned | Split memory, planning, ops, admin domains |
| S2-03 | Replace `_patch_runtime_singletons` with DI wiring | Architecture | ⏳ Planned | Remove dummy classes, use container bootstrap |
| S2-04 | Update tests to consume DI container | QA | ⏳ Planned | Adjust fixtures in `tests/conftest.py` |
| S2-05 | Create ADR-001 documenting DI adoption | Architecture | ⏳ Planned | Location: `docs/adr/ADR-001-di-adoption.md` |

## Daily Journal

| Date | Update |
| --- | --- |
| 2025-10-18 | Sprint planned. Awaiting hand-off from Sprint 1 deliverables. |

## Risks & Mitigations

- **Circular dependency risk**: Mitigate with clean interfaces and provider registry tests.
- **Test fixture breakage**: Provide compatibility layer while migrating fixtures.
- **Runtime regression**: Add smoke tests to exercise `/health`, `/remember`, `/recall` through routers.

## Definition of Done

- DI container provides all formerly global singletons.
- `somabrain/app.py` only wires FastAPI app and imports routers.
- All tests pass using DI path; no legacy `_patch_runtime_singletons` calls remain.
