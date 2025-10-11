# soma-apps Helm chart

This chart deploys the application layer of the Soma stack—SomaBrain (SB),
SomaAgent01 (SA01), SomaAgentHub (SAH), and SomaFractalMemory (SMF)—and wires
each service to the shared infra namespace provisioned by `soma-infra`.

## Prerequisites

* A Kubernetes cluster with the `soma-infra` chart installed (Auth, OPA, Redis,
  Kafka, Vault, Etcd, kube-prometheus-stack, etc.).
* Container images for each service pushed to a registry accessible by the
  cluster.

## Quick install (kind/local)

```bash
helm upgrade --install soma-apps infra/helm/charts/soma-apps \
  -n somabrain --create-namespace \
  -f infra/helm/charts/soma-apps/values.yaml
```

Override the image repositories/tags and per-service configuration as needed
using your own values file. Each service can be enabled/disabled individually
(`sb.enabled`, `sa01.enabled`, etc.).

## Chart structure

* `values.yaml` – default images, ports, and shared environment variables
  (memory/redis/kafka/opa endpoints).
* `templates/*` – Deployments and Services for SB, SA01, SAH, and SMF.

## Customisation

* Set `envCommon` to point at the DNS names of your shared infra services.
* Override per-service environment variables via `sb.env`, `sah.env`, etc.
* Provide production-ready resource requests/limits and liveness/readiness
  probes in values overrides.

For advanced rollouts (ingress, TLS, horizontal autoscaling) extend the chart
with additional templates or embed it as a subchart of a higher-level release.
