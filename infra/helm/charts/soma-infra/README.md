> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# soma-infra Helm chart

This chart is the shared infra bundle for SomaBrain. It is intentionally
lightweight as a scaffold; each component (Auth, OPA, Kafka, Redis, Prometheus,
Grafana, Vault, Etcd) should be wired to either subcharts or external
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

3. For rapid local iteration you can use `scripts/start_dev_infra.sh` which
   uses `docker-compose` and provides a faster developer loop.

Notes
-----
- `values-dev.yaml` contains local overrides to enable/disable components.
- This chart includes templates for a `ConfigMap` and a `Secret` used by
  applications to read config and secrets in non-Vault dev modes.
