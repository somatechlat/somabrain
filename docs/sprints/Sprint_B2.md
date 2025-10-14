# Sprint B2 – Vectorizer Fusion (Weeks 11-12)

> Canonical log for SomaBrain 3.0, Epic B (Math & Vectorizer Modernization)

## Objective
Deliver the fused surface+deep embedding pipeline with configurable weights and deterministic normalization.

- Implement hashed sparse encoder with Johnson-Lindenstrauss projection.
- Integrate deep model embeddings via linear projector into MathService.
- Provide tenant-configurable fusion weights (alpha, beta) with validation.

## Scope Checklist

| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| Implement hashed sparse encoder module | ML Platform | ☐ | Document tokenization and hash seeds.
| Add JL projection component with unit tests | ML Platform | ☐ | Ensure reproducibility across runs.
| Integrate deep embedding projector (matrix) | ML Platform | ☐ | Cache per-model weights.
| Implement fusion logic via MathService (`normalize(alpha*x_surface + beta*x_deep)`) | Platform | ☐ | Respect tenant overrides.
| Update configuration schema and validation | Architecture | ☐ | Add bounds for alpha/beta.
| Benchmark vectorizer latency & quality | Performance | ☐ | Compare to existing pipeline.
| Document vectorizer tuning guide | Docs | ☐ | Add to math playbook.

## Deliverables
- Fused Vectorizer implemented and exposed through MathService
- Configuration update with tenant overrides and defaults
- Benchmarks demonstrating latency/quality profile

## Risks & Mitigations
- **Hash collisions affecting recall** -> Evaluate with benchmark corpora, adjust density.
- **Model projector drift** -> Version projector matrices, add checksum verification.

## Exit Criteria
- Vectorizer fusion enabled in staging behind flag with positive metrics
- Config schema validated in CI, documentation published
- Legacy vectorizer can be toggled off without breaking tests

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-10-13 | AI assistant | Created Sprint B2 canonical log. |

---

_Update this document as Sprint B2 proceeds._
