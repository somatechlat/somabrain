# Observability Guide - SomaBrain ↔ SomaFractalMemory Integration

## Overview

This document describes the observability infrastructure for monitoring the SomaBrain (SB) to SomaFractalMemory (SFM) integration layer. It covers metrics, distributed tracing, and recommended Grafana dashboards.

## Metrics

### Integration Metrics (H2.1-H2.5)

All integration metrics are defined in `somabrain/somabrain/metrics/integration.py` and exported via the main metrics module.

#### Request Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `sb_sfm_request_total` | Counter | operation, tenant, status | Total requests from SB to SFM |
| `sb_sfm_request_duration_seconds` | Histogram | operation, tenant | Request latency distribution |

#### Circuit Breaker Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `sb_sfm_circuit_breaker_state` | Gauge | tenant | Circuit state (0=closed, 1=half-open, 2=open) |
| `sb_sfm_degradation_events_total` | Counter | tenant, event_type | Degradation mode events |

#### Outbox Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `sb_sfm_outbox_pending_total` | Gauge | tenant | Pending outbox events |

#### WM-LTM Promotion Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `sb_sfm_wm_promotion_total` | Counter | tenant, status | WM to LTM promotions |
| `sb_wm_promotion_latency_seconds` | Histogram | tenant | Promotion latency |

#### Graph Operation Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `sb_sfm_graph_operations_total` | Counter | tenant, operation, status | Graph operations |
| `sb_sfm_graph_latency_seconds` | Histogram | tenant, operation | Graph operation latency |

#### Bulk Store Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `sb_sfm_bulk_store_total` | Counter | tenant, status | Bulk store operations |
| `sb_sfm_bulk_store_items_total` | Counter | tenant, status | Items in bulk operations |
| `sb_sfm_bulk_store_latency_seconds` | Histogram | tenant | Bulk store latency |

#### Hybrid Recall Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `sb_sfm_hybrid_recall_total` | Counter | tenant, status, fallback | Hybrid recall operations |
| `sb_sfm_hybrid_recall_latency_seconds` | Histogram | tenant | Hybrid recall latency |

## Distributed Tracing (H1.1-H1.5)

### Trace Context Propagation

SomaBrain injects W3C Trace Context headers into all HTTP calls to SFM:
- `traceparent`: Contains trace ID, span ID, and trace flags
- `tracestate`: Contains vendor-specific trace data

### Span Hierarchy

```
sb_remember (SomaBrain)
└── sfm_store (SomaFractalMemory)
    ├── kv_store_set
    ├── vector_store_upsert
    └── graph_store_add_memory

sb_recall (SomaBrain)
└── sfm_search (SomaFractalMemory)
    ├── vector_store_search
    └── kv_store_get (for each result)
```

### Span Attributes

All SB→SFM spans include:
- `tenant`: Tenant identifier
- `endpoint`: API endpoint being called
- `service.name`: "somabrain"
- `peer.service`: "somafractalmemory"
- `http.status_code`: Response status code
- `success`: Boolean indicating success/failure

### Configuration

Tracing is configured via OpenTelemetry environment variables:
- `OTEL_TRACES_SAMPLER`: Sampling strategy (default: parentbased_traceidratio)
- `OTEL_TRACES_SAMPLER_ARG`: Sampling rate (default: 0.01 = 1%)
- `OTEL_EXPORTER_OTLP_ENDPOINT`: OTLP collector endpoint

## Grafana Dashboard Panels

### SFM Integration Overview

```json
{
  "title": "SFM Integration Overview",
  "panels": [
    {
      "title": "Request Rate by Operation",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum(rate(sb_sfm_request_total[5m])) by (operation)",
          "legendFormat": "{{operation}}"
        }
      ]
    },
    {
      "title": "Error Rate",
      "type": "stat",
      "targets": [
        {
          "expr": "sum(rate(sb_sfm_request_total{status!=\"success\"}[5m])) / sum(rate(sb_sfm_request_total[5m])) * 100",
          "legendFormat": "Error %"
        }
      ]
    },
    {
      "title": "P99 Latency by Operation",
      "type": "timeseries",
      "targets": [
        {
          "expr": "histogram_quantile(0.99, sum(rate(sb_sfm_request_duration_seconds_bucket[5m])) by (le, operation))",
          "legendFormat": "{{operation}}"
        }
      ]
    }
  ]
}
```

### Circuit Breaker Status

```json
{
  "title": "Circuit Breaker Status",
  "panels": [
    {
      "title": "Circuit State by Tenant",
      "type": "stat",
      "targets": [
        {
          "expr": "sb_sfm_circuit_breaker_state",
          "legendFormat": "{{tenant}}"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "mappings": [
            {"value": 0, "text": "CLOSED", "color": "green"},
            {"value": 1, "text": "HALF-OPEN", "color": "yellow"},
            {"value": 2, "text": "OPEN", "color": "red"}
          ]
        }
      }
    },
    {
      "title": "Degradation Events",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum(rate(sb_sfm_degradation_events_total[5m])) by (tenant, event_type)",
          "legendFormat": "{{tenant}} - {{event_type}}"
        }
      ]
    }
  ]
}
```

### Outbox Health

```json
{
  "title": "Outbox Health",
  "panels": [
    {
      "title": "Pending Events by Tenant",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sb_sfm_outbox_pending_total",
          "legendFormat": "{{tenant}}"
        }
      ],
      "alert": {
        "name": "High Outbox Backlog",
        "conditions": [
          {
            "evaluator": {"type": "gt", "params": [1000]},
            "operator": {"type": "and"},
            "query": {"params": ["A", "5m", "now"]}
          }
        ]
      }
    }
  ]
}
```

### WM-LTM Promotion

```json
{
  "title": "WM-LTM Promotion",
  "panels": [
    {
      "title": "Promotion Rate",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum(rate(sb_sfm_wm_promotion_total{status=\"success\"}[5m])) by (tenant)",
          "legendFormat": "{{tenant}}"
        }
      ]
    },
    {
      "title": "Promotion Latency P99",
      "type": "gauge",
      "targets": [
        {
          "expr": "histogram_quantile(0.99, sum(rate(sb_wm_promotion_latency_seconds_bucket[5m])) by (le))"
        }
      ]
    }
  ]
}
```

## Alerting Rules

### Critical Alerts

```yaml
groups:
  - name: sfm_integration
    rules:
      - alert: SFMCircuitBreakerOpen
        expr: sb_sfm_circuit_breaker_state == 2
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "SFM circuit breaker open for tenant {{ $labels.tenant }}"
          
      - alert: SFMHighErrorRate
        expr: |
          sum(rate(sb_sfm_request_total{status!="success"}[5m])) 
          / sum(rate(sb_sfm_request_total[5m])) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "SFM error rate above 5%"
          
      - alert: SFMOutboxBacklog
        expr: sb_sfm_outbox_pending_total > 10000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "SFM outbox backlog exceeds 10000 for tenant {{ $labels.tenant }}"
          
      - alert: SFMDegradedMode
        expr: |
          increase(sb_sfm_degradation_events_total{event_type="enter"}[5m]) > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "SFM degraded mode active for tenant {{ $labels.tenant }}"
```

## Health Check Endpoints

### SomaBrain Health

```
GET /health
```

Response includes SFM component status:
```json
{
  "status": "healthy",
  "sfm_available": true,
  "sfm_kv_store": true,
  "sfm_vector_store": true,
  "sfm_graph_store": true,
  "degraded": false,
  "degraded_components": [],
  "outbox_pending": 0
}
```

### SomaFractalMemory Health

```
GET /healthz
```

Basic health check (no auth required).

```
GET /health
```

Full health check with component status (requires auth).

## Troubleshooting

### High Latency

1. Check `sb_sfm_request_duration_seconds` histogram for P99 latency
2. Look at distributed traces for slow spans
3. Check SFM backend health (Postgres, Redis, Milvus)

### Circuit Breaker Open

1. Check `sb_sfm_circuit_breaker_state` gauge
2. Review `sb_sfm_degradation_events_total` for enter/exit events
3. Check SFM availability and error logs

### Outbox Backlog

1. Monitor `sb_sfm_outbox_pending_total` gauge
2. Check for SFM connectivity issues
3. Review outbox replay worker logs

### Tenant Isolation Issues

1. Verify `X-Soma-Tenant` header is set correctly
2. Check tenant-scoped metrics for cross-tenant patterns
3. Review audit logs for tenant mismatch errors
