# Sprint B0 – MathService Facade (Weeks 7-8)

> Canonical log for SomaBrain 3.0, Epic B (Math & Vectorizer Modernization)

## Objective
Introduce a unified MathService facade that exposes Composer and Vectorizer capabilities with rigorous tests and documentation.

- Define MathService API covering binding, unbinding, normalization, and vector fusion.
- Implement reference Composer/Vectorizer using current FFT pipeline for compatibility.
- Establish property-based and golden tests to validate algebraic guarantees.

## Scope Checklist

| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| Draft MathService interface and module layout | Architecture | ☐ | Include type hints + docstrings.
| Port existing math utilities behind facade | Platform | ☐ | Maintain backward compatibility.
| Add property-based tests (binding/unbinding, norm preservation) | QA | ☐ | Use Hypothesis or similar.
| Document math playbook outline | Docs | ☐ | Seed `docs/math/playbook.md`.
| Benchmark facade vs legacy direct calls | Performance | ☐ | Capture baseline numbers.
| Prepare feature flag `math.service.enabled` | Platform | ☐ | Default off.

## Deliverables
- `somabrain/math/service.py` (or equivalent) with tests
- Math playbook skeleton
- Benchmark report comparing facade vs legacy path

## Risks & Mitigations
- **Hidden dependencies bypassing facade** -> search repo, create lint rule.
- **Test flakiness in property-based suite** -> seed runs, cap examples.

## Exit Criteria
- All math entry points routed through facade behind flag
- Property tests green in CI
- Benchmarks show acceptable overhead (<5% regression)

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-10-13 | AI assistant | Created Sprint B0 canonical log. |

---

_This document must be updated throughout Sprint B0._
