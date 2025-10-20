# Security and Production Hardening

Baseline recommendations when deploying SomaBrain to production:

- Authentication
  - Set `SOMABRAIN_AUTH_REQUIRED=true` and distribute tokens via a secrets manager.
  - If fronted by an API gateway, enforce TLS and JWT verification upstream.

- Rate limits and quotas
  - Tune per-tenant `SOMABRAIN_RATE_RPS`/`SOMABRAIN_RATE_BURST` and `SOMABRAIN_WRITE_DAILY_LIMIT` based on traffic patterns.

- Secrets and config
  - Use environment variables or a secrets manager; do not bake secrets into images.
  - Use `config.yaml` for non-secrets only; keep per-environment overrides.

- Observability
  - Scrape `/metrics` with Prometheus; add dashboards for recall stages, predictor latency, HRR rerank, diversity, salience rates, and exec conflict.
  - Alert on p95 latency SLOs and error rates.

- Memory backend
  - Prefer HTTP mode for production and configure the remote memory API token.
  - Configure vector/graph indexes per `docs/INDEX_PROFILES.md`.

- Provenance and data hygiene
  - Set `SOMABRAIN_REQUIRE_PROVENANCE=true` in environments that import data.
  - Redact sensitive fields in logs; enable field-level encryption in the memory layer when needed.

- Network and runtime
  - Run containers as non-root with minimal base images (Dockerfiles provided are a starting point).
  - Keep FastAPI behind a reverse proxy/load balancer; use multiple workers if CPU-bound.

