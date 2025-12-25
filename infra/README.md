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

### Helm Charts (`helm/`) — Canonical
Canonical source of truth for Kubernetes deployment of SomaBrain. All service ports, health probes, and Prometheus scraping are configured via chart values.

NodePort exposure (optional; centralized in `infra/helm/charts/soma-apps/values.yaml`):
- `.Values.expose.apiNodePort` (default false) → API NodePort at `.Values.ports.apiNodePort` (default 30200)
- `.Values.expose.healthNodePorts` (default false) → health NodePorts for integrator, segmentation, and predictors (30201–30205)
- `.Values.expose.learnerNodePorts` (default false) → learner NodePorts for reward/online (30206–30207)
ContainerPorts/targetPorts remain unchanged; prefer ServiceMonitor/PodMonitor for scraping instead of exposing health ports unless needed for host access.

### Kubernetes (`k8s/`) — Deprecated Examples
Raw manifests kept for reference and ad-hoc testing only. Do not use these alongside Helm. Prefer the Helm charts for any real environment (dev/staging/prod).

### Kafka (`kafka/`)
Kafka topic definitions and user configurations for event streaming.

### Observability (`observability/`)
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
# Deploy with Helm (recommended & canonical)
helm upgrade --install somabrain infra/helm/charts/soma-apps -n somabrain --create-namespace

# Optional: Deploy shared infra
helm upgrade --install soma-infra infra/helm/charts/soma-infra -n soma --create-namespace
```

Notes:
- The raw manifests under `infra/k8s/` are deprecated examples; avoid mixing them with Helm releases to prevent drift.
- Canonical ports for sidecar health endpoints are centralized in `infra/helm/charts/soma-apps/values.yaml` (healthPort per component).

---

## References

- [Technical Manual](../docs/technical-manual/index.md)
- [Deployment Guide](../docs/technical-manual/deployment.md)
- [Monitoring Guide](../docs/technical-manual/monitoring.md)
