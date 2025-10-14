# Sprint C2 – Retrieval Pipeline Orchestration (Weeks 17-18)

> Canonical log for SomaBrain 3.0, Epic C (Salience & Retrieval)

## Objective
Refactor the retrieval stack into a staged pipeline with clear adapters, caching, and observability.

- Split MemoryClient into transport adapters (HTTP, mirror, outbox) with shared interfaces.
- Implement pipeline orchestrator coordinating prefilter, remote recall, scoring, and caching.
- Expose per-stage metrics and controls for experimentation.

## Scope Checklist

| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| Extract MemoryClient adapters (transport, mirror, outbox) | Platform | ☐ | Maintain legacy API via facade.
| Implement retrieval pipeline orchestrator | Platform | ☐ | Compose stages (prefilter, recall, scorer, cache).
| Add caching layer with configurable TTL per tenant | Platform | ☐ | Include warming strategy.
| Instrument metrics per stage (latency, hit source) | Observability | ☐ | Export to Prometheus.
| Integrate unified scorer from Sprint C1 | Platform | ☐ | Ensure pluggable strategy.
| Update documentation with pipeline diagrams | Docs | ☐ | Include failure/rollback paths.
| Run load/stress benchmarks | Performance | ☐ | Validate throughput and tail latency.

## Deliverables
- Modular retrieval pipeline implementation
- Metrics dashboards showing stage breakdown
- Benchmark report covering load and stress scenarios

## Risks & Mitigations
- **Adapter regressions** -> Provide integration tests using stub services.
- **Cache inconsistencies** -> Use tenant namespaces, add expiry monitoring.

## Exit Criteria
- Pipeline enabled in staging under feature flag
- Metrics dashboards confirm expected stage behavior
- Load tests meet latency and throughput targets

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-10-13 | AI assistant | Created Sprint C2 canonical log. |

---

_Update status and change log entries as Sprint C2 advances._
