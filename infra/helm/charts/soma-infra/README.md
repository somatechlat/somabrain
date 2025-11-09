> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# soma-infra Helm chart

This chart is the shared infra bundle for SomaBrain. It is intentionally
lightweight as a scaffold; each component (Auth, OPA, Kafka, Redis, Prometheus,
Vault, Etcd) should be wired to either subcharts or external
operators in `Chart.yaml` dependencies.

Quick dev install (Kind)

1. Create a kind cluster:

```bash
kind create cluster --name soma-dev
kubectl cluster-info --context kind-soma-dev
```

2. Install the chart into the `soma` namespace:

```bash
kubectl create ns soma || true
helm upgrade --install soma-infra ./infra/helm/charts/soma-infra -n soma -f infra/helm/charts/soma-infra/values.yaml
```

3. For rapid local iteration use `scripts/dev_up.sh`, which
   uses Docker Compose and provides a faster developer loop.

Notes
-----
- `values-dev.yaml` contains local overrides to enable/disable components.
- This chart includes templates for a `ConfigMap` and a `Secret` used by
  applications to read config and secrets in non-Vault dev modes.

Persistence and production settings
-----------------------------------
- By default, persistence is disabled for Kafka/Redis/Etcd/Vault to keep local
   iteration fast and stateless. For production, enable persistence and set
   appropriate storage sizes in a values override (e.g., `values-prod.yaml`).

Example (values override):

```yaml
kafka:
   enabled: true
   persistence:
      enabled: true
      size: 100Gi

redis:
   master:
      persistence:
         enabled: true
         size: 20Gi

etcd:
   persistence:
      enabled: true

vault:
   server:
      standalone:
         enabled: true
   injector:
      enabled: true
```

Observability
-------------
ServiceMonitor/PodMonitor resources can be enabled from the application chart
(`infra/helm/charts/soma-apps`) to scrape metrics. You can also provide Grafana
dashboards via your chosen Grafana deployment; see your platform’s dashboard
provisioning docs. This repo ships Prometheus scrape examples for Docker Compose
under `ops/prometheus/`.
