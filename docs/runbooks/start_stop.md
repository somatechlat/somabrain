# Runbook: Service Start / Stop

This runbook describes how to start and stop the SomaBrain services in both **Docker‑Compose** and **Kubernetes** environments.

## Docker‑Compose

```bash
# Start all services (detached)
docker compose -f docker-compose.yml up -d

# Stop all services and clean up volumes
docker compose -f docker-compose.yml down --volumes --remove-orphans
```

### Individual services

```bash
# Start only the API service (useful for quick iteration)
docker compose -f docker-compose.yml up -d somabrain_app

# Stop a single service
docker compose -f docker-compose.yml stop somabrain_app
```

## Kubernetes

```bash
# Install or upgrade the Helm chart (namespace "soma-prod")
helm upgrade --install soma-prod ./charts/somabrain -n soma-prod -f values-prod.yaml
```

```bash
# Scale down (stop) all pods – set replica count to 0
helm upgrade soma-prod ./charts/somabrain -n soma-prod --set replicaCount=0
```

```bash
# Delete the release (full teardown)
helm uninstall soma-prod -n soma-prod
```

---

**Verification**: After start, ensure the health endpoint responds:

```bash
curl http://$APP_HOST:$APP_PORT/health
```

---
