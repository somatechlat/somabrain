# SomaFractalMemory Settings Reference

**Document Version:** 1.0.0  
**Date:** 2025-12-24  
**Source File:** `somafractalmemory/settings.py` (308 lines)

---

## Overview

SomaFractalMemory uses Django settings with environment variables prefixed with `SOMA_`.

---

## Settings Categories

### Security

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMA_SECRET_KEY` | str | dev-only | Django secret key |
| `SOMA_DEBUG` | bool | False | Debug mode |
| `SOMA_ALLOWED_HOSTS` | list | localhost | Allowed hosts |
| `SOMA_API_TOKEN` | str | None | API authentication token |
| `SOMA_API_TOKEN_FILE` | str | None | Path to token file |

---

### Database

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMA_DB_NAME` | str | somamemory | Database name |
| `SOMA_DB_USER` | str | soma | Database user |
| `SOMA_DB_PASSWORD` | str | soma | Database password |
| `SOMA_DB_HOST` | str | postgres | Database host |
| `SOMA_DB_PORT` | str | 5432 | Database port |
| `SOMA_POSTGRES_SSL_MODE` | str | None | SSL mode |

---

### Redis

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMA_REDIS_HOST` | str | redis | Redis host |
| `SOMA_REDIS_PORT` | int | 6379 | Redis port |
| `SOMA_REDIS_DB` | int | 0 | Redis database |
| `SOMA_REDIS_PASSWORD` | str | None | Redis password |

---

### Milvus Vector Store

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMA_MILVUS_HOST` | str | milvus | Milvus host |
| `SOMA_MILVUS_PORT` | int | 19530 | Milvus port |

---

### Memory System

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMA_NAMESPACE` | str | default | Default namespace |
| `SOMA_MEMORY_NAMESPACE` | str | api_ns | Memory namespace |
| `SOMA_MEMORY_MODE` | str | evented_enterprise | Memory mode |
| `SOMA_MODEL_NAME` | str | microsoft/codebert-base | Embedding model |
| `SOMA_VECTOR_DIM` | int | 768 | Vector dimension |
| `SOMA_MAX_MEMORY_SIZE` | int | 100000 | Max memory count |
| `SOMA_PRUNING_INTERVAL_SECONDS` | int | 600 | Pruning interval |
| `SOMA_FORCE_HASH_EMBEDDINGS` | bool | False | Force hash embeddings |

---

### Hybrid Search

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMA_HYBRID_RECALL_DEFAULT` | bool | True | Enable hybrid recall |
| `SOMA_HYBRID_BOOST` | float | 2.0 | Hybrid boost factor |
| `SOMA_HYBRID_CANDIDATE_MULTIPLIER` | float | 4.0 | Candidate multiplier |
| `SOMA_SIMILARITY_METRIC` | str | cosine | Similarity metric |

---

### API Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMA_API_PORT` | int | 9595 | API port |
| `SOMA_LOG_LEVEL` | str | INFO | Log level |
| `SOMA_MAX_REQUEST_BODY_MB` | float | 5.0 | Max request body |
| `SOMA_RATE_LIMIT_MAX` | int | 60 | Rate limit max |
| `SOMA_RATE_LIMIT_WINDOW` | float | 60.0 | Rate limit window |
| `SOMA_CORS_ORIGINS` | str | '' | CORS origins |

---

### Importance Normalization

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMA_IMPORTANCE_RESERVOIR_MAX` | int | 512 | Reservoir max size |
| `SOMA_IMPORTANCE_RECOMPUTE_STRIDE` | int | 64 | Recompute stride |
| `SOMA_IMPORTANCE_WINSOR_DELTA` | float | 0.25 | Winsorization delta |
| `SOMA_IMPORTANCE_LOGISTIC_TARGET_RATIO` | float | 9.0 | Logistic target |
| `SOMA_IMPORTANCE_LOGISTIC_K_MAX` | float | 25.0 | Logistic K max |

---

### Decay Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMA_DECAY_AGE_HOURS_WEIGHT` | float | 1.0 | Age weight |
| `SOMA_DECAY_RECENCY_HOURS_WEIGHT` | float | 1.0 | Recency weight |
| `SOMA_DECAY_ACCESS_WEIGHT` | float | 0.5 | Access weight |
| `SOMA_DECAY_IMPORTANCE_WEIGHT` | float | 2.0 | Importance weight |
| `SOMA_DECAY_THRESHOLD` | float | 2.0 | Decay threshold |

---

### Batch Processing

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMA_ENABLE_BATCH_UPSERT` | bool | False | Enable batch upsert |
| `SOMA_BATCH_SIZE` | int | 1 | Batch size |
| `SOMA_BATCH_FLUSH_MS` | int | 0 | Batch flush ms |

---

### Feature Flags

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMA_ASYNC_METRICS_ENABLED` | bool | False | Enable async metrics |
| `SFM_FAST_CORE` | bool | False | Enable fast core |
| `SOMA_FAST_CORE_INITIAL_CAPACITY` | int | 1024 | Fast core capacity |

---

### JWT Authentication

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMA_JWT_ENABLED` | bool | False | Enable JWT auth |
| `SOMA_JWT_ISSUER` | str | '' | JWT issuer |
| `SOMA_JWT_AUDIENCE` | str | '' | JWT audience |
| `SOMA_JWT_SECRET` | str | '' | JWT secret |
| `SOMA_JWT_PUBLIC_KEY` | str | '' | JWT public key |

---

### Circuit Breaker

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMA_CIRCUIT_FAILURE_THRESHOLD` | int | 3 | Failure threshold |
| `SOMA_CIRCUIT_RESET_INTERVAL` | float | 60.0 | Reset interval |
| `SOMA_CIRCUIT_COOLDOWN_INTERVAL` | float | 0.0 | Cooldown interval |

---

### External Services

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMA_VAULT_URL` | str | '' | Vault URL |
| `SOMA_SECRETS_PATH` | str | '' | Secrets path |
| `SOMA_LANGFUSE_PUBLIC` | str | '' | Langfuse public key |
| `SOMA_LANGFUSE_SECRET` | str | '' | Langfuse secret |
| `SOMA_LANGFUSE_HOST` | str | '' | Langfuse host |

---

### Data Directories

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `SOMA_BACKUP_DIR` | Path | ./backups | Backup directory |
| `SOMA_MEMORY_DATA_DIR` | Path | ./data | Memory data dir |
| `SOMA_S3_BUCKET` | str | '' | S3 bucket |
| `SOMA_SERIALIZER` | str | json | Serializer type |

---

## Total Settings Count: 70+

---

*SomaFractalMemory Settings - VIBE Coding Rules Compliant*
