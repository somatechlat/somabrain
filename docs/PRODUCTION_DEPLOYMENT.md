# SomaBrain Production Deployment Guide

This document provides comprehensive documentation for the production-grade deployment of SomaBrain, covering both Docker Compose development stacks and Kubernetes production environments with proper TLS termination, ingress, and shared infrastructure alignment.

## Architecture Overview

SomaBrain follows a microservices architecture with clear separation between the core brain API and supporting infrastructure services. The deployment supports two primary modes:

1. **Docker Compose Stack** (Development/Testing) - Port 9696
2. **Kubernetes Cluster** (Production) - Port 9999 via Ingress

## Shared Infrastructure Services

Based on the current architecture design, the following shared services are standardized across both deployment modes:

### Core Infrastructure Components

| Service | Docker Image | Docker Port | K8s Service | K8s Port | Purpose |
|---------|--------------|-------------|-------------|----------|---------|
| **Redis** | `redis:7.2-alpine` | `6379` | `sb-redis.somabrain-prod.svc.cluster.local` | `6379` | Cache, rate limiting, working memory |
| **Kafka** | `bitnami/kafka:latest` | `9092` | External (not in current K8s manifest) | `9092` | Event streaming, audit pipeline |
| **OPA** | `openpolicyagent/opa:0.48.0` | `8181` | `sb-opa.somabrain-prod.svc.cluster.local` | `8181` | Policy enforcement engine |
| **Prometheus** | `prom/prometheus:v2.49.0` | `9090` | External (monitoring stack) | `9090` | Metrics collection |
| **Postgres** | `postgres:15-alpine` | `5432` | `postgres.somabrain-prod.svc.cluster.local` | `5432` | Persistent data storage |
| **SomaMemory** | `python:3.13-slim` (runtime) | `9595` | `somamemory.somabrain-prod.svc.cluster.local` | `9595` | External memory service |

### Network Connectivity Matrix

#### Docker Compose Network Configuration
```yaml
# Internal service-to-service communication
SOMABRAIN_REDIS_URL: "redis://sb_redis:6379/0"
SOMABRAIN_KAFKA_URL: "kafka://kafka:9092" 
SOMABRAIN_OPA_URL: "http://sb_opa:8181"
SOMABRAIN_POSTGRES_DSN: "postgresql://soma:soma_pass@sb_postgres:5432/somabrain"
SOMABRAIN_MEMORY_HTTP_ENDPOINT: "http://host.docker.internal:9595"
```

#### Kubernetes Cluster DNS Configuration
```yaml
# Fully qualified cluster DNS names
SOMABRAIN_REDIS_URL: "redis://sb-redis.somabrain-prod.svc.cluster.local:6379/0"
SOMABRAIN_OPA_URL: "http://sb-opa.somabrain-prod.svc.cluster.local:8181"
SOMABRAIN_POSTGRES_DSN: "postgresql://somabrain:somabrain-dev-password@postgres.somabrain-prod.svc.cluster.local:5432/somabrain"
SOMABRAIN_MEMORY_HTTP_ENDPOINT: "http://somamemory.somabrain-prod.svc.cluster.local:9595"
```

## Docker Compose Development Stack

### Port Allocation Strategy
The `scripts/dev_up.sh` script automatically detects free ports and generates `.env.local`:

```bash
# Standard port assignments (when available)
SOMABRAIN_HOST_PORT=9696      # Main API endpoint
REDIS_HOST_PORT=6379          # Redis cache
KAFKA_HOST_PORT=9092          # Kafka broker  
PROMETHEUS_HOST_PORT=9090     # Metrics
POSTGRES_HOST_PORT=15432      # Database (host port differs to avoid conflicts)
```

### Service Dependencies
```yaml
# Dependency chain in Docker Compose
somabrain:
  depends_on:
    - redis (service_started)
    - kafka (service_started) 
    - opa (service_started)
    - postgres (service_started)
```

### Volume Persistence
```yaml
volumes:
  postgres_data: # Persistent PostgreSQL data
  kafka_data:    # Kafka log segments
  redis_data:    # Redis persistence (if enabled)
```

## Kubernetes Production Deployment

### Namespace and Resource Organization
```yaml
namespace: somabrain-prod
resources:
  - ConfigMap: somabrain-env (environment variables)
  - ConfigMap: somabrain-overrides (runtime patches)
  - Secret: somabrain-secrets (credentials, JWT keys)
  - Secret: somabrain-postgres (database credentials)
  - PVC: somabrain-outbox-pvc (persistent outbox storage)
```

### Production-Grade Ingress and TLS

#### LoadBalancer Service (External Access)
```yaml
apiVersion: v1
kind: Service
metadata:
  name: somabrain-public
  namespace: somabrain-prod
spec:
  type: LoadBalancer
  ports:
    - name: http-external
      port: 9999           # External production port
      targetPort: 9696     # Internal container port
  selector:
    app: somabrain
```

#### Nginx Ingress Configuration
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: somabrain
  namespace: somabrain-prod
  annotations:
    nginx.ingress.kubernetes.io/backend-protocol: "HTTP"
    nginx.ingress.kubernetes.io/proxy-body-size: "32m"
spec:
  ingressClassName: nginx
  tls:
    - hosts: [somabrain.internal]
      secretName: somabrain-tls
  rules:
    - host: somabrain.internal
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: somabrain
                port: { number: 9696 }
```

#### TLS Certificate Management
```bash
# Generate and install TLS certificates
./scripts/setup_ingress_tls.sh

# Generated files
infra/tls/somabrain.internal.crt  # Public certificate
infra/tls/somabrain.internal.key  # Private key

# Kubernetes secret
kubectl get secret somabrain-tls -n somabrain-prod
```

### StatefulSet Services

#### PostgreSQL Database
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres
  replicas: 1
  volumeClaimTemplates:
    - metadata: { name: postgres-data }
      spec:
        accessModes: [ReadWriteOnce]
        resources: { requests: { storage: 10Gi }}
```

#### Redis Cache
```yaml  
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sb-redis
spec:
  template:
    spec:
      containers:
        - name: redis
          image: redis:7.2
          ports: [{ containerPort: 6379 }]
```

## Environment Configuration Matrix

### Strict Real Mode Settings
Both deployment modes enforce production-grade settings:

```yaml
# Shared strict-real configuration
SOMABRAIN_STRICT_REAL: "1"           # No stub components
SOMABRAIN_FORCE_FULL_STACK: "1"      # Require all services
SOMABRAIN_REQUIRE_MEMORY: "1"        # Memory service mandatory
SOMABRAIN_ENABLE_BEST: "1"           # Production optimizations
SOMABRAIN_PREDICTOR_PROVIDER: "mahal" # Real predictor (not stub)
```

### Security and Authentication
```yaml
# Development (Docker)
SOMABRAIN_DISABLE_AUTH: "1"    # Simplified auth for dev

# Production (Kubernetes) 
SOMABRAIN_DISABLE_AUTH: "0"    # Full JWT validation
SOMABRAIN_JWT_PUBLIC_KEY_PATH: "/secrets/jwt_pub.pem"
SOMABRAIN_JWT_ISSUER: "production-issuer"
SOMABRAIN_JWT_AUDIENCE: "somabrain-api"
```

## Access Patterns and Port Forwarding

### Local Development Access
```bash
# Docker Compose - direct host access
curl http://localhost:9696/health

# Kubernetes - port forwarding required
kubectl port-forward -n somabrain-prod svc/somabrain 9696:9696
curl http://localhost:9696/health
```

### Production Access via Ingress
```bash
# HTTPS via ingress controller (production path)
kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 9999:80
curl -sk --resolve somabrain.internal:9999:127.0.0.1 https://somabrain.internal:9999/health

# Add to /etc/hosts for local testing:
echo "127.0.0.1 somabrain.internal" >> /etc/hosts
```

### Multi-Service Port Forwarding
```bash
# Forward all services for integration testing
kubectl port-forward -n somabrain-prod svc/somabrain 9696:9696 &
kubectl port-forward -n somabrain-prod svc/somamemory 9595:9595 &  
kubectl port-forward -n somabrain-prod svc/sb-redis 6379:6379 &
kubectl port-forward -n somabrain-prod svc/postgres 55432:5432 &
kubectl port-forward -n somabrain-prod svc/sb-opa 8181:8181 &
```

## Health Check and Readiness Validation

### Service Health Endpoints
```bash
# Primary health check
curl http://localhost:9696/health

# Memory service health  
curl http://localhost:9595/health

# Expected health response
{
  "ok": true,
  "components": {
    "memory": {"http": true},
    "wm_items": "tenant-scoped"
  },
  "predictor_provider": "mahal",
  "strict_real": true,
  "ready": true
}
```

### Readiness Requirements
- Non-stub predictor provider (`mahal` not `stub`)
- External memory service reachable
- Database connectivity established
- Redis cache operational
- OPA policy engine responsive (if fail-closed mode)

## Resource Requirements and Scaling

### Docker Compose Resources
```yaml
# Typical development resource usage
somabrain: ~500MB RAM, 1 CPU core
postgres:  ~256MB RAM, 0.2 CPU
redis:     ~64MB RAM, 0.1 CPU  
kafka:     ~512MB RAM, 0.5 CPU
```

### Kubernetes Resource Limits
```yaml
# Production resource specifications
somabrain:
  requests: { cpu: "500m", memory: "1Gi" }
  limits:   { cpu: "1200m", memory: "2Gi" }
postgres:
  requests: { cpu: "50m", memory: "128Mi" }  
  limits:   { cpu: "200m", memory: "256Mi" }
redis:
  requests: { cpu: "50m", memory: "64Mi" }
  limits:   { cpu: "200m", memory: "256Mi" }
```

## Migration and Upgrade Procedures

### Docker to Kubernetes Migration
1. Export existing data from Docker volumes
2. Create PVCs in Kubernetes cluster  
3. Import data to persistent volumes
4. Apply K8s manifests with matching configuration
5. Verify service connectivity and health

### Rolling Updates
```bash
# Update somabrain deployment
kubectl set image deployment/somabrain -n somabrain-prod \
  somabrain=somabrain:v2.0.0

# Monitor rollout status  
kubectl rollout status deployment/somabrain -n somabrain-prod

# Rollback if needed
kubectl rollout undo deployment/somabrain -n somabrain-prod
```

## Security Considerations

### Network Policies
```yaml
# Isolate somabrain-prod namespace traffic
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: somabrain-isolation
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
    - from: [{ namespaceSelector: { matchLabels: { name: somabrain-prod }}}]
  egress:
    - to: [{ namespaceSelector: { matchLabels: { name: somabrain-prod }}}]
```

### Secret Management
```bash
# Rotate database credentials
kubectl create secret generic somabrain-postgres-new \
  --from-literal=POSTGRES_PASSWORD=new-secure-password

# Update deployment reference
kubectl patch deployment postgres -n somabrain-prod \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"postgres","envFrom":[{"secretRef":{"name":"somabrain-postgres-new"}}]}]}}}}'
```

## Monitoring and Observability

### Prometheus Metrics Collection
```yaml
# Service monitor for metrics scraping
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor  
metadata:
  name: somabrain-metrics
spec:
  selector:
    matchLabels: { app: somabrain }
  endpoints:
    - port: http
      path: /metrics
      interval: 30s
```

### Log Aggregation
```bash
# View aggregated logs
kubectl logs -f deployment/somabrain -n somabrain-prod
kubectl logs -f deployment/sb-redis -n somabrain-prod  
kubectl logs -f statefulset/postgres -n somabrain-prod
```

## Troubleshooting Guide

### Common Issues and Resolution

#### Service Discovery Problems
```bash
# Check service DNS resolution
kubectl exec -it deployment/somabrain -n somabrain-prod -- \
  nslookup sb-redis.somabrain-prod.svc.cluster.local

# Verify service endpoints
kubectl get endpoints -n somabrain-prod
```

#### Memory Service Connectivity
```bash
# Test memory service from somabrain pod
kubectl exec -it deployment/somabrain -n somabrain-prod -- \
  curl http://somamemory.somabrain-prod.svc.cluster.local:9595/health
```

#### TLS Certificate Issues  
```bash
# Verify TLS secret contents
kubectl get secret somabrain-tls -n somabrain-prod -o yaml

# Test certificate validity
openssl x509 -in infra/tls/somabrain.internal.crt -text -noout
```

This deployment architecture ensures production parity between development and production environments while maintaining clear service boundaries and proper security controls.