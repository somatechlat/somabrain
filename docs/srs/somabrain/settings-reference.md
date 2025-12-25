# SomaBrain Settings Reference

**Document Version:** 1.0.0  
**Date:** 2025-12-24  
**Source File:** `somabrain/settings.py` (684 lines)

---

## Overview

SomaBrain uses Django settings with django-environ for configuration. All settings are loaded from environment variables.

---

## Settings Categories

### Django Core

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `DEBUG` | bool | False | Enable debug mode |
| `SECRET_KEY` | str | insecure-key | Django secret key |
| `ALLOWED_HOSTS` | list | ['*'] | Allowed hosts |

---

### Authentication & Security

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMABRAIN_AUTH_REQUIRED` | bool | False | Require authentication |
| `SOMABRAIN_API_TOKEN` | str | None | API authentication token |
| `SOMABRAIN_AUTH_SERVICE_URL` | str | None | Auth service URL |
| `SOMABRAIN_JWT_SECRET` | str | None | JWT signing secret |
| `SOMABRAIN_JWT_PUBLIC_KEY_PATH` | str | None | Path to JWT public key |
| `SOMABRAIN_JWT_AUDIENCE` | str | None | JWT audience claim |
| `SOMABRAIN_JWT_ISSUER` | str | None | JWT issuer claim |
| `SOMABRAIN_OPA_PRIVKEY_PATH` | str | None | OPA private key path |
| `SOMABRAIN_OPA_PUBKEY_PATH` | str | None | OPA public key path |
| `SOMABRAIN_PROVENANCE_SECRET` | str | None | Provenance signing secret |
| `SOMABRAIN_VAULT_ADDR` | str | None | HashiCorp Vault address |
| `SOMABRAIN_VAULT_TOKEN` | str | None | Vault access token |

---

### Infrastructure

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMABRAIN_POSTGRES_DSN` | str | '' | PostgreSQL connection string |
| `SOMABRAIN_REDIS_URL` | str | '' | Redis connection URL |
| `SOMABRAIN_REDIS_HOST` | str | None | Redis host |
| `SOMABRAIN_REDIS_PORT` | int | 6379 | Redis port |
| `SOMABRAIN_REDIS_DB` | int | 0 | Redis database number |
| `KAFKA_BOOTSTRAP_SERVERS` | str | '' | Kafka bootstrap servers |
| `SOMABRAIN_MILVUS_HOST` | str | None | Milvus vector DB host |
| `SOMABRAIN_MILVUS_PORT` | int | 19530 | Milvus port |
| `SOMABRAIN_OPA_URL` | str | http://opa:8181 | OPA policy server URL |

---

### Service Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMABRAIN_HOST` | str | 0.0.0.0 | Bind host |
| `SOMABRAIN_PORT` | str | 9696 | Bind port |
| `SOMABRAIN_WORKERS` | int | 1 | Number of workers |
| `SOMABRAIN_SERVICE_NAME` | str | somabrain | Service name |
| `SOMABRAIN_NAMESPACE` | str | public | Default namespace |
| `SOMABRAIN_DEFAULT_TENANT` | str | public | Default tenant |
| `SOMABRAIN_MODE` | str | full-local | Operation mode |
| `SOMABRAIN_LOG_LEVEL` | str | INFO | Log level |

---

### Memory System

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMABRAIN_MEMORY_HTTP_ENDPOINT` | str | http://localhost:9595 | SomaFractalMemory URL |
| `SOMABRAIN_MEMORY_MAX` | str | 10GB | Max memory usage |
| `SOMABRAIN_EMBED_DIM` | int | 256 | Embedding dimension |
| `SOMABRAIN_WM_SIZE` | int | 64 | Working memory size |
| `SOMABRAIN_WM_SALIENCE_THRESHOLD` | float | 0.4 | Salience threshold |
| `SOMABRAIN_WM_PER_TENANT_CAPACITY` | int | 128 | Per-tenant WM capacity |
| `SOMABRAIN_MTWM_MAX_TENANTS` | int | 1000 | Max tenants in WM |

---

### Working Memory Weights

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMABRAIN_WM_ALPHA` | float | 0.6 | Recency weight |
| `SOMABRAIN_WM_BETA` | float | 0.3 | Relevance weight |
| `SOMABRAIN_WM_GAMMA` | float | 0.1 | Importance weight |
| `SOMABRAIN_WM_RECENCY_TIME_SCALE` | float | 1.0 | Time scale factor |
| `SOMABRAIN_WM_RECENCY_MAX_STEPS` | int | 1000 | Max recency steps |

---

### Salience Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMABRAIN_SALIENCE_METHOD` | str | dense | Salience method |
| `SOMABRAIN_SALIENCE_W_NOVELTY` | float | 0.6 | Novelty weight |
| `SOMABRAIN_SALIENCE_W_ERROR` | float | 0.4 | Error weight |
| `SOMABRAIN_SALIENCE_THRESHOLD_STORE` | float | 0.5 | Store threshold |
| `SOMABRAIN_SALIENCE_THRESHOLD_ACT` | float | 0.7 | Action threshold |

---

### Retrieval Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMABRAIN_RETRIEVAL_ALPHA` | float | 1.0 | Vector weight |
| `SOMABRAIN_RETRIEVAL_BETA` | float | 0.2 | Graph weight |
| `SOMABRAIN_RETRIEVAL_GAMMA` | float | 0.1 | Recency weight |
| `SOMABRAIN_RETRIEVAL_TAU` | float | 0.7 | Temperature |
| `SOMABRAIN_RECALL_DEFAULT_RETRIEVERS` | str | vector,wm,graph,lexical | Retriever list |

---

### Rate Limiting & Quotas

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMABRAIN_RATE_RPS` | int | 1000 | Requests per second |
| `SOMABRAIN_RATE_BURST` | int | 2000 | Burst limit |
| `SOMABRAIN_WRITE_DAILY_LIMIT` | int | 100000 | Daily write limit |
| `SOMABRAIN_QUOTA_TENANT` | int | 10000 | Tenant quota |
| `SOMABRAIN_QUOTA_TOOL` | int | 1000 | Tool quota |
| `SOMABRAIN_QUOTA_ACTION` | int | 500 | Action quota |

---

### Neuromodulation (Cognitive)

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMABRAIN_NEURO_DOPAMINE_BASE` | float | 0.4 | Base dopamine level |
| `SOMABRAIN_NEURO_SEROTONIN_BASE` | float | 0.5 | Base serotonin level |
| `SOMABRAIN_NEURO_NORAD_BASE` | float | 0.0 | Base noradrenaline |
| `SOMABRAIN_NEURO_ACETYL_BASE` | float | 0.0 | Base acetylcholine |

---

### Sleep & Consolidation

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMABRAIN_ENABLE_SLEEP` | bool | True | Enable sleep cycle |
| `SOMABRAIN_CONSOLIDATION_ENABLED` | bool | True | Enable consolidation |
| `SOMABRAIN_SLEEP_INTERVAL_SECONDS` | int | 3600 | Sleep interval |
| `SOMABRAIN_NREM_BATCH_SIZE` | int | 16 | NREM batch size |
| `SOMABRAIN_REM_RECOMB_RATE` | float | 0.2 | REM recombination rate |

---

### Feature Flags

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMABRAIN_MINIMAL_PUBLIC_API` | bool | False | Minimal API mode |
| `SOMABRAIN_ALLOW_ANONYMOUS_TENANTS` | bool | False | Allow anonymous |
| `SOMABRAIN_KILL_SWITCH` | bool | False | Emergency kill switch |
| `SOMABRAIN_USE_HRR` | bool | False | Use HRR encoding |
| `SOMABRAIN_USE_META_BRAIN` | bool | False | Use meta-brain |
| `SOMABRAIN_USE_EXEC_CONTROLLER` | bool | False | Use exec controller |
| `SOMABRAIN_USE_PLANNER` | bool | False | Use planner |
| `ENABLE_OAK` | bool | False | Enable OAK (ROAMDP) |
| `ENABLE_COG_THREADS` | bool | False | Enable cog threads |

---

### Kafka Topics

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMABRAIN_TOPIC_CONFIG_UPDATES` | str | cog.config.updates | Config update topic |
| `SOMABRAIN_TOPIC_NEXT_EVENT` | str | cog.next_event | Next event topic |
| `SOMABRAIN_TOPIC_STATE_UPDATES` | str | cog.state.updates | State update topic |
| `SOMABRAIN_TOPIC_AGENT_UPDATES` | str | cog.agent.updates | Agent update topic |
| `SOMABRAIN_AUDIT_TOPIC` | str | soma.audit | Audit event topic |

---

### Outbox Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `OUTBOX_BATCH_SIZE` | int | 100 | Batch size |
| `OUTBOX_MAX_DELAY` | float | 5.0 | Max delay seconds |
| `OUTBOX_MAX_RETRIES` | int | 5 | Max retry count |
| `OUTBOX_POLL_INTERVAL` | float | 1.0 | Poll interval |

---

### Circuit Breaker

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMABRAIN_CIRCUIT_FAILURE_THRESHOLD` | int | 3 | Failure threshold |
| `SOMABRAIN_CIRCUIT_RESET_INTERVAL` | float | 60.0 | Reset interval |
| `SOMABRAIN_CIRCUIT_COOLDOWN_INTERVAL` | float | 0.0 | Cooldown interval |

---

## Total Settings Count

| Category | Count |
|----------|-------|
| Django Core | 5 |
| Auth & Security | 15 |
| Infrastructure | 20 |
| Service Config | 12 |
| Memory System | 50+ |
| Cognitive/Neuro | 40+ |
| Sleep/Consolidation | 20 |
| Feature Flags | 15 |
| Kafka Topics | 10 |
| Rate Limiting | 8 |
| **TOTAL** | **300+** |

---

*SomaBrain Settings - VIBE Coding Rules Compliant*
