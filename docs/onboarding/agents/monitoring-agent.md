# Monitoring Agent Guide

**Purpose**: Understand observability, metrics, and health checks in SomaBrain.

## Health Endpoint (Code-Verified)

**Endpoint**: `GET /health`

**Implementation**: `somabrain/app.py` line ~1900

**Response Structure** (actual fields from code):

```json
{
  "ok": true,
  "components": {
    "memory": {"http": true, "ok": true},
    "wm_items": "tenant-scoped",
    "api_version": 1
  },
  "namespace": "somabrain_ns",
  "ready": true,
  "predictor_ok": true,
  "memory_ok": true,
  "embedder_ok": true,
  "kafka_ok": true,
  "postgres_ok": true,
  "opa_ok": true,
  "external_backends_required": true,
  "predictor_provider": "mahal",
  "embedder": {"provider": "tiny", "dim": 256},
  "memory_circuit_open": false
}
```

## Readiness Checks (Actual Logic)

**From `somabrain/app.py` health endpoint**:

```python
# Backend enforcement requires:
predictor_ok = predictor_provider not in ("stub", "baseline")
memory_ok = memory_backend.health()["http"] == True
embedder_ok = embedder is not None
kafka_ok = check_kafka(kafka_url)  # somabrain/healthchecks.py
postgres_ok = check_postgres(pg_dsn)  # somabrain/healthchecks.py
opa_ok = opa_client.is_ready()

# Overall readiness:
ready = predictor_ok and memory_ok and embedder_ok and kafka_ok and postgres_ok and opa_ok
```

## Metrics Endpoint

**Endpoint**: `GET /metrics`

**Implementation**: `somabrain/metrics.py`

**Format**: Prometheus text format

**Key Metrics** (actual from code):

### Request Metrics
```
somabrain_http_request_duration_seconds{method="POST",path="/recall"}
somabrain_http_requests_total{method="POST",path="/recall",status="200"}
```

### Memory Metrics
```
somabrain_wm_hits_total
somabrain_wm_misses_total
somabrain_wm_utilization
somabrain_recall_cache_hit_total{cohort="baseline"}
somabrain_recall_cache_miss_total{cohort="baseline"}
```

### Scoring Metrics
```
somabrain_scorer_component{component="cosine"}
somabrain_scorer_component{component="fd"}
somabrain_scorer_component{component="recency"}
somabrain_scorer_final
```

### Learning Metrics
```
somabrain_learning_retrieval_weight{tenant_id="sandbox",param="alpha"}
somabrain_learning_retrieval_weight{tenant_id="sandbox",param="beta"}
somabrain_learning_retrieval_weight{tenant_id="sandbox",param="gamma"}
somabrain_learning_retrieval_weight{tenant_id="sandbox",param="tau"}
somabrain_learning_utility_weight{tenant_id="sandbox",param="lambda"}
somabrain_learning_utility_weight{tenant_id="sandbox",param="mu"}
somabrain_learning_utility_weight{tenant_id="sandbox",param="nu"}
```

### HRR Metrics
```
somabrain_hrr_cleanup_calls_total
somabrain_hrr_cleanup_used_total
somabrain_hrr_cleanup_score
somabrain_hrr_anchor_size
somabrain_hrr_context_saturation
somabrain_hrr_rerank_applied_total
```

## Prometheus Configuration

**File**: `ops/prometheus/etc/prometheus.yml`

**Scrape Config**:

```yaml
scrape_configs:
  - job_name: 'somabrain'
    static_configs:
      - targets: ['somabrain_app:9696']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

## Health Check Implementation

**File**: `somabrain/healthchecks.py`

### Kafka Check

```python
def check_kafka(kafka_url: str) -> bool:
    """Verify Kafka broker is reachable."""
    # Actual implementation uses AdminClient
    # Returns True if broker responds
```

### Postgres Check

```python
def check_postgres(dsn: str) -> bool:
    """Verify Postgres connection."""
    # Actual implementation uses psycopg2
    # Returns True if connection succeeds
```

## Circuit Breaker (Memory Service)

**File**: `somabrain/services/memory_service.py`

**State Variables** (class-level):

```python
_circuit_open: bool = False
_failure_count: int = 0
_last_failure_time: float = 0.0
_failure_threshold: int = 3
_reset_interval: int = 60  # seconds
```

**Logic**:

```python
# On failure:
_failure_count += 1
if _failure_count >= _failure_threshold:
    _circuit_open = True
    _last_failure_time = time.time()

# On success:
_failure_count = 0
_circuit_open = False

# Auto-reset after interval:
if _circuit_open and (time.time() - _last_failure_time) > _reset_interval:
    _circuit_open = False
    _failure_count = 0
```

## Logging Configuration

**File**: `somabrain/app.py` (setup_logging function)

**Log Levels**:
- `INFO`: General system events
- `DEBUG`: Cognitive processing details
- `ERROR`: Error handling

**Log Output**:
- Console (stdout)
- File: `/app/logs/somabrain.log` (if writable)

**Format**:
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

## Observability Stack (Docker Compose)

| Component | Port | Purpose |
|-----------|------|---------|
| Prometheus | 30105 | Metrics collection |
| Jaeger | 30011 | Distributed tracing |
| Kafka Exporter | 30103 | Kafka metrics |
| Postgres Exporter | 30107 | Postgres metrics |

## Example: Monitoring Workflow

```bash
# 1. Check health
curl http://localhost:9696/health | jq .

# 2. Verify readiness
curl http://localhost:9696/health | jq '.ready'

# 3. Scrape metrics
curl http://localhost:9696/metrics | grep somabrain_

# 4. Query Prometheus
curl 'http://localhost:30105/api/v1/query?query=somabrain_http_requests_total'

# 5. Check circuit breaker
curl http://localhost:9696/health | jq '.memory_circuit_open'
```

## Alert Conditions (Recommended)

Based on actual metrics:

```yaml
# High error rate
- alert: HighErrorRate
  expr: rate(somabrain_http_requests_total{status=~"5.."}[5m]) > 0.05

# Memory backend down
- alert: MemoryBackendDown
  expr: somabrain_health_memory_ok == 0

# Circuit breaker open
- alert: CircuitBreakerOpen
  expr: somabrain_memory_circuit_open == 1

# WM utilization high
- alert: WMUtilizationHigh
  expr: somabrain_wm_utilization > 0.9
```

## Key Files to Read

1. `somabrain/app.py` - Health endpoint implementation
2. `somabrain/metrics.py` - Metrics definitions
3. `somabrain/healthchecks.py` - Health check functions
4. `somabrain/services/memory_service.py` - Circuit breaker
5. `ops/prometheus/etc/prometheus.yml` - Prometheus config
