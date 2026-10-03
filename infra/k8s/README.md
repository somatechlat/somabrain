# SomaBrain Kubernetes Deployment (Tilt)

## Overview
This directory contains Kubernetes manifests for local development using Tilt + Minikube. Configuration is the authoritative source for production-like deployments.

## Prerequisites
- Minikube with `vfkit` driver (macOS)
- Tilt v0.33+
- kubectl configured for `brain` context

## Quick Start
```bash
# Start Minikube profile
minikube start -p brain --driver=vfkit --memory=10240 --cpus=4

# Configure Docker environment
eval $(minikube docker-env -p brain)

# Start Tilt
tilt up --port 10352
```

## Architecture
```
brain-resilient.yaml
├── ConfigMap (somabrain-config)
├── Deployments
│   ├── postgres (15-alpine)
│   ├── redis (7-alpine)
│   ├── kafka (apache/kafka:3.7.0)
│   ├── milvus (v2.3.9)
│   └── somabrain-api
├── Services
│   ├── postgres:5432
│   ├── redis:6379
│   ├── kafka:9092
│   ├── milvus:19530
│   └── somabrain-api:20020 (NodePort)
└── Job (somabrain-migrate)
```

## Resource Limits

| Component | Memory | CPU | Port |
|-----------|--------|-----|------|
| somabrain-api | 2Gi | 1 | 20020 |
| postgres | 2Gi | 1 | 5432 |
| redis | 1Gi | 0.5 | 6379 |
| kafka | 2Gi | 1 | 9092 |
| milvus | 4Gi | 2 | 19530 |

## Environment Variables (ConfigMap)
```yaml
SOMABRAIN_LOG_LEVEL: "INFO"
# Database topology — parts, not a DSN. A DSN embeds the password, so it must
# never sit in a ConfigMap, a .env or git. The password is read from Vault at
# secret/agent/credentials/postgres_password and the connection is assembled
# at runtime (VIBE Rule 164).
SOMABRAIN_POSTGRES_HOST: "postgres"
SOMABRAIN_POSTGRES_PORT: "5432"
SOMABRAIN_POSTGRES_USER: "somabrain"
SOMABRAIN_POSTGRES_DB: "somabrain"
SOMABRAIN_REDIS_URL: "redis://redis:6379/0"
SOMABRAIN_KAFKA_URL: "kafka:9092"
SOMABRAIN_MILVUS_HOST: "milvus"
SOMABRAIN_MILVUS_PORT: "19530"
ALLOWED_HOSTS: "*"
# SOMA_API_TOKEN is a credential and is read from Vault at
# secret/agent/credentials/soma_api_token. It is never set here.
```

## Port Forwards (Tiltfile)
| Service | Host Port | Container Port |
|---------|-----------|----------------|
| somabrain-api | 20020 | 20020 |
| postgres | 30106 | 5432 |
| redis | 30100 | 6379 |
| kafka | 30102 | 9092 |
| milvus | 30119 | 19530 |

## Commands

```bash
# Start Tilt dashboard
tilt up --port 10352

# Apply manifests manually
kubectl apply -f brain-resilient.yaml -n somabrain

# Check pod status
kubectl get pods -n somabrain

# View API logs
kubectl logs -f deployment/somabrain-api -n somabrain

# Port-forward manually
kubectl port-forward svc/somabrain-api 20020:20020 -n somabrain

# Restart deployment
kubectl rollout restart deployment/somabrain-api -n somabrain
```

## Troubleshooting

### Pods stuck in Pending
```bash
kubectl describe pods -n somabrain | grep -A5 Events
```
Check Minikube has sufficient resources (10GB RAM minimum).

### ImagePullBackOff
Ensure Docker environment is configured:
```bash
eval $(minikube docker-env -p brain)
```

### Health probe failures
Verify `ALLOWED_HOSTS=*` is set in ConfigMap for K8s IP-based probes.
