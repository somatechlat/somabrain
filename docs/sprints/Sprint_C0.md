# Sprint C0 – Frequent-Directions Salience Core (Weeks 13-14)

> Canonical log for SomaBrain 3.0, Epic C (Salience & Retrieval)

## Objective
Implement the Frequent-Directions salience sketch to maintain PSD low-rank structure per tenant.

- Build salience service maintaining B in R^{r x D} with float64 precision.
- Support streaming updates with thin SVD shrink and subspace versioning.
- Expose APIs to retrieve (S, Lambda) and manage projection caches.

## Scope Checklist

| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| Implement salience sketch data structure | Platform | ☐ | Include persistence hooks.
| Add streaming update logic + thin SVD shrink | Platform | ☐ | Use numpy/scipy fallback.
| Design subspace versioning + cache invalidation | Platform | ☐ | Integrate with BrainState.
| Write analytical tests ensuring PSD and rank bounds | QA | ☐ | Include randomized checks.
| Integrate metrics for sketch size, update latency | Observability | ☐ | Add to Prometheus.
| Document salience architecture in math playbook | Docs | ☐ | Include diagrams.

## Deliverables
- Salience service module with unit/integration tests
- Metrics reporting for sketch operations
- Documentation covering Frequent-Directions usage

## Risks & Mitigations
- **SVD performance issues** -> Evaluate incremental SVD or approximations, set r accordingly.
- **Cache invalidation bugs** -> Use version tokens, property tests.

## Exit Criteria
- Salience sketch produces PSD subspace verified by tests
- Metrics visible for update latency and rank
- Service integrated behind feature flag with fallback to legacy salience

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-10-13 | AI assistant | Created Sprint C0 canonical log. |

---

_Update fields as Sprint C0 progresses._
