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

## 6. Degradation Flow (Authoritative Reference)

### 6.1 Detection & Circuit Opening

1. `MemoryService` guards every `remember`/`recall` with `_reset_circuit_if_needed()` (file: `somabrain/services/memory_service.py`).
2. If the HTTP call to `MemoryClient` raises or `/health` reports any component as `False`, the per‑tenant circuit breaker (file: `somabrain/infrastructure/circuit_breaker.py`) records a failure.
3. After `circuit_failure_threshold` consecutive failures the breaker opens **automatically**. No operator input is required.

### 6.2 Queuing Writes While Degraded

1. Once `_is_circuit_open()` returns `True`, `MemoryService` routes writes through `_queue_degraded()`:
   - payloads are appended to the journal (`somabrain/journal/local_journal.py`) with topic `memory.degraded` (configurable via `memory_degrade_topic`).
   - the same payload is written into the durable outbox table (`somabrain/db/models/outbox.py`) by the API layer.
2. `memory_degrade_queue` is always `True` in production builds, enforcing “queue, never drop”.
3. If `memory_degrade_readonly` is `True`, the service raises after queuing so callers know the write did not reach the backend; otherwise it raises a degraded error explicitly (`RuntimeError("Memory service unavailable (circuit open)")`).

### 6.3 Replay Once Healthy

1. The FastAPI startup hook launches `outbox_sync_loop` (file: `somabrain/services/outbox_sync.py`), which polls `outbox_events` continuously.
2. The loop skips work while the backend is still unhealthy; once `/health` succeeds it replays pending events via `MemoryClient.remember()`.
3. Successful sends flip `status` to `sent` and emit metrics (`MEMORY_OUTBOX_SYNC_TOTAL` plus per‑tenant gauges).
4. If the backend stays down, retries back off exponentially; no writes are discarded.

### 6.4 Read/Recall Behavior During Degradation

1. `/recall` (both `app.py` and `somabrain/api/memory_api.py`) inspects the breaker state:
   - If the breaker is open, the handler short‑circuits to **working‑memory only** results and sets `degraded=True` in the response schema (`somabrain/schemas.py::RecallResponse`).
   - If the breaker is closed but the long‑term recall path fails mid‑request, the degraded flag is also set so clients know results may be partial.
2. `/remember` responses include `breaker_open`/`queued` hints so agents can react.

### 6.5 Recovery & Auto‑Reset

1. The health watchdog in `app.py` (`_init_health_watchdog`) polls every tenant at `memory_health_poll_interval`.
2. When `/health` returns all components healthy, it calls `MemoryService.reset_circuit_for_tenant`, automatically closing the breaker.
3. No manual toggles or mode switches are required; once healthy, new writes go straight to the HTTP backend and the outbox loop drains the backlog.

### 6.6 Telemetry & Diagnostics

| Signal | Location | Meaning |
|--------|----------|---------|
| `memory_ok`, `memory_circuit_open`, `memory_degraded` | `/health` JSON (`somabrain/app.py`) | Current backend status per tenant. |
| `memory_degrade_queue`, `memory_degrade_readonly` | `/health` JSON | Runtime policy flags resolved from settings. |
| `OUTBOX_PENDING`, `OUTBOX_PENDING_BY_TENANT` | `somabrain/metrics.py` | Gauge of queued events (alerts when >0 for prolonged periods). |
| `MEMORY_OUTBOX_SYNC_TOTAL{status}` | `somabrain/metrics.py` | Success/failure counters for replay attempts. |
| `somabrain_memory_http_requests_total` | Prometheus metric (`somabrain/metrics.py`) | Operation/tenant/status tagged counter for live HTTP calls to port 9595. |
| `somabrain_memory_http_latency_seconds` | Prometheus metric (`somabrain/metrics.py`) | Histogram tracking end-to-end latency per operation/tenant. |
| `tests/integration/test_recall_quality.py` | CI coverage | Verifies the `degraded` flag is surfaced end‑to‑end. |

Operators should alarm on:
- `memory_circuit_open == true` for >5 minutes.
- Outbox pending count increasing without decrease.
- `/recall` responses reporting `degraded=true` for production tenants.

### 6.7 Configuration Summary

| Setting | Default | Purpose |
|---------|---------|---------|
| `memory_degrade_queue` | `True` | Ensure writes are journaled/outboxed when degraded. |
| `memory_degrade_readonly` | `False` | When `True`, `/remember` raises immediately after queuing to prevent WM admission. |
| `memory_degrade_topic` | `memory.degraded` | Journal topic for queued payloads. |
| `memory_health_poll_interval` | `5` seconds | Frequency of watchdog resets. |
| `circuit_failure_threshold` | `3` | Consecutive failures before opening breaker. |
| `circuit_reset_interval` | `60` seconds | Minimum wait before retrying a closed circuit. |

Set these through `common/config/settings.py` or environment variables (`SOMABRAIN_MEMORY_DEGRADE_*`, `SOMABRAIN_MEMORY_HEALTH_POLL_INTERVAL`, etc.).

### 6.8 Operator Checklist

1. **Detection**: Alert fires on `memory_circuit_open`. Confirm `/health` shows `memory_degraded=true`.
2. **Containment**: Verify outbox queue depth is increasing (expected).
3. **Resolution**: Restore the external memory backend (port 9595). Watch `/diagnostics` until `memory_endpoint` responds.
4. **Verification**: Confirm outbox depth returns to zero and `/recall` responses flip `degraded` back to `false`.

## 7. End‑to‑End Verification Recipe

```bash
# 1. Stop the external memory container
docker stop somafractalmemory_api
# 2. Send a few remember calls (they will be queued)
curl -X POST http://localhost:9696/remember ...
# 3. Restart the memory container
docker start somafractalmemory_api
# 4. Wait ~70 s (reset interval + watchdog poll)
# 5. Verify circuit closed and outbox empty
curl -s http://localhost:9696/health/memory | jq .
```

The response should show `circuit_open: false` and `memory_service: "healthy"`.

---

*All changes are on the `strip` branch. Merge to `main` after verification.*
