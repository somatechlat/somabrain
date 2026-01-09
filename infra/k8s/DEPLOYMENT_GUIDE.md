# SomaBrain Kubernetes Deployment Guide

**Document ID**: SOMA-DEPLOY-K8S-001  
**Version**: 1.0.0  
**Last Updated**: 2026-01-09  
**Status**: Template (K8s manifests pending)

---

## 1. Overview

This guide provides step-by-step instructions for deploying SomaBrain to Kubernetes. The deployment uses Kustomize for environment-specific configurations.

### 1.1 Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Kubernetes | 1.27+ | 1.29+ |
| kubectl | 1.27+ | 1.29+ |
| Helm | 3.12+ | 3.14+ |
| RAM (cluster) | 16GB | 32GB |
| Nodes | 3 | 5+ |

### 1.2 Cluster Requirements

- **Ingress Controller**: nginx-ingress or traefik
- **Storage Class**: Standard or SSD-backed persistent volumes
- **DNS**: External DNS for service discovery
- **TLS**: cert-manager for certificate management

---

## 2. Quick Start

### Step 1: Configure kubectl Context

```bash
# Verify cluster access
kubectl cluster-info
kubectl get nodes
```

### Step 2: Create Namespace

```bash
kubectl create namespace somabrain
kubectl config set-context --current --namespace=somabrain
```

### Step 3: Deploy with Kustomize

```bash
cd /path/to/somabrain/infra/k8s

# Apply base configuration
kubectl apply -k base/

# Or apply environment-specific overlay
kubectl apply -k overlays/production/
```

### Step 4: Verify Deployment

```bash
# Check pod status
kubectl get pods -n somabrain

# Check services
kubectl get svc -n somabrain

# Port-forward to test
kubectl port-forward svc/somabrain-api 30101:9696 -n somabrain
curl http://localhost:30101/healthz
```

---

## 3. Directory Structure

```
infra/k8s/
├── base/
│   ├── kustomization.yaml
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ingress.yaml
├── overlays/
│   ├── development/
│   │   └── kustomization.yaml
│   ├── staging/
│   │   └── kustomization.yaml
│   └── production/
│       ├── kustomization.yaml
│       └── patches/
└── DEPLOYMENT_GUIDE.md
```

---

## 4. Configuration

### 4.1 ConfigMap (Non-Sensitive)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: somabrain-config
data:
  SOMABRAIN_MODE: "production"
  SOMABRAIN_HOST: "0.0.0.0"
  SOMABRAIN_PORT: "9696"
  KAFKA_BOOTSTRAP_SERVERS: "kafka.somabrain.svc:9092"
  MILVUS_HOST: "milvus.somabrain.svc"
  MILVUS_PORT: "19530"
```

### 4.2 Secrets (Sensitive)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: somabrain-secrets
type: Opaque
stringData:
  POSTGRES_PASSWORD: "<secure-password>"
  REDIS_PASSWORD: "<secure-password>"
  SOMABRAIN_POSTGRES_DSN: "postgresql://somabrain:<password>@postgres:5432/somabrain"
```

### 4.3 Resource Limits

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

---

## 5. Helm Charts (Alternative)

For production deployments, use Helm charts for dependency management:

```bash
# Add SomaTech Helm repo
helm repo add somatech https://charts.somatech.lat
helm repo update

# Install SomaBrain
helm install somabrain somatech/somabrain \
  --namespace somabrain \
  --create-namespace \
  --values values-production.yaml
```

---

## 6. Health Probes

### 6.1 Liveness Probe

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 9696
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

### 6.2 Readiness Probe

```yaml
readinessProbe:
  httpGet:
    path: /readyz
    port: 9696
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3
```

---

## 7. Monitoring

### 7.1 Prometheus ServiceMonitor

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: somabrain
spec:
  selector:
    matchLabels:
      app: somabrain
  endpoints:
    - port: metrics
      path: /metrics
      interval: 30s
```

### 7.2 Grafana Dashboard

Import dashboard ID `SOMA-BRAIN-001` from the Grafana marketplace.

---

## 8. Scaling

### 8.1 Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: somabrain-api
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: somabrain-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

---

## 9. Troubleshooting

### 9.1 Common Issues

```bash
# Check pod events
kubectl describe pod <pod-name> -n somabrain

# View logs
kubectl logs -f deployment/somabrain-api -n somabrain

# Shell into pod
kubectl exec -it <pod-name> -n somabrain -- /bin/bash
```

### 9.2 Database Connectivity

```bash
# Test PostgreSQL from pod
kubectl exec -it <pod-name> -n somabrain -- \
  pg_isready -h postgres -U somabrain
```

---

## 10. Production Checklist

- [ ] External PostgreSQL configured (RDS/Cloud SQL)
- [ ] External Redis configured (ElastiCache/Memorystore)
- [ ] Secrets managed via External Secrets Operator
- [ ] TLS certificates configured via cert-manager
- [ ] Network policies applied
- [ ] Pod security policies enabled
- [ ] Backup strategy implemented
- [ ] Monitoring and alerting configured
- [ ] Log aggregation enabled (Loki/ELK)

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-09 | Vibe Collective | Initial template |
