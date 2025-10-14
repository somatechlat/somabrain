# Sprint B1 – Composer Rollout (Weeks 9-10)

> Canonical log for SomaBrain 3.0, Epic B (Math & Vectorizer Modernization)

## Objective
Deploy the new deterministic Composer (Rademacher masks + permutations) behind feature flags and validate performance in staging.

- Implement mask/permutation generation per tenant (seeded by tenant and model version).
- Provide bind/unbind implementations using elementwise ops with optional permutation.
- Benchmark vs legacy FFT-based path and record metrics.

## Scope Checklist

| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| Implement mask/permutation generator service | Platform | ☐ | Cache results for reuse.
| Integrate Composer into MathService behind `math.composer.v1` flag | Platform | ☐ | Fallback to legacy when disabled.
| Create benchmarks (throughput, latency, memory) | Performance | ☐ | Include O(D) confirmation.
| Validate statistical properties (zero-mean noise, invertibility) | QA | ☐ | Analytical + empirical tests.
| Roll out to staging tenant(s) under supervision | Ops | ☐ | Collect metrics for 48 hours.
| Update math playbook with Composer details | Docs | ☐ | Include parameterization guidance.

## Deliverables
- New Composer implementation wired via MathService
- Benchmark report and staging run analysis
- Documentation updates referencing Composer

## Risks & Mitigations
- **Permutation overhead** -> optimize caching, allow no-permutation mode for tiny dims.
- **Unexpected collisions across tenants** -> add seed audit logging, verification tests.

## Exit Criteria
- Composer enabled in staging without regressions
- Benchmarks show improved or equivalent performance vs FFT path
- Documentation reviewed by math leads

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-10-13 | AI assistant | Created Sprint B1 canonical log. |

---

_Maintain status entries as tasks progress._
