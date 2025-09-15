Monitoring and local dev notes
==============================

This project includes a lightweight monitoring stack for local development and smoke testing. The compose file is at the repository root:

  - docker-compose.monitoring.yml

Prometheus configuration used by the compose file lives at:

  - docs/prometheus.yml

Quick start (local dev):

1. Start the monitoring stack (requires docker-compose):

   docker compose -f docker-compose.monitoring.yml up -d

2. Start the application (or rely on the image in the compose file). The smoke test script verifies readiness:

   ./scripts/smoke_test.sh http://127.0.0.1:9696

3. Grafana will be available at http://127.0.0.1:3000 (default credentials admin/admin for local images). Import the dashboard JSON in `ops/grafana/somabrain_minimal_dashboard.json` for a minimal overview.

Notes:
- The Prometheus config scrapes the application at host.docker.internal:9696 when run via docker-compose. On Linux you may need to replace `host.docker.internal` with the host IP or adjust the compose network.
- This README intentionally documents only non-production defaults. For production, use a hardened stack with TLS, authentication, and persistent volumes.
