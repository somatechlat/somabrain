# Sprint A2 – Observability Bedrock (Weeks 3-4)

> Canonical log for SomaBrain 3.0, Epic A (Foundations & Infrastructure)

## Objective
Upgrade observability so every subsequent epic can rely on consistent metrics, traces, and benchmark automation.

- Expand Prometheus metrics for latency, dependency install times, and feature flags.
- Wire structured logging context across services.
- Stand up benchmark CI pipeline (nightly + per-PR smoke) with artifacts.

## Scope Checklist

| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| Audit existing metrics and define new labels | Observability | ☐ | Document in metrics catalog.
| Implement logging context propagation (request ID, tenant) | Platform | ☐ | Cover FastAPI middleware + background tasks.
| Create CI job for nightly benchmarks | DevOps | ☐ | Attach artifacts to run.
| Add lightweight smoke benchmarks to PR workflow | DevOps | ☐ | Gate on threshold warnings.
| Document dashboards and alert thresholds | Docs | ☐ | Update `docs/observability.md`.
| Update Grafana dashboards with new panels | Observability | ☐ | Include dependency install duration.

## Deliverables
- Metrics catalog update
- Structured logging middleware + tests
- CI workflows for benchmarks (nightly + PR)
- Grafana dashboards refreshed with new panels

## Risks & Mitigations
- **Metric cardinality explosion** -> review label design, use allowlists.
- **Benchmark flakiness** -> capture variance, add retries or baselines.

## Exit Criteria
- New metrics visible in Prometheus and dashboards
- Benchmark CI jobs running successfully with stored artifacts
- Logging context verified via integration tests

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-10-13 | AI assistant | Created Sprint A2 canonical log. |

---

_Update status columns and change log entries as work progresses._
