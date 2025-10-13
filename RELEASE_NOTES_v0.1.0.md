> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# SomaBrain v0.1.0

Observable memory API (HRR + typed links) with multi-tenancy and Prometheus metrics.

## Quickstart

```bash
docker run --rm \
  -p 8000:9696 \
  -e SOMABRAIN_DISABLE_AUTH=true \
  ghcr.io/somatechlat/somabrain:latest
```

Then:
- Health: curl -s http://localhost:8000/health
- OpenAPI: http://localhost:8000/docs
- Metrics: http://localhost:8000/metrics

## Endpoints
- `/remember`, `/recall`, `/link`, `/docs` (OpenAPI), `/metrics` (Prometheus)

## Security
- Token auth via `Authorization: Bearer <token>` (set `SOMABRAIN_API_TOKEN` to enable)
- Tenancy via `X-Tenant-ID`
- For public demos, you can keep `SOMABRAIN_DISABLE_AUTH=true`; for real deployments enable auth.

## Observability
- One command (Prometheus only):
  ```bash
  docker compose -f docker-compose.observability.yml up
  ```
- Prometheus UI: http://localhost:9090

## Known limits (initial)
- Bounded working memory; tune dimensions with env vars.
- Rate/size limits recommended at front proxy.
