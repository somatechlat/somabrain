# Learning Loop: Reward → Learner → Config Update → Integrator

This doc outlines the online learning loop and how to validate it locally.

## Components
- Reward Producer (`somabrain/services/reward_producer.py`): HTTP service to publish `RewardEvent` to Kafka `cog.reward.events`.
- Learner Online (`somabrain/services/learner_online.py`): Consumes rewards, computes an EMA, emits `ConfigUpdate` on `cog.config.updates`.
- Integrator Hub (`somabrain/services/integrator_hub.py`): Consumes config updates and adjusts softmax temperature (tau).
- Predictors: Emit `BeliefUpdate` and optional `NextEvent`.

## Topics & Schemas (Avro)
- `cog.reward.events` — `reward_event.avsc`
- `cog.config.updates` — `config_update.avsc`
- `cog.global.frame` — `global_frame.avsc`
- `cog.next.events` — `next_event.avsc`

## Feature Flags
- `SOMABRAIN_FF_REWARD_INGEST` (default 1 in dev): Enables Reward Producer.
- `SOMABRAIN_FF_LEARNER_ONLINE` (default 1 in dev): Enables Learner Online loop.
- `SOMABRAIN_FF_NEXT_EVENT` (default 1 in dev): Enables NextEvent processing (reserved; future predictors).
- `SOMABRAIN_FF_CONFIG_UPDATES` (default 1 in dev): Enables ConfigUpdate publication/consumption.
- `ENABLE_COG_THREADS` (composite): Enables cognitive services if set.

## Ports (dev compose)
- Reward Producer: host `30083` → container `8083`
- Integrator Metrics: host `30010` → container `9010` (`/metrics`)

## Quick Start (dev)
```bash
# 1) Start/refresh containers
docker compose build somabrain_cog && docker compose up -d somabrain_cog

# 2) Post a reward
curl -sS -X POST http://localhost:30083/reward/frame123 \
  -H 'Content-Type: application/json' \
  -d '{"r_task":0.6,"r_user":0.2,"r_latency":0.0,"r_safety":0.0,"r_cost":0.0,"total":0.8}' | jq

# 3) Check integrator tau moved (metrics)
curl -sS http://localhost:30010/metrics | grep '^somabrain_integrator_tau'
```

## Notes
- Both services are values-gated; disable by setting flags to `0`.
- In production, flags are set via Helm values and secrets, not compose.
- Learner maps reward EMA → tau in [0.1,1.0]; higher reward lowers exploration.
