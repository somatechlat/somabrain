# Era of Experience — Cognitive Threads and Learning Loop

Last updated: 2025-10-26

This document tracks the cognitive-thread design and the experience-centric learning loop that sits alongside the core memory/governance roadmap. It is additive and non-breaking: existing `cog.*` topics and services continue to work.

## Goals

- Predictive threads emit belief updates and next-event predictions (state/agent/action).
- Integrator Hub selects a leader (softmax with OPA), segments streams, and publishes context.
- Reward Producer ingests real reward signals; Learner Online closes the loop by adjusting exploration temperature (τ) and other knobs via `ConfigUpdate`.
- Observability is metrics-only via Prometheus.
- 9999 dev stack uses strict 301xx host ports; services are isolated.

## Topics & Contracts

- `cog.state.updates`, `cog.agent.updates`, `cog.action.updates` — BeliefUpdate
- `cog.global.frame` — GlobalFrame (integrator output)
- `cog.segments` — SegmentBoundary (segmentation)
- `cog.next.events` — NextEvent (predictor next-event emission)
- `cog.reward.events` — RewardEvent (external reward input)
- `cog.config.updates` — ConfigUpdate (learner → integrator and peers)

Schemas live under `proto/cog/*.avsc`. Tests validate presence and optional fastavro round-trips.

## Delivered

- New Avro schemas: `reward_event`, `next_event`, `config_update`.
- Composite master flag: `ENABLE_COG_THREADS` across predictors, integrator, segmentation, orchestrator.
- Integrator Hub: shadow-policy routing (`SHADOW_RATIO`), runtime τ updates from `cog.config.updates`, leader-switch/τ/shadow metrics.
- Reward Producer service (`somabrain/services/reward_producer.py`): FastAPI + Kafka producer, metrics counter.
- Learner Online service (`somabrain/services/learner_online.py`): Kafka consumer/producer; EMA-based τ; metrics gauges.
- Predictors emit `NextEvent` to `cog.next.events`.
- K8s manifests (`k8s/era-experience.yaml`) for reward_producer and learner_online with health probes.
- Docker Compose services with strict 301xx host ports for the 9999 stack.

## How to run (local 9999 stack)

```bash
# From repo root
docker compose --env-file .env.9999.local up -d somabrain_kafka somabrain_app somabrain_reward_producer somabrain_learner_online

# Health checks
curl -sf http://localhost:30183/health
curl -sf http://localhost:30184/health

# Send a reward
curl -s -X POST http://localhost:30183/reward/demo-frame \
  -H 'Content-Type: application/json' \
  -d '{"r_task":0.7,"r_user":0.8,"r_latency":0.1,"r_safety":0.9,"r_cost":0.05}'
```

Prometheus metrics are available from the main API at `/metrics`. The learner exports `soma_exploration_ratio` and `soma_policy_regret_estimate`; the integrator exports `somabrain_integrator_tau`, `somabrain_integrator_leader_switches_total`, and `somabrain_integrator_shadow_*`.

## Next steps

- Optional HTTP `/predict` wrappers for predictors (thin FastAPI facades) if external control is desired.
- CI: add coverage gating and a smoke that validates a reward → config_update loop in isolation.
- Helm packaging (if Helm is preferred over raw YAML) with values for ports/flags.
