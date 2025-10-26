# Cognitive Thread: Production Runbook

This runbook covers end-to-end deployment, canarying, rollback, and SLO guardrails for the cognitive-thread services (predictors, segmentation, integrator, orchestrator).

## 1. Prereqs
- Install `soma-infra` in the `soma` namespace (Kafka, Redis, OPA, Prometheus, Grafana). Optionally enable Grafana dashboards in `soma-infra`:

```
# values override
grafana:
  dashboards:
    enabled: true
    namespace: soma
```

- Enable scraping of worker metrics via PodMonitors in `soma-apps`:

```
prometheus:
  podMonitor:
    enabled: true
```

## 2. Install apps

```
helm upgrade --install soma-apps infra/helm/charts/soma-apps -n soma \
  --set featureFlags.enableCogThreads=true \
  --set integrator.enabled=true \
  --set segmentation.enabled=true \
  --set predictorState.enabled=true \
  --set predictorAgent.enabled=true \
  --set predictorAction.enabled=true \
  --set orchestrator.enabled=true
```

## 3. Canary and rollback

- Start with 1 replica each; confirm metrics and events:
  - `somabrain_integrator_frames_total` > 0
  - `somabrain_segments_emitted_total` > 0
  - Predictor `somabrain_predictor_*_emitted_total` increasing

- Enable alerts (optional, recommended):

```
prometheus:
  rules:
    enabled: true
    frames_absent_minutes: 5
    segments_absent_minutes: 5
    leader_switches_rate_threshold: 0.2
    outbox_p90_seconds_threshold: 2.0
```

- Scale up gradually (or enable HPA):

```
autoscaling:
  enabled: true
  minReplicas: 1
  maxReplicas: 3
  cpu:
    targetAverageUtilization: 70
```

- Rollback:
  - Flip `featureFlags.enableCogThreads=false` or disable individual components and `helm upgrade`. Pods stay up but idle; traffic subsides immediately.
  - Alerts should clear; verify dashboards normalize.

## 4. OPA policies (optional)
- Provide minimal integrator policy in `soma-infra` values:

```
opa:
  enabled: true
  policies:
    sample_integrator: |
      package soma.policy.integrator
      default allow = true
      allow := true
```

- Pass `SOMABRAIN_OPA_POLICY` via app env if you use a non-default package path.

## 5. Network, availability, and disruption

- To apply conservative guardrails:

```
networkPolicy:
  enabled: true
podDisruptionBudget:
  enabled: true
  minAvailable: 1
```

## 6. Verification checklist
- Events emitted and consumed:
  - Kafka topics `cog.global.frame` and `cog.segments` active
- Observability:
  - Grafana dashboard “Somabrain • Cognitive Thread” populated
  - Alerts in green; no firing warnings
- Resiliency:
  - Restart a single pod; no duplicate boundaries; system re-stabilizes

## 7. Troubleshooting
- No frames/segments:
  - Check predictor pods are running; integrator logs for OPA errors
  - Confirm Kafka connectivity (pod can resolve `soma-infra-kafka:9092`)
- Metrics empty:
  - Ensure `HEALTH_PORT` env is injected (handled by Helm templates)
  - Confirm PodMonitor enabled and Prometheus Operator installed
