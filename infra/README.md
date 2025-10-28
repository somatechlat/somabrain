# Infrastructure

**Purpose**: Consolidated infrastructure configuration and deployment resources.

**Audience**: DevOps engineers, SREs, platform teams.

---

## Directory Structure

```
infra/
├── gateway/           # API gateway configurations
├── helm/              # Helm charts for Kubernetes
├── k8s/               # Kubernetes manifests
├── kafka/             # Kafka topics and users
├── observability/     # Monitoring and observability configs
├── ops/               # Operational tools (Envoy, OPA, Prometheus, Supervisor)
├── tls/               # TLS certificates
└── web/               # Web UI and monitoring dashboards
```

---

## Components

### Gateway (`gateway/`)
API gateway configuration for routing and load balancing.

### Helm Charts (`helm/`)
Kubernetes Helm charts for deploying SomaBrain services.

### Kubernetes (`k8s/`)
Raw Kubernetes manifests for deployment, services, and ingress.

### Kafka (`kafka/`)
Kafka topic definitions and user configurations for event streaming.

### Observability (`observability/`)
- Grafana provisioning
- OpenTelemetry configuration
- Prometheus configuration

### Operations (`ops/`)
- **Envoy**: Service mesh configuration
- **OPA**: Policy engine rules
- **Prometheus**: Metrics collection
- **Supervisor**: Process management

### TLS (`tls/`)
SSL/TLS certificates for secure communication.

### Web (`web/`)
Web-based monitoring dashboards and UI components.

---

## Usage

### Local Development
```bash
# Start infrastructure stack
docker compose up -d

# Access monitoring
open http://localhost:9090  # Prometheus
```

### Kubernetes Deployment
```bash
# Deploy with Helm
helm install somabrain infra/helm/charts/somabrain

# Deploy with kubectl
kubectl apply -f infra/k8s/
```

---

## References

- [Technical Manual](../docs/technical-manual/index.md)
- [Deployment Guide](../docs/technical-manual/deployment.md)
- [Monitoring Guide](../docs/technical-manual/monitoring.md)
