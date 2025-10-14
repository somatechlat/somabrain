# Sprint D1 – App Modularization (Weeks 21-22)

> Canonical log for SomaBrain 3.0, Epic D (Brain Architecture & Execution)

## Objective
Refactor application entry points so API transport, application services, and domain logic are cleanly separated.

- Break `somabrain.app` into bootstrapping, router registration, and service wiring modules.
- Ensure lifecycle hooks from BrainState integrate with FastAPI middleware and background tasks.
- Update tooling (lint, tests, packaging) to reflect new structure.

## Scope Checklist

| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| Split `somabrain.app` into modules (`bootstrap`, `routers`, `services`) | Platform | ☐ | Maintain API compatibility.
| Integrate BrainState hooks into FastAPI middleware | Platform | ☐ | Manage request-scoped state.
| Update import paths and re-export as needed | Platform | ☐ | Provide shim module if required.
| Adjust tests and fixtures to new structure | QA | ☐ | Ensure minimal churn for external clients.
| Update documentation (API startup sequence) | Docs | ☐ | Include diagram.
| Review packaging and entrypoints (setup, Docker, Make) | DevOps | ☐ | Keep builds green.

## Deliverables
- Modularized application entry structure
- Updated tests and fixtures
- Documentation capturing new startup flow

## Risks & Mitigations
- **Breaking external imports** -> Provide compatibility shims and deprecation warnings.
- **Middleware regressions** -> Add integration tests covering auth, rate limiting, controls.

## Exit Criteria
- API serves correctly in staging through new bootstrap path
- Compatibility shims verified by regression tests
- Documentation accepted by platform + API teams

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-10-13 | AI assistant | Created Sprint D1 canonical log. |

---

_Maintain this file as Sprint D1 progresses._
