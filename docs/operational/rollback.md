# Rollback Guide

This guide describes how to quickly roll back the cognitive-thread + learning layer using Helm values without changing images.

## Fast Disable (Flags Only)

- Set `featureFlags.enableCogThreads: false`
- Set `learnerEnabled: false`
- Optionally set `enableShadowTraffic: false`

Then apply:

```yaml
featureFlags:
  enableCogThreads: false
learnerEnabled: false
enableShadowTraffic: false
```

Apply with Helm:

```sh
helm upgrade somabrain charts/somabrain -n somabrain-prod -f values.yaml -f values-rollback.yaml
```

Effect:
- Predictors, segmentation, integrator, and orchestrator do not run gated paths.
- `learner_online` does not consume/publish config updates.
- Shadow duplication disabled.

## Full Rollback (Pinned Values + Image)

If you need to revert to a previous image and flags:

```yaml
image:
  repository: somabrain
  tag: <previous-tag>
  pullPolicy: IfNotPresent
featureFlags:
  enableCogThreads: false
learnerEnabled: false
```

Apply:

```sh
helm upgrade somabrain charts/somabrain -n somabrain-prod -f values.yaml -f values-rollback.yaml
```

## Verification

- Confirm HTTP health and metrics:
  - `GET /health` on API/pods returns 200
  - `GET /metrics` shows no `somabrain_integrator_*` increments
- Kafka activity
  - Topics `cog.global.frame`, `cog.config.updates` remain idle
- OPA
  - `somabrain_integrator_opa_veto_ratio` remains constant or absent

## Roll Forward

To re-enable learning gradually:

```yaml
featureFlags:
  enableCogThreads: true
learnerEnabled: true
shadowRatio: 0.02   # 2% shadow
```

Monitor KPIs:
- `somabrain_planning_latency_p99 <= 0.022` (22ms)
- `somabrain_integrator_opa_veto_ratio <= 0.05`
- `somabrain_learning_regret_ewma <= 0.05`

If thresholds exceed for a sustained window, revert flags above.
