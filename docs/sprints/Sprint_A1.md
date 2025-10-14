# Sprint A1 – Architecture Baseline (Weeks 1-2)

> Canonical log for SomaBrain 3.0, Epic A (Foundations & Infrastructure)

## Objective
Enforce clean architecture boundaries and lay down the scaffolding for BrainState and service composition.

- Document domain/application/infrastructure separation via ADR.
- Introduce BrainState skeleton with dependency injection stubs.
- Prepare factories to assemble current services without behavior change.

## Scope Checklist

| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| Write ADR: "Layered Architecture for SomaBrain" | Architecture | ☐ | Capture in `docs/adr/`.
| Prototype `BrainState` dataclass with current dependencies | Platform | ☐ | No functional change; behind feature flag.
| Create module boundaries (`domain/`, `application/`, `infrastructure/`) | Platform | ☐ | Update imports to respect new structure.
| Add composition root / factory module | Architecture | ☐ | Serves as future DI container.
| Update lint/mypy paths to new packages | QA | ☐ | Ensure tooling passes.
| Document architecture handoff in `DEVELOPMENT_GUIDE.md` | Docs | ☐ | Add overview diagram.

## Deliverables
- ADR outlining layered architecture
- `somabrain/brain_state.py` (or similar) skeleton
- Initial composition root with existing services wired
- Developer guide update summarizing architecture

## Risks & Mitigations
- **Legacy imports breaking** -> run `ruff`, `mypy`, `pytest` to catch regressions.
- **Team confusion over new layout** -> provide diagram + brown-bag walkthrough.

## Exit Criteria
- ADR merged and referenced from roadmap
- BrainState skeleton available behind flag with tests passing
- Project builds without import errors after directory restructuring

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-10-13 | AI assistant | Created Sprint A1 canonical log. |

---

_Maintain this document as source of truth during Sprint A1._
