# Memory Management & Circuit‑Breaker Documentation

This document explains the recent changes that enable automatic recovery of the memory service and the out‑of‑process outbox handling.

---

## 1. Circuit‑Breaker Overview

- **Location**: `somabrain/infrastructure/circuit_breaker.py`
- **Behavior**:
  - Opens after `failure_threshold` consecutive failures (default 3).
  - Remains open for `reset_interval` seconds (default 60 s).
  - After the interval the watchdog attempts a reset.
- **Per‑tenant state** is stored in dictionaries guarded by a `RLock`.
- **Metrics**: Updated to use the correct Prometheus gauge `CIRCUIT_BREAKER_STATE`.

## 2. Health‑Watchdog (`app.py`)

- Runs as a FastAPI **startup** background task (`_init_health_watchdog`).
- Periodically (configurable via `SOMABRAIN_MEMORY_HEALTH_POLL_INTERVAL`, default 5 s) iterates over all tenants and:
  1. Creates a `MemoryService` for the tenant.
  2. Checks if the circuit is open.
  3. Calls `client.health()` on the external memory backend.
  4. Detects a healthy response using **both** the legacy flat payload (`healthy`, `http`, `ok`) **and** the newer nested payload (`components["memory"]["healthy"]`).
  5. Calls `MemoryService.reset_circuit_for_tenant` when healthy, logging the reset.
- The logic was updated in this PR to recognise the nested payload, which previously prevented the automatic reset.

## 3. Outbox Publisher Fix

- **File**: `common/config/settings.py`
- Added Boolean field `require_infra` (default `True`).
- This flag is consulted by the outbox‑publisher startup guard; missing it caused the container to crash.
- The field is now documented in `settings.py` and exposed via the environment variable `SOMABRAIN_REQUIRE_INFRA`.

## 4. Journal Import Fix

- **File**: `somabrain/journal/local_journal.py`
- Added the missing `from somabrain.common.config.settings import settings` import.
- Included a comment explaining why the import is required (to avoid `NameError` when the journal is used by the outbox sync loop).

## 5. Configuration Values

| Setting | Env var | Default | Description |
|---------|---------|---------|-------------|
| `memory_health_poll_interval` | `SOMABRAIN_MEMORY_HEALTH_POLL_INTERVAL` | `5.0` seconds | How often the watchdog runs. |
| `require_infra` | `SOMABRAIN_REQUIRE_INFRA` | `True` | Whether infrastructure services (Kafka, Postgres, etc.) are required for the outbox publisher. |
| `circuit_failure_threshold` | `SOMABRAIN_MEMORY_CIRCUIT_FAILURE_THRESHOLD` | `3` | Failures before opening circuit. |
| `circuit_reset_interval` | `SOMABRAIN_MEMORY_CIRCUIT_RESET_INTERVAL` | `60.0` seconds | Minimum wait before a reset attempt. |

## 6. Expected Workflow

1. **Memory service down** → requests fail → circuit opens, writes are queued to the outbox and journal.
2. **Memory service restored** → watchdog sees the healthy payload → resets the circuit.
3. **Outbox sync** re‑plays queued events to the memory backend.
4. **Journal** persists events for crash‑recovery; the new import ensures it works.

## 7. How to Verify

```bash
# 1. Stop the external memory container
docker stop somafractalmemory_api
# 2. Send a few remember calls (they will be queued)
curl -X POST http://localhost:9696/memory/remember ...
# 3. Restart the memory container
docker start somafractalmemory_api
# 4. Wait ~70 s (reset interval + watchdog poll)
# 5. Verify circuit closed and outbox empty
curl -s http://localhost:9696/health/memory | jq .
```

The response should show `circuit_open: false` and `memory_service: "healthy"`.

---

*All changes are on the `strip` branch. Merge to `main` after verification.*
