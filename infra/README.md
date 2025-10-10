# Shared‑Infra Helm Chart (soma‑infra)

This directory contains the **Helm chart** that deploys the common infrastructure
required by every component in the SomaStack. The chart vendors in upstream
Helm dependencies for the long-lived services and adds a lightweight deployment
for the Soma Auth API:

* **Auth** – JWT issuance and validation (Soma image).
* **OPA** – policy decision point (OPA upstream chart).
* **Kafka** – event bus (Bitnami Kafka).
* **Redis** – in‑memory cache.
* **Etcd** – feature‑flag key‑value store.
* **Vault** – secret injection (dev mode runs an in‑memory Vault).
* **Observability stack** – kube-prometheus-stack (Prometheus + Grafana).

All services are **cluster‑internal only**; they are reachable via DNS such as
`auth.soma‑infra.svc.cluster.local`.  The chart is version‑controlled and
intended to be installed **once per cluster**.  Applications (e.g. SomaBrain)
declare a dependency on this chart in their own `Chart.yaml`.

## Quick start (local development)

```bash
# From the repository root
helm dependency update infra/helm/charts/soma-infra
helm upgrade --install soma-infra infra/helm/charts/soma-infra \
  -n soma-dev --create-namespace \
  -f infra/helm/charts/soma-infra/values-dev.yaml
```

The command will:
1. Ensure subchart dependencies are pulled to `charts/`.
2. Create the target namespace (`soma-dev`) if necessary.
3. Install/upgrade the release with the dev overrides.
4. Wait for all pods to become Ready (use `--wait` for blocking rollouts).

## Customising

Edit `infra/helm/charts/soma-infra/values-dev.yaml`,
`values-staging.yaml`, or `values-prod.yaml` to override replica counts,
resource limits, passwords, etc. Because we rely on upstream charts you can
apply any of their configuration knobs by nesting values under the matching key
(for example `kafka.persistence.enabled` or
`kube-prometheus-stack.prometheus.prometheusSpec`).

---

*This README lives alongside the Helm chart to make onboarding new developers
fast and to serve as the single source of truth for the shared infrastructure.*
