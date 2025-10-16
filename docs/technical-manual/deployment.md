# Production Deployment Guide

**Purpose**: This document provides comprehensive instructions for deploying SomaBrain in production environments.

**Audience**: Platform engineers, SREs, and DevOps teams responsible for production deployments.

**Prerequisites**: Docker, Kubernetes, cloud platform access, and understanding of container orchestration.

---

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

#### Production Docker Compose
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  somabrain:
    image: somabrain:${SOMA_VERSION}
    restart: always
    environment:
      - SOMABRAIN_STRICT_REAL=1
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
- Helm 3.0+
- kubectl configured for target cluster
- Container registry access

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
  SOMABRAIN_STRICT_REAL: "1"
  SOMABRAIN_FORCE_FULL_STACK: "1"
  SOMABRAIN_REQUIRE_MEMORY: "1"
  SOMABRAIN_MODE: "production"
```

## Environment Configuration

### Required Environment Variables
| Variable | Production Value | Description |
|----------|-----------------|-------------|
| `SOMABRAIN_STRICT_REAL` | `1` | Enforce production-grade execution |
| `SOMABRAIN_FORCE_FULL_STACK` | `1` | Require all backing services |
| `SOMABRAIN_REQUIRE_MEMORY` | `1` | Memory service must be available |
| `SOMABRAIN_MODE` | `production` | Deployment mode identifier |
| `SOMABRAIN_REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `SOMABRAIN_POSTGRES_URL` | `postgresql://user:pass@host/db` | Database connection |
| `SOMABRAIN_KAFKA_BROKERS` | `kafka:9092` | Kafka broker endpoints |

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

### Grafana Dashboard Import
```bash
# Import SomaBrain dashboard
curl -X POST http://grafana:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${GRAFANA_TOKEN}" \
  -d @dashboards/somabrain-overview.json
```

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