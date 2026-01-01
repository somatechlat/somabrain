# SomaBrain Degradation Mode

**Version:** 1.0  
**Date:** December 9, 2025  
**Classification:** Operational Documentation

---

## 1. Overview

SomaBrain implements a sophisticated degradation mode that ensures system resilience when the external memory service (port 9595) becomes unavailable. This document describes the degradation architecture, behavior, and recovery mechanisms.

### 1.1 Design Principles

Per VIBE Coding Rules, the degradation system:
- Uses REAL infrastructure (no mocks or stubs)
- Provides explicit error messages with context
- Maintains data integrity through journaling
- Supports automatic recovery when services restore

---

## 2. Architecture

### 2.1 Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    SomaBrain Application                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │MemoryService │───▶│CircuitBreaker│───▶│ LocalJournal │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                    │              │
│         ▼                   ▼                    ▼              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │MemoryClient  │    │  CB State    │    │ Journal Files│      │
│  │  (HTTP)      │    │  (per-tenant)│    │ (JSONL)      │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
├─────────────────────────────────────────────────────────────────┤
│                    External Memory Service                       │
│                    (http://localhost:9595)                       │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `MemoryService` | `somabrain/services/memory_service.py` | High-level memory facade with degradation logic |
| `CircuitBreaker` | `somabrain/infrastructure/circuit_breaker.py` | Per-tenant failure detection and recovery |
| `LocalJournal` | `somabrain/journal/local_journal.py` | Durable event storage for degraded writes |
| `MemoryClient` | `somabrain/memory_client.py` | HTTP transport to external memory service |

---

## 3. Circuit Breaker

### 3.1 Configuration

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| Failure Threshold | `SOMABRAIN_CIRCUIT_FAILURE_THRESHOLD` | 3 | Consecutive failures before circuit opens |
| Reset Interval | `SOMABRAIN_CIRCUIT_RESET_INTERVAL` | 60.0s | Time before attempting circuit reset |
| Cooldown Interval | `SOMABRAIN_CIRCUIT_COOLDOWN_INTERVAL` | 0.0s | Extra wait after reset attempt |

### 3.2 State Machine

```
                    ┌─────────────┐
                    │   CLOSED    │◀──────────────────┐
                    │  (healthy)  │                   │
                    └──────┬──────┘                   │
                           │                         │
              failure_count >= threshold             │
                           │                         │
                           ▼                         │
                    ┌─────────────┐          health check
                    │    OPEN     │          succeeds
                    │ (degraded)  │                   │
                    └──────┬──────┘                   │
                           │                         │
              reset_interval elapsed                 │
                           │                         │
                           ▼                         │
                    ┌─────────────┐                  │
                    │ HALF-OPEN   │──────────────────┘
                    │  (testing)  │
                    └─────────────┘
```

### 3.3 Per-Tenant Isolation

Each tenant has independent circuit breaker state:
- Failure counts are tracked per tenant
- One tenant's failures don't affect others
- Recovery is also per-tenant

---

## 4. Degradation Behavior

### 4.1 Write Operations (remember)

When the circuit is OPEN:

1. **Queue to Journal**: Write is persisted to local journal
2. **Return Error**: `RuntimeError("Memory service unavailable (circuit open); queued locally for replay")`
3. **Metric Update**: `CIRCUIT_BREAKER_STATE` gauge set to 1

```python
# From somabrain/services/memory_service.py
def remember(self, key: str, payload: dict, universe: str | None = None):
    if self._is_circuit_open():
        self._queue_degraded("remember", {"key": key, "payload": payload})
        message = "Memory service unavailable (circuit open)"
        if self._degrade_readonly:
            raise RuntimeError(message)
        raise RuntimeError(f"{message}; queued locally for replay")
```

### 4.2 Read Operations (recall)

When the circuit is OPEN:

1. **Fallback to WM**: Retrieval switches to Working Memory only
2. **Mark Degraded**: Response includes `degraded: true`
3. **No External Calls**: Memory service is not contacted

```python
# From somabrain/api/memory_api.py
if circuit_open:
    degraded = True
    ret_req.retrievers = ["wm"]
    ret_req.persist = False
    ret_req.layer = "wm"
```

### 4.3 Configuration Flags

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| Degrade Queue | `SOMABRAIN_MEMORY_DEGRADE_QUEUE` | true | Queue writes when degraded |
| Degrade Readonly | `SOMABRAIN_MEMORY_DEGRADE_READONLY` | false | If true, reject writes entirely |
| Degrade Topic | `SOMABRAIN_MEMORY_DEGRADE_TOPIC` | `memory.degraded` | Kafka topic for degraded events |

---

## 5. Local Journal

### 5.1 Purpose

The local journal provides durable storage for memory writes that cannot be sent to the external service. Events are persisted to disk and can be replayed when the service recovers.

### 5.2 Configuration

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| Journal Directory | `SOMABRAIN_JOURNAL_DIR` | `/tmp/somabrain_journal` | Storage location |
| Max File Size | `SOMABRAIN_JOURNAL_MAX_FILE_SIZE` | 100MB | Rotation threshold |
| Max Files | `SOMABRAIN_JOURNAL_MAX_FILES` | 10 | Maximum journal files |
| Retention Days | `SOMABRAIN_JOURNAL_RETENTION_DAYS` | 7 | Cleanup threshold |
| Sync Writes | `SOMABRAIN_JOURNAL_SYNC_WRITES` | true | fsync for durability |

### 5.3 Event Format

```json
{
  "id": "uuid-v4",
  "topic": "memory.degraded",
  "payload": {
    "action": "remember",
    "payload": {
      "key": "memory-key",
      "payload": { "text": "...", "metadata": {...} }
    }
  },
  "tenant_id": "tenant-123",
  "timestamp": "2025-12-09T12:00:00.000000",
  "status": "pending",
  "retries": 0
}
```

### 5.4 File Structure

```
/tmp/somabrain_journal/
├── journal_2025-12-09_12-00-00.json
├── journal_2025-12-09_13-00-00.json
└── journal_2025-12-09_14-00-00.json
```

---

## 6. Recovery

### 6.1 Automatic Recovery

The circuit breaker automatically attempts recovery:

1. **Wait for Reset Interval**: Default 60 seconds after last failure
2. **Health Check**: Probe the memory service `/health` endpoint
3. **Record Success**: If healthy, close the circuit
4. **Resume Normal Operation**: Subsequent requests go to memory service

```python
# From somabrain/services/memory_service.py
def _reset_circuit_if_needed(self) -> bool:
    if not self._is_circuit_open():
        return False
    if not breaker.should_attempt_reset(tenant):
        return False
    if self._health_check():
        breaker.record_success(tenant)
        return True
    return False
```

### 6.2 Manual Recovery

To manually reset a tenant's circuit:

```python
from somabrain.services.memory_service import MemoryService
MemoryService.reset_circuit_for_tenant("tenant-123")
```

### 6.3 Journal Replay

Pending journal events should be replayed after recovery:

```python
from somabrain.journal import get_journal

journal = get_journal()
pending = journal.read_events(status="pending")
for event in pending:
    # Replay to memory service
    # Mark as sent on success
    journal.mark_events_sent([event.id])
```

---

## 7. Observability

### 7.1 Health Endpoint

The `/health` endpoint exposes degradation state:

```json
{
  "ok": true,
  "memory_ok": true,
  "memory_circuit_open": false,
  "memory_degraded": false,
  "memory_should_reset": false,
  "components": {
    "memory": {
      "kv_store": true,
      "vector_store": true,
      "graph_store": true,
      "healthy": true
    },
    "memory_circuit_open": false,
    "outbox": {
      "pending": 0,
      "last_pending_created_at": null
    }
  }
}
```

### 7.2 Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `somabrain_circuit_breaker_state` | Gauge | 1 if open, 0 if closed |
| `somabrain_memory_degraded_writes_total` | Counter | Total degraded write events |
| `somabrain_journal_pending_events` | Gauge | Pending journal events |

### 7.3 Recall Response

Recall responses include degradation flag:

```json
{
  "results": [...],
  "degraded": true
}
```

---

## 8. Troubleshooting

### 8.1 Circuit Stuck Open

**Symptoms**: Memory operations fail even after service recovery

**Resolution**:
1. Check memory service health: `curl http://localhost:9595/health`
2. Verify network connectivity from container
3. Manually reset circuit if needed

### 8.2 Journal Growing

**Symptoms**: Journal files accumulating

**Resolution**:
1. Check memory service availability
2. Replay pending events
3. Verify retention policy is running

### 8.3 Data Loss Concerns

**Prevention**:
- Journal uses fsync for durability
- Events are not deleted until marked sent
- 7-day retention provides recovery window

---

## 9. Best Practices

1. **Monitor Circuit State**: Alert on `somabrain_circuit_breaker_state == 1`
2. **Set Appropriate Thresholds**: Balance between sensitivity and stability
3. **Implement Replay**: Ensure journal events are replayed after recovery
4. **Test Degradation**: Regularly test by stopping memory service
5. **Size Journal Storage**: Ensure sufficient disk for retention period

---

## 10. Related Documentation

- [Memory Management](../memory_management.md)
- [Production Deployment](../production_deployment.md)
- [Runtime Configuration](./runtime-config.md)
- [Strict Mode](./strict-mode.md)
