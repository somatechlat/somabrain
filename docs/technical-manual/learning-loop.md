# Learning Loop: Reward → Learner → Config Update → Integrator

This document describes the real (non‑mocked) online learning loop, the runtime
contracts between its components, the environment variables that centralize all
configuration, and the validation procedure. No placeholders or synthetic
shortcuts are used: every step touches the live Kafka broker and services.

## Components (Real Services)
- **Reward Producer** (`somabrain/services/reward_producer.py`)
  - FastAPI endpoint `/reward/{frame_id}` producing `RewardEvent` records to Kafka.
  - Uses `confluent-kafka` producer when available; falls back to `kafka-python`.
  - Avro-first serialization (schema present) with JSON fallback or forced JSON via `REWARD_FORCE_JSON=1` (still real messages).
- **Learner Online** (`somabrain/services/learner_online.py`)
  - Consumes reward topic, maintains per-tenant EMA of `total` reward.
  - Maps EMA to exploration temperature (tau) using configurable clamp bounds.
  - Emits `ConfigUpdate` messages; prefers `confluent-kafka` producer, falls back to `kafka-python` only if necessary.
  - Prints an `effective_config` JSON line at startup (no secrets) for observability.
- **Integrator Hub** (`somabrain/services/integrator_hub.py`)
  - Consumes config updates, applies `exploration_temp` to internal policy state.
  - Exposes `/tau` for direct inspection and `/healthz` for liveness.
- **Predictors (State/Agent/Action)**
  - Produce frames and belief updates; not directly changed by learning loop but influenced by updated tau in downstream selection.
- **(Reserved)** Global Frame / Next Event topics for future contextual learning features.

## Topics & Schemas (All Real)
Environment can override names (see Variables). Defaults:

| Logical Purpose      | Default Topic               | Avro Schema (if present)      | Env Override Key                          |
|----------------------|-----------------------------|--------------------------------|-------------------------------------------|
| Reward Events        | `cog.reward.events`         | `reward_event.avsc`            | `SOMABRAIN_TOPIC_REWARD_EVENTS`          |
| Config Updates       | `cog.config.updates`        | `config_update.avsc`           | `SOMABRAIN_TOPIC_CONFIG_UPDATES`         |
| Global Frame         | `cog.global.frame`          | `global_frame.avsc`            | `SOMABRAIN_TOPIC_GLOBAL_FRAME`           |
| Next Events          | `cog.next.events`           | `next_event.avsc`              | `SOMABRAIN_TOPIC_NEXT_EVENTS`            |

Auto-create is enabled in the dev Kafka compose configuration; in stricter
clusters, topics must be provisioned ahead of time or via admin client (learner
will attempt creation of the config topic if missing and admin APIs available).

## Feature Flags (Enable/Disable Loop Segments)
| Flag                            | Function                                           | Typical Dev Default |
|---------------------------------|----------------------------------------------------|---------------------|
| `SOMABRAIN_FF_REWARD_INGEST`    | Start reward producer HTTP service                 | 1                   |
| `SOMABRAIN_FF_LEARNER_ONLINE`   | Enable learner thread (consumption + emission)     | 1                   |
| `SOMABRAIN_FF_NEXT_EVENT`       | Consume future next event topic (reserved)         | 1                   |
| `SOMABRAIN_FF_CONFIG_UPDATES`   | Allow config update production / consumption       | 1                   |
| `ENABLE_COG_THREADS`            | Composite on-switch for cognition sub-services     | 1 (compose)         |

Flags are additive; disabling a single flag short-circuits only that segment.
No mock path exists: when disabled, the segment simply does not run.

## Ports (Dev Compose)
| Purpose              | Host Port | Container Port | Endpoint Examples                     |
|----------------------|-----------|----------------|---------------------------------------|
| Reward Producer API  | 30083     | 8083           | `POST /reward/{frame_id}` `/health`   |
| Integrator Health    | 30010     | 9010           | `/healthz` `/tau` `/metrics`          |

Other cognition services run internally under supervisor and expose only logs.

## Quick Start (Dev)
```bash
# 1) Start/refresh containers
docker compose build somabrain_cog && docker compose up -d somabrain_cog

# 2) Post a reward
curl -sS -X POST http://localhost:30083/reward/frame123 \
  -H 'Content-Type: application/json' \
  -d '{"r_task":0.6,"r_user":0.2,"r_latency":0.0,"r_safety":0.0,"r_cost":0.0,"total":0.8}' | jq

# 3) Check integrator tau moved (direct endpoint)
curl -sS http://localhost:30010/tau

# 4) Inspect raw config updates
docker compose exec somabrain_cog python - <<'PY'
from kafka import KafkaConsumer
import os
bs=os.getenv('SOMA_KAFKA_BOOTSTRAP') or os.getenv('SOMABRAIN_KAFKA_URL') or 'somabrain_kafka:9092'
if bs.startswith('kafka://'): bs=bs[len('kafka://'):]
c=KafkaConsumer(os.getenv('SOMABRAIN_TOPIC_CONFIG_UPDATES','cog.config.updates'), bootstrap_servers=bs, auto_offset_reset='earliest', enable_auto_commit=False, value_deserializer=lambda b:b, consumer_timeout_ms=3000)
for m in c:
  print(m.offset, m.value.decode('utf-8','ignore'))
PY
```

## Learner Mapping & Parameters
| Parameter              | Env Var              | Default | Effect |
|------------------------|----------------------|---------|--------|
| EMA Alpha              | `LEARNER_EMA_ALPHA`  | 0.2     | Smoothing factor for reward signal |
| Emit Period (s)        | `LEARNER_EMIT_PERIOD`| 30      | Keepalive config update cadence     |
| Tau Min                | `LEARNER_TAU_MIN`    | 0.1     | Lower clamp bound for exploration   |
| Tau Max                | `LEARNER_TAU_MAX`    | 1.0     | Upper clamp bound                   |
| Default LR             | `LEARNER_DEFAULT_LR` | 0.05    | Learning rate emitted with config   |
| Keepalive Tau          | `LEARNER_KEEPALIVE_TAU`| 0.7   | Tau used on periodic emit when idle |
| Force Config JSON      | `LEARNER_FORCE_JSON` | 0       | Disable Avro for config updates     |

Tau formula (pre-clamp):
\( \tau = 0.8 - 0.5 (\text{EMA} - 0.5) \). Higher sustained reward lowers exploration.

## Effective Config Log
At learner startup a single line like:
```
learner_online: effective_config {"bootstrap":"somabrain_kafka:9092", ... }
```
Use this to confirm environment centralization and serialization modes.

## Reliability Choices
- **Producers:** Prefer `confluent-kafka` for delivery reliability (acked offsets observed). Fallback only when unavailable.
- **Topic Creation:** Learner attempts to create the config topic if absent and admin API available; otherwise relies on broker auto-create (enabled in dev compose).
- **No Mocks:** All messages traverse the real Kafka broker; flags disable processing but do not substitute fake implementations.

## Validation Checklist
| Step | Action | Expected |
|------|--------|----------|
| 1 | Post reward | HTTP 200 `{ "status": "ok" }` |
| 2 | Learner logs | `reward total=... tau=...` then `emitted config_update ...` |
| 3 | Config topic consume | New JSON/Avro record with updated tau |
| 4 | `/tau` endpoint | Reflects new exploration temperature value |

## Troubleshooting
| Symptom | Likely Cause | Resolution |
|---------|--------------|-----------|
| Reward OK, no config updates | `kafka-python` timeouts | Ensure `confluent-kafka` installed; rebuild image |
| Tau stuck at 1.0 | No config messages consumed | Check topic existence & learner emission logs |
| Avro serialization errors | Missing schema registry or schema | Force JSON (`REWARD_FORCE_JSON=1` / `LEARNER_FORCE_JSON=1`) |

## Environment Centralization
See `config/env.example` for a full, single source of truth of all variables
governing the loop (topics, flags, mapping bounds). No secrets are stored there;
only operational parameters.

## Security / Secrets
No sensitive values (e.g. JWT secrets) are logged in effective config. Keep
secret material in separate secret management (K8s secrets, Vault, etc.).

## Future Extensions (Planned)
- Per-tenant adaptive policy overrides sourced from `learning.tenants.yaml`.
- Additional metrics: emission success counter, late/retry counts.
- Optional learner `/config` HTTP endpoint mirroring effective config log.

---
This loop implementation follows the strict “no guesswork” rule: each value is
explicitly bound to an environment variable or real-time Kafka data.
