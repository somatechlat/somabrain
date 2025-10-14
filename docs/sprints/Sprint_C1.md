# Sprint C1 – Unified Scorer (Weeks 15-16)

> Canonical log for SomaBrain 3.0, Epic C (Salience & Retrieval)

## Objective
Deliver the unified scoring function that combines cosine similarity, salience subspace, and recency decay with bounded weights.

- Implement scorer strategy using MathService vectors, salience projections, and timestamps.
- Provide configuration for weights (w_cos, w_sub, w_rec, half_life) with validation.
- Instrument scoring pipeline with metrics and logging for observability.

## Scope Checklist

| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| Implement scorer strategy class | Platform | ☐ | Expose interface for pipeline orchestrator.
| Integrate salience projections (S^T q, Lambda z_i) | Platform | ☐ | Cache per item where possible.
| Add recency decay component with configurable half-life | Platform | ☐ | Ensure stability for long tails.
| Validate parameter bounds and tenant override schema | Architecture | ☐ | Add config tests.
| Instrument metrics (score breakdown, latency) | Observability | ☐ | Prometheus counters/histograms.
| Update documentation (retrieval design) | Docs | ☐ | Reference new scorer.
| Run evaluation benchmarks on recall quality | ML QA | ☐ | Compare to legacy scoring.

## Deliverables
- Unified scorer implementation with tests
- Config schema updates with validation
- Benchmark & evaluation report summarizing quality/latency

## Risks & Mitigations
- **Weight misconfiguration** -> Provide safe defaults, add guardrails to config loader.
- **Cache staleness** -> Invalidate on salience version bump; add monitoring.

## Exit Criteria
- Unified scorer running in shadow mode with metrics captured
- Configured weights validated across tenants
- Evaluation shows equal or improved recall quality vs baseline

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-10-13 | AI assistant | Created Sprint C1 canonical log. |

---

_Keep this document current throughout Sprint C1._
