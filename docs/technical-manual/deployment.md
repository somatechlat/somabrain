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
- API: `9696`
- Redis: `20001`
- Kafka: `20002`
- Kafka Exporter: `20003`
- OPA: `20004`
- Prometheus: `20005`
- PostgreSQL: `20006`
- PostgreSQL Exporter: `20007`

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
cp .env.example .env.local
# Edit .env.local with production values

# Start services with dynamic port assignment
./scripts/dev_up.sh --rebuild

# Verify deployment
curl -fsS http://localhost:9696/health | jq
```

#### Direct Port Access (Local Parity)

The compose stack binds container ports directly to localhost for backend-enforcement parity:

| Service | Host Port | Notes |
| --- | --- | --- |
| SomaBrain API | 9696 | `http://localhost:9696` for health, metrics, OpenAPI |
| Redis | 6379 | `redis://localhost:6379/0` working-memory cache |
| Kafka | 9092 | Local bootstrap for audit/event streaming |
| Kafka Exporter | 9308 | Metrics endpoint for Kafka observability |
| OPA | 8181 | Policy decisions (`http://localhost:8181`) |
| Prometheus | 9090 | Monitoring UI and scrape target |
| Postgres | 5432 | Primary database access |
| Postgres Exporter | 9187 | Database metrics |

Use `./scripts/assign_ports.sh` when conflicts arise; it rewrites `.env.local` and `ports.json` with available values.

#### Docker Image Hardening Notes

- Multi-stage Dockerfile builds wheels and copies only runtime artefacts into a slim image.
- `.dockerignore` excludes tests, examples, build artefacts, and secrets to keep the context minimal.
- Runtime image includes `somabrain/`, `scripts/`, `arc_cache.py`, and documentation required at runtime.
- Containers run as a non-root user; ensure volumes and Kubernetes security contexts respect this constraint.

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

### PostgreSQL Setup
```sql
-- Create database and user
CREATE DATABASE somabrain;
CREATE USER somabrain WITH ENCRYPTED PASSWORD '${POSTGRES_PASSWORD}';
GRANT ALL PRIVILEGES ON DATABASE somabrain TO somabrain;

-- Apply migrations
\c somabrain
\i migrations/001_initial_schema.sql
\i migrations/002_audit_tables.sql
```

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
- All 9 services running and healthy
- Ports: 9696 (API), 20001-20007 (services)
- Configuration: Centralized in `.env` file
- Access: http://localhost:9696

**Kubernetes Deployment** ✅
- 6/8 services running (Kafka/Outbox need external memory)
- LoadBalancers: 20020 (API), 20021-20027 (services)
- Configuration: Centralized in ConfigMap/Secrets
- Access: kubectl port-forward or LoadBalancer

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
curl http://localhost:9696/health
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
