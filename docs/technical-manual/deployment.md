# Production Deployment Guide

**Purpose**: This document provides comprehensive instructions for deploying SomaBrain in production environments.

**Audience**: Platform engineers, SREs, and DevOps teams responsible for production deployments.

**Prerequisites**: Docker, Kubernetes, cloud platform access, and understanding of container orchestration.

---

## Centralized Configuration

**All configuration variables are centralized in `.env` file for Docker and ConfigMap for Kubernetes.**

### Development Credentials
⚠️ **WARNING: The following credentials are for DEVELOPMENT ONLY**

**MUST be changed before production deployment:**
- PostgreSQL: `POSTGRES_USER=soma`, `POSTGRES_PASSWORD=soma_dev_pass_CHANGE_IN_PRODUCTION`
- Memory Token: `SOMABRAIN_MEMORY_HTTP_TOKEN=dev-token-CHANGE_IN_PRODUCTION`
- JWT Secret: `SOMABRAIN_JWT_SECRET=dev-jwt-secret-CHANGE_IN_PRODUCTION`
- API Token: `SOMABRAIN_API_TOKEN=dev-api-token-CHANGE_IN_PRODUCTION`

### Port Assignments

**Docker Compose (localhost):**
Standard ports (host → container):
- API: `9999` → `9696`
- Redis: `30100` → `6379`
- Kafka (EXTERNAL): `30102` → `9094` (INTERNAL listener remains `9092`)
- Kafka Exporter: `30103` → `9308`
- OPA: `30104` → `8181`
- Prometheus: `30105` → `9090`
- PostgreSQL: `30106` → `5432`
- PostgreSQL Exporter: `30107` → `9187`

**Kubernetes (LoadBalancer):**
- API: `20020`
- Redis: `20021`
- Kafka: `20022`
- Kafka Exporter: `20023`
- OPA: `20024`
- Prometheus: `20025`
- PostgreSQL: `20026`
- PostgreSQL Exporter: `20027`

## Deployment Methods

### Docker Compose (Recommended for Development/Testing)

#### Quick Start
```bash
# Clone repository
git clone https://github.com/somatechlat/somabrain.git
cd somabrain

# Configure environment
cp .env.example .env
# Edit .env with environment-specific values

# Or generate a default .env and start
./scripts/generate_global_env.sh
docker compose --env-file ./.env -f docker-compose.yml up -d --build somabrain_app

# Alternatively, auto-assign free host ports in the 30000+ range
./scripts/dev_up.sh

# Verify deployment (unified /health endpoint)
curl -fsS http://localhost:9999/health | jq
```

#### Direct Port Access (Local Parity)

The compose stack binds container ports directly to localhost for backend-enforcement parity:

| Service | Host Port | Notes |
| --- | --- | --- |
| SomaBrain API | 9999 | `http://localhost:9999` for health, metrics, OpenAPI |
| Redis | 30100 | `redis://localhost:30100/0` working-memory cache |
| Kafka (EXTERNAL) | 30102 | Host bootstrap; INTERNAL remains `somabrain_kafka:9092` |
| Kafka Exporter | 30103 | Metrics endpoint for Kafka observability |
| OPA | 30104 | Policy decisions (`http://localhost:30104`) |
| Prometheus | 30105 | Monitoring UI and scrape target |
| Postgres | 30106 | Primary database access |
| Postgres Exporter | 30107 | Database metrics |

Use `./scripts/assign_ports.sh` when conflicts arise; it rewrites `.env` and `ports.json` with available values.

#### Docker Image Hardening Notes

- Multi-stage Dockerfile builds wheels and copies only runtime artefacts into a slim image.
- `.dockerignore` excludes tests, examples, build artefacts, and secrets to keep the context minimal.
- Runtime image includes `somabrain/`, `scripts/`, `arc_cache.py`, and documentation required at runtime.
- Containers run as a non-root user; ensure volumes and Kubernetes security contexts respect this constraint.
 - Compose hardening: `somabrain_app` drops all capabilities, uses a read-only root filesystem, enables `no-new-privileges`, and mounts `/app/logs` as tmpfs for write access.

#### Production Docker Compose
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  somabrain:
    image: somabrain:${SOMA_VERSION}
    restart: always
    environment:
      - SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1
      - SOMABRAIN_FORCE_FULL_STACK=1
      - SOMABRAIN_REQUIRE_MEMORY=1
      - SOMABRAIN_REDIS_URL=redis://redis:6379/0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9696/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    depends_on:
      - redis
      - postgres
      - kafka

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --maxmemory 8gb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  redis_data:
  postgres_data:
  kafka_data:
```

### Kubernetes Deployment

#### Prerequisites
- Kubernetes cluster (v1.24+)
- kubectl configured for target cluster
- Docker image built and loaded into cluster
- External memory service running on port 9595

#### Quick Deploy
```bash
# Build and load image
docker build -t somabrain:latest .
kind load docker-image somabrain:latest --name <cluster-name>

# Deploy with centralized configuration
kubectl apply -f k8s/somabrain-configmap.yaml
kubectl apply -f k8s/somabrain-deployment.yaml

# Check deployment status
kubectl get pods -n somabrain
kubectl get svc -n somabrain

# Access API
kubectl port-forward -n somabrain svc/somabrain-app 20020:9696
curl http://localhost:20020/health
```

#### Configuration Files

**ConfigMap** (`k8s/somabrain-configmap.yaml`):
- Contains all non-sensitive configuration
- Service URLs, ports, feature flags
- Kafka, Redis, PostgreSQL settings
- Resource limits and quotas

**Secrets** (`k8s/somabrain-configmap.yaml`):
- Database credentials (DEVELOPMENT ONLY)
- API tokens and JWT secrets
- ⚠️ **MUST be replaced with secure values in production**

**Deployment** (`k8s/somabrain-deployment.yaml`):
- All service deployments (Redis, Kafka, OPA, PostgreSQL, Prometheus)
- StatefulSets for stateful services
- LoadBalancer services for external access
- Health checks and resource limits

#### Helm Chart Deployment (Alternative)

#### Helm Chart Deployment
```bash
# Add SomaBrain Helm repository
helm repo add somabrain https://charts.somabrain.io
helm repo update

# Create namespace
kubectl create namespace somabrain-prod

# Deploy with production values
helm install somabrain-prod somabrain/somabrain \
  --namespace somabrain-prod \
  --values values.prod.yaml \
  --wait --timeout=10m

# Verify deployment
kubectl get pods -n somabrain-prod
kubectl get svc -n somabrain-prod
```

#### Production Values File (`values.prod.yaml`)
```yaml
# Helm values for production deployment
replicaCount: 3

image:
  repository: somabrain/somabrain
  tag: "v0.1.0"
  pullPolicy: IfNotPresent

service:
  type: LoadBalancer
  port: 80
  targetPort: 9696

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: api.somabrain.company.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: somabrain-tls
      hosts:
        - api.somabrain.company.com

resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

redis:
  enabled: true
  architecture: replication
  auth:
    enabled: true
  master:
    persistence:
      enabled: true
      size: 100Gi
  replica:
    replicaCount: 2

postgresql:
  enabled: true
  auth:
    database: somabrain
    username: somabrain
  primary:
    persistence:
      enabled: true
      size: 500Gi
    resources:
      requests:
        memory: "4Gi"
        cpu: "2000m"

kafka:
  enabled: true
  replicaCount: 3
  persistence:
    enabled: true
    size: 100Gi

prometheus:
  enabled: true
  server:
    retention: "30d"
    persistentVolume:
      size: 100Gi

environment:
  SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS: "1"
  SOMABRAIN_FORCE_FULL_STACK: "1"
  SOMABRAIN_REQUIRE_MEMORY: "1"
  SOMABRAIN_MODE: "production"
```

## Environment Configuration

### Centralized Configuration Location

**Docker Compose**: `.env` file in project root
**Kubernetes**: `somabrain-config` ConfigMap and `somabrain-secrets` Secret

### Required Environment Variables
| Variable | Development Value | Production Value | Description |
|----------|------------------|------------------|-------------|
| `SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS` | `1` | `1` | Enforce production-grade execution |
| `SOMABRAIN_FORCE_FULL_STACK` | `1` | `1` | Require all backing services |
| `SOMABRAIN_REQUIRE_MEMORY` | `1` | `1` | Memory service must be available |
| `SOMABRAIN_MODE` | `enterprise` | `production` | Deployment mode identifier |
| `SOMABRAIN_REDIS_URL` | `redis://somabrain-redis:6379/0` | `redis://redis:6379/0` | Redis connection string |
| `SOMABRAIN_POSTGRES_DSN` | `postgresql://soma:soma_dev_pass@somabrain-postgres:5432/somabrain` | `postgresql://user:CHANGE_ME@host/db` | Database connection |
| `SOMABRAIN_KAFKA_URL` | `kafka://somabrain-kafka:9092` | `kafka://kafka:9092` | Kafka broker endpoints |
| `SOMABRAIN_MEMORY_HTTP_ENDPOINT` | `http://host.docker.internal:9595` | `http://memory-service:9595` | Memory service endpoint |
| `POSTGRES_USER` | `soma` | **CHANGE IN PRODUCTION** | Database user |
| `POSTGRES_PASSWORD` | `soma_dev_pass` | **CHANGE IN PRODUCTION** | Database password |
| `SOMABRAIN_MEMORY_HTTP_TOKEN` | `dev-token` | **CHANGE IN PRODUCTION** | Memory service auth token |
| `SOMABRAIN_JWT_SECRET` | (unset) | **REQUIRED** | JWT signing key for API auth |
| `SOMABRAIN_API_TOKEN` | (unset) | **REQUIRED (or disable auth)** | Static API token if used |

### Security Configuration
```bash
# JWT authentication
export SOMABRAIN_JWT_SECRET="$(openssl rand -base64 32)"
export SOMABRAIN_JWT_ISSUER="somabrain-prod"
export SOMABRAIN_JWT_AUDIENCE="api.somabrain.company.com"

# OPA policy endpoint
export SOMABRAIN_OPA_ENDPOINT="http://opa:8181"

# Rate limiting
export SOMABRAIN_RATE_RPS="100"
export SOMABRAIN_RATE_BURST="200"
export SOMABRAIN_WRITE_DAILY_LIMIT="50000"
```

## Infrastructure Setup

### Redis Configuration
```bash
# Redis production configuration
redis-server --config /etc/redis/redis.conf \
  --maxmemory 8gb \
  --maxmemory-policy allkeys-lru \
  --save 900 1 \
  --appendonly yes \
  --appendfsync everysec \
  --bind 0.0.0.0 \
  --protected-mode yes \
  --requirepass ${REDIS_PASSWORD}
```

### Database Setup & Migrations

Create the database and user with your preferred method (manually or via IaC), then apply Alembic migrations. For Docker Compose dev stacks, use the one-shot migration job:

```bash
# Dev: apply Alembic migrations
./scripts/migrate_db.sh            # or: docker compose --profile dev run --rm somabrain_db_migrate
```

Notes:
- The one-shot job targets the internal Postgres host `somabrain_postgres` and runs `alembic upgrade heads`.
- If the schema already exists without Alembic history (legacy DB), the dev job automatically stamps heads to align. Do not use stamping in production.
- For production/staging, run migrations explicitly in CI/CD or via a controlled job (no auto-stamp), and keep `SOMABRAIN_AUTO_MIGRATE=0`.
- The API entrypoint supports a dev-only auto-migrate hook when `SOMABRAIN_AUTO_MIGRATE=1`, running `alembic upgrade heads` on startup. Prefer the one-shot job instead.

### Kafka Topics
```bash
# Create required Kafka topics
kafka-topics.sh --create --topic audit.operations \
  --bootstrap-server localhost:9092 \
  --partitions 6 --replication-factor 3

kafka-topics.sh --create --topic audit.events \
  --bootstrap-server localhost:9092 \
  --partitions 3 --replication-factor 3

kafka-topics.sh --create --topic metrics.streams \
  --bootstrap-server localhost:9092 \
  --partitions 3 --replication-factor 3
```

## Deployment Verification

### Health Check Validation
```bash
# Basic health check
curl -f http://api.somabrain.company.com/health

# Expected response (200 OK)
{
  "status": "healthy",
  "timestamp": "2025-10-15T12:00:00Z",
  "components": {
    "redis": {"status": "healthy", "latency_ms": 1.2},
    "postgres": {"status": "healthy", "latency_ms": 2.1},
    "kafka": {"status": "healthy", "latency_ms": 0.8},
    "opa": {"status": "healthy", "latency_ms": 1.0}
  },
  "version": "v0.1.0",
  "mode": "production"
}
```

### Metrics Validation
```bash
# Verify Prometheus metrics endpoint
curl -s http://api.somabrain.company.com/metrics | grep somabrain

# Expected metrics
# somabrain_requests_total{method="GET",endpoint="/health"} 1
# somabrain_request_duration_seconds_bucket{method="GET",endpoint="/health",le="0.1"} 1
# somabrain_density_trace_error_total 0
```

### Functional Testing
```bash
# Test memory operations
curl -X POST http://api.somabrain.company.com/remember \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -d '{
    "content": "Test memory for production deployment",
    "metadata": {"test": true, "deployment": "production"}
  }'

# Test recall
curl -X POST http://api.somabrain.company.com/recall \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -d '{
    "query": "test memory",
    "k": 5
  }'
```

## Monitoring Setup

### Prometheus Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "somabrain-alerts.yml"

scrape_configs:
  - job_name: 'somabrain'
    static_configs:
      - targets: ['somabrain:9696']
    metrics_path: /metrics
    scrape_interval: 5s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:9121']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
```

<!-- Dashboard import instructions deleted. -->

> Linux hosts: If running Prometheus inside Docker on Linux, `host.docker.internal` may not resolve by default. Options:
> - Run Prometheus with host networking and scrape `localhost:PORT`.
> - Add `--add-host=host.docker.internal:host-gateway` to the Prometheus container (compose `extra_hosts`).
> - Expose scrape targets inside the compose network and reference service names.

## Backup & Recovery Setup

### Automated Backup Script
```bash
#!/bin/bash
# backup-somabrain.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/somabrain/$DATE"
mkdir -p "$BACKUP_DIR"

# Redis backup
redis-cli --rdb "$BACKUP_DIR/redis.rdb"

# PostgreSQL backup
pg_dump -h postgres -U somabrain somabrain > "$BACKUP_DIR/postgres.sql"

# Configuration backup
kubectl get configmap somabrain-config -o yaml > "$BACKUP_DIR/config.yaml"

# Upload to object storage
aws s3 cp "$BACKUP_DIR" s3://company-backups/somabrain/ --recursive

# Retention cleanup (keep 30 days)
find /backups/somabrain -type d -mtime +30 -exec rm -rf {} \;
```

### Backup Verification
```bash
# Schedule backup verification
0 2 * * * /scripts/backup-somabrain.sh
0 4 * * 0 /scripts/verify-backup.sh

# Test restore procedure monthly
0 6 1 * * /scripts/test-restore.sh
```

## Scaling Considerations

### Maximum capacity configuration (production)

For sustained peak throughput and lowest tail latency, configure the platform with these proven settings:

- API process
  - Replicas: 4–8 behind a load balancer (HPA min 4, max 20)
  - Concurrency: uvicorn workers = CPU cores (2–4 per pod) with keep-alive 75s; enable HTTP pipelining at the ingress
  - ENABLE_COG_THREADS: "1" across all cognitive services to keep the pipeline always-on
  - OPA policy: mount policies from ops/opa/policies and run OPA fail-closed (mode_opa_fail_closed=true)
  - Auth: mode_api_auth_enabled=true (JWT recommended) and rate limits tuned per tenant

- Kafka
  - Partitions: 12+ for audit and cognition topics to avoid producer backpressure
  - Acks: all; linger.ms ~ 5–10ms for better batching under load
  - Exporter enabled and scraped every 30s for saturation alerts

- Redis
  - Maxmemory: 8–16GiB with allkeys-lru; persistent snapshot + AOF for durability
  - Use SOMABRAIN_REDIS_URL with pooled connections; pin CPU/memory in k8s

- PostgreSQL
  - Instance RAM: 8–16GiB; shared_buffers ~ 25% RAM; effective_cache_size ~ 60% RAM
  - WAL on fast storage; enable pg_stat_statements and exporter
  - Read replicas for reporting; primary reserved for writes and hot data

- Prometheus/Alertmanager
  - Retention: 15–30d; persistent volumes sized for retention targets
  - PodMonitors for all components; alerts for API p95>2s, error rate>5%, memory>85%

- OPA
  - Serve on 8181, policies under ops/opa/policies; bundle or ConfigMap sync
  - Enforce fail-closed in production; add liveness/readiness probes

Operational flags to set in Helm values or environment:
- SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1
- SOMABRAIN_FORCE_FULL_STACK=1
- SOMABRAIN_REQUIRE_MEMORY=1
- ENABLE_COG_THREADS=1

Capacity tips:
- Scale API first; Kafka partitions next; then Redis memory. Validate with load tests and Prometheus SLOs.
- Keep Prometheus retention manageable; ship long-term metrics to a remote store if needed.

### Horizontal Pod Autoscaler (HPA)
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: somabrain-hpa
  namespace: somabrain-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: somabrain
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Database Scaling
```yaml
# PostgreSQL read replicas
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: somabrain-db
spec:
  instances: 3
  postgresql:
    parameters:
      max_connections: "200"
      shared_buffers: "256MB"
      effective_cache_size: "1GB"
  monitoring:
    enabled: true
```

## Troubleshooting

### Common Deployment Issues

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Health check fails | 503 responses from `/health` | Verify Redis/Postgres connectivity |
| Memory operations timeout | Slow `/remember` responses | Check memory service endpoint configuration |
| Authentication errors | 401/403 responses | Validate JWT secret and OPA policies |
| Resource constraints | Pod restarts, OOMKilled | Increase memory/CPU limits |

### Log Analysis
```bash
# Check application logs
kubectl logs -f deployment/somabrain -n somabrain-prod

# Filter for errors
kubectl logs deployment/somabrain -n somabrain-prod | grep "ERROR\|FATAL"

# Check resource usage
kubectl top pods -n somabrain-prod
```

### Performance Tuning
```bash
# Monitor metrics for tuning
curl -s http://api.somabrain.company.com/metrics | grep -E "latency|memory|cpu"

# Adjust resource limits based on metrics
kubectl patch deployment somabrain -n somabrain-prod -p '{"spec":{"template":{"spec":{"containers":[{"name":"somabrain","resources":{"limits":{"memory":"8Gi","cpu":"4000m"}}}]}}}}'
```

## Deployment Summary

### Current Deployment Status

**Docker Compose Deployment** ✅
- All services running and healthy (API + Redis/Kafka/OPA/Postgres/Prometheus)
- Ports: 9999 (API), 30100–30108 (services)
- Configuration: Centralized in `.env` file
- Access: http://localhost:9999

**Kubernetes Deployment** ✅
- Helm charts are canonical (`infra/helm/charts/soma-infra` and `soma-apps`)
- External access via NodePort/Ingress; defaults in `soma-apps/values.yaml`
- Configuration: Centralized in ConfigMap/Secrets
- Access: kubectl port-forward or Ingress/Service

### Configuration Files

**Docker:**
- `.env` - All environment variables
- `docker-compose.yml` - Service definitions

**Kubernetes:**
- `k8s/somabrain-configmap.yaml` - ConfigMap and Secrets
- `k8s/somabrain-deployment.yaml` - All service deployments

### Quick Access Commands

**Docker:**
```bash
# Start cluster
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f somabrain_app

# Access API
curl http://localhost:9999/health
```

**Kubernetes:**
```bash
# Deploy
kubectl apply -f k8s/somabrain-configmap.yaml
kubectl apply -f k8s/somabrain-deployment.yaml

# Check status
kubectl get pods -n somabrain

# View logs
kubectl logs -f deployment/somabrain-app -n somabrain

# Access API
kubectl port-forward -n somabrain svc/somabrain-app 20020:9696
curl http://localhost:20020/health
```

### Production Checklist

Before deploying to production, ensure:

- [ ] Change all development credentials in ConfigMap/Secrets
- [ ] Update `POSTGRES_PASSWORD` from `soma_dev_pass`
- [ ] Update `SOMABRAIN_MEMORY_HTTP_TOKEN` from `dev-token`
- [ ] Update `SOMABRAIN_JWT_SECRET` from development value
- [ ] Update `SOMABRAIN_API_TOKEN` from development value
- [ ] Configure TLS certificates for external access
- [ ] Set up monitoring and alerting
- [ ] Configure backup procedures
- [ ] Review and update resource limits
- [ ] Enable authentication and authorization
- [ ] Configure network policies
- [ ] Set up log aggregation
- [ ] Test disaster recovery procedures

---

**Verification**: Complete deployment verification checklist before declaring production ready.

**Common Errors**:
- Image pull failures → Verify registry credentials and image tags
- Service discovery issues → Check DNS configuration and service names
- Persistent volume failures → Validate storage class and PVC configurations

**References**:
- [Architecture Overview](architecture.md) for system design understanding
- [Monitoring Guide](monitoring.md) for observability setup
- [Security Configuration](security/) for hardening procedures
- [Runbooks](runbooks/) for operational procedures

---

### Kafka EXTERNAL listener (WSL2/remote clients)
By default, Kafka’s EXTERNAL listener is advertised as `localhost:${KAFKA_BROKER_HOST_PORT}` for host clients. For remote clients or WSL2, set the host/IP before running `scripts/dev_up.sh`:

```bash
KAFKA_EXTERNAL_HOST=192.168.1.10 ./scripts/dev_up.sh
```

### Cognitive-thread services in Compose
CI exercises additional services (predictors, integrator, segmentation, orchestrator, learner). For local experimentation with the predictors that live in this repo, use the optional overlay file `docker-compose.cog.yml`:

```bash
docker compose -f docker-compose.yml -f docker-compose.cog.yml up -d --build \
  somabrain_predictor_state somabrain_predictor_agent somabrain_predictor_action
```

### OPA policies
The dev policy at `ops/opa/policies/example.rego` is permissive. For production, use the deny-by-default example under `ops/opa/policies-prod/default.rego` and configure OPA to load that directory.
