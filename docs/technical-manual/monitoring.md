# Monitoring Guide

**Purpose**: Comprehensive guide for monitoring SomaBrain performance, health, and operational metrics in production environments.

**Audience**: DevOps engineers, system administrators, and SRE teams responsible for SomaBrain operations.

**Prerequisites**: SomaBrain deployed and [Architecture](architecture.md) understanding.

---

## Monitoring Architecture

SomaBrain provides multi-layer monitoring capabilities designed for production observability:

### Monitoring Stack Components

**Application Metrics**: SomaBrain native metrics exposed via Prometheus format
**System Metrics**: Container and host-level resource monitoring
**Log Aggregation**: Structured logging with correlation IDs
**Health Checks**: Automated service health verification
**Alerting**: Rule-based alerts for operational issues
**Dashboards**: Prometheus UI and Alertmanager for alerts (no Grafana)

### Metrics Collection Flow

```
SomaBrain Services → Prometheus → AlertManager → Notifications
                 ↓
              Log Aggregation → ElasticSearch/Loki → Log Analysis
                 ↓
              Health Checks → Service Discovery → Load Balancer
```

---

## Application Metrics

### Core Service Metrics

SomaBrain exposes detailed metrics at `/metrics` endpoint:

```bash
# Access Prometheus metrics
curl http://localhost:9696/metrics

# Key metric categories
somabrain_requests_total{operation="recall",tenant="org_acme"} 12450
somabrain_requests_duration_seconds{operation="remember",quantile="0.95"} 0.120
somabrain_memories_total{tenant="org_acme"} 45230
somabrain_vector_encoding_duration_seconds{quantile="0.50"} 0.045
somabrain_similarity_computation_duration_seconds{quantile="0.99"} 0.230
```

### Memory Operations Metrics

Monitor cognitive memory operations performance:

```promql
# Memory storage rate
rate(somabrain_memories_stored_total[5m])

# Memory recall latency percentiles
histogram_quantile(0.95, rate(somabrain_recall_duration_seconds_bucket[5m]))

# Similarity score distribution
histogram_quantile(0.50, rate(somabrain_similarity_scores_bucket[5m]))

# Memory encoding performance
rate(somabrain_vector_encoding_total[5m]) / rate(somabrain_vector_encoding_duration_seconds_sum[5m])

# Reasoning operation success rate
rate(somabrain_reasoning_successful_total[5m]) / rate(somabrain_reasoning_total[5m])
```

### Tenant-Specific Metrics

Monitor per-tenant performance and usage:

```promql
# Per-tenant memory usage
somabrain_memories_total by (tenant)

# Per-tenant request rate
rate(somabrain_requests_total[5m]) by (tenant)

# Tenant resource utilization
somabrain_tenant_storage_bytes by (tenant) / somabrain_tenant_storage_limit_bytes by (tenant)

# Tenant rate limit utilization
somabrain_tenant_requests_per_minute by (tenant) / somabrain_tenant_rate_limit by (tenant)
```

### API Performance Metrics

Track REST API performance and errors:

```promql
# API request rate by endpoint
rate(somabrain_http_requests_total[5m]) by (method, endpoint)

# HTTP error rate
rate(somabrain_http_requests_total{status=~"4..|5.."}[5m]) / rate(somabrain_http_requests_total[5m])

# Request duration by endpoint
histogram_quantile(0.95, rate(somabrain_http_request_duration_seconds_bucket[5m])) by (endpoint)

# Concurrent connections
somabrain_http_connections_active

# Request queue length
somabrain_http_request_queue_length
```

---

## System Resource Monitoring

### Container Resource Usage

Monitor Docker container resources:

```promql
# CPU usage per container
rate(container_cpu_usage_seconds_total{name=~"somabrain.*"}[5m]) * 100

# Memory usage per container
container_memory_usage_bytes{name=~"somabrain.*"} / container_spec_memory_limit_bytes{name=~"somabrain.*"} * 100

# Network I/O per container
rate(container_network_receive_bytes_total{name=~"somabrain.*"}[5m])
rate(container_network_transmit_bytes_total{name=~"somabrain.*"}[5m])

# Disk I/O per container
rate(container_fs_reads_bytes_total{name=~"somabrain.*"}[5m])
rate(container_fs_writes_bytes_total{name=~"somabrain.*"}[5m])
```

### Database Performance

Monitor PostgreSQL and Redis performance:

```promql
# PostgreSQL metrics
pg_stat_database_tup_inserted{datname="somabrain"}
pg_stat_database_tup_fetched{datname="somabrain"}
pg_locks_count{datname="somabrain"}
pg_database_size_bytes{datname="somabrain"}

# Redis metrics
redis_connected_clients{instance="somabrain-redis:6379"}
redis_used_memory_bytes{instance="somabrain-redis:6379"}
redis_keyspace_hits_total{instance="somabrain-redis:6379"} / (redis_keyspace_hits_total{instance="somabrain-redis:6379"} + redis_keyspace_misses_total{instance="somabrain-redis:6379"})
redis_commands_processed_total{instance="somabrain-redis:6379"}
```

---

## Prometheus Configuration

### Prometheus Setup

Configure Prometheus to scrape SomaBrain metrics:

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "somabrain_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  # SomaBrain API metrics
  - job_name: 'somabrain-api'
    static_configs:
      - targets: ['somabrain-api:9696']
    metrics_path: '/metrics'
    scrape_interval: 10s

  # SomaBrain worker metrics
  - job_name: 'somabrain-workers'
    static_configs:
      - targets: ['somabrain-worker:8080']
    metrics_path: '/metrics'

  # PostgreSQL metrics
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # Redis metrics
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  # Node/container metrics
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
```

#### Reference Docker Compose Targets

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'somabrain_active'
    static_configs:
      - targets: ['sb_somabrain:9696']
    metrics_path: '/metrics'
    scrape_interval: 30s
    scrape_timeout: 10s

  - job_name: 'somabrain_host'
    static_configs:
      - targets: ['host.docker.internal:9696']
    metrics_path: '/metrics'
    scrape_interval: 30s
    scrape_timeout: 10s

  - job_name: 'redis_metrics'
    static_configs:
      - targets: ['sb_redis:6379']
    metrics_path: '/metrics'
    scrape_interval: 30s
    scrape_timeout: 10s

  - job_name: 'postgres_metrics'
    static_configs:
      - targets: ['sb_postgres_exporter:9187']
    metrics_path: '/metrics'
    scrape_interval: 30s
    scrape_timeout: 10s

  - job_name: 'kafka_metrics'
    static_configs:
      - targets: ['sb_kafka_exporter:9308']
    scrape_interval: 30s
    scrape_timeout: 10s

  - job_name: 'opa_metrics'
    static_configs:
      - targets: ['sb_opa:8181']
    metrics_path: '/metrics'
    scrape_interval: 30s
    scrape_timeout: 10s
```

### Alerting Rules

Define alerting rules for operational issues:

```yaml
# somabrain_rules.yml
groups:
- name: somabrain.rules
  rules:

  # High error rate alert
  - alert: SomaBrainHighErrorRate
    expr: rate(somabrain_http_requests_total{status=~"5.."}[5m]) / rate(somabrain_http_requests_total[5m]) > 0.05
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "SomaBrain API error rate is {{ $value | humanizePercentage }}"
      description: "SomaBrain API has error rate of {{ $value | humanizePercentage }} for more than 2 minutes"

  # High response time alert
        <!-- Grafana sections removed: Grafana is not part of this project. Use Prometheus UI and Alertmanager. -->
    expr: histogram_quantile(0.95, rate(somabrain_http_request_duration_seconds_bucket[5m])) > 2
    for: 3m
    labels:
      severity: warning
    annotations:
      summary: "SomaBrain API 95th percentile latency is {{ $value }}s"

  # Memory usage alert
  - alert: SomaBrainHighMemoryUsage
    expr: container_memory_usage_bytes{name="somabrain-api"} / container_spec_memory_limit_bytes{name="somabrain-api"} > 0.85
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "SomaBrain API memory usage is {{ $value | humanizePercentage }}"

  # Storage usage alert
  - alert: SomaBrainStorageSpaceLow
    expr: (somabrain_storage_used_bytes / somabrain_storage_total_bytes) > 0.80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "SomaBrain storage usage is {{ $value | humanizePercentage }}"

  # Service down alert
  - alert: SomaBrainServiceDown
    expr: up{job="somabrain-api"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "SomaBrain API service is down"

  # Database connection issues
  - alert: SomaBrainDatabaseConnectionHigh
    expr: somabrain_database_connections_active / somabrain_database_connections_max > 0.80
    for: 3m
    labels:
      severity: warning
    annotations:
      summary: "SomaBrain database connection usage is {{ $value | humanizePercentage }}"

  # Tenant rate limiting
  - alert: SomaBrainTenantRateLimited
    expr: increase(somabrain_rate_limit_exceeded_total[5m]) by (tenant) > 10
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "Tenant {{ $labels.tenant }} is being rate limited"
```

---

## Visualization examples (removed)

### Main SomaBrain Dashboard

Historical example only (kept for reference; not used in this project):

```json
{
  "dashboard": {
    "title": "SomaBrain Operations Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(somabrain_requests_total[5m])",
            "legendFormat": "{{operation}} - {{tenant}}"
          }
        ]
      },
      {
        "title": "Response Time Distribution",
        "type": "heatmap",
        "targets": [
          {
            "expr": "rate(somabrain_http_request_duration_seconds_bucket[5m])",
            "format": "heatmap"
          }
        ]
      },
      {
        "title": "Memory Operations",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(somabrain_memories_total)",
            "legendFormat": "Total Memories"
          },
          {
            "expr": "rate(somabrain_memories_stored_total[1h])",
            "legendFormat": "Memories/hour"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(somabrain_http_requests_total{status=~\"5..\"}[5m]) / rate(somabrain_http_requests_total[5m])",
            "legendFormat": "Error Rate"
          }
        ],
        "thresholds": "0.01,0.05"
      }
    ]
  }
}
```

### Tenant-Specific Dashboard

```json
{
  "dashboard": {
    "title": "SomaBrain Tenant Dashboard",
    "templating": {
      "list": [
        {
          "name": "tenant",
          "type": "query",
          "query": "label_values(somabrain_requests_total, tenant)"
        }
      ]
    },
    "panels": [
      {
        "title": "Tenant Request Rate",
        "targets": [
          {
            "expr": "rate(somabrain_requests_total{tenant=\"$tenant\"}[5m])"
          }
        ]
      },
      {
        "title": "Tenant Memory Usage",
        "targets": [
          {
            "expr": "somabrain_memories_total{tenant=\"$tenant\"}"
          },
          {
            "expr": "somabrain_storage_used_bytes{tenant=\"$tenant\"}"
          }
        ]
      },
      {
        "title": "Tenant Rate Limits",
        "targets": [
          {
            "expr": "somabrain_tenant_requests_per_minute{tenant=\"$tenant\"} / somabrain_tenant_rate_limit{tenant=\"$tenant\"}"
          }
        ]
      }
    ]
  }
}
```

---

## Log Management

### Structured Logging Configuration

Configure structured logging for SomaBrain:

```yaml
# docker-compose.yml logging configuration
services:
  somabrain-api:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "5"
        labels: "service,version,tenant"

    environment:
      - LOG_LEVEL=INFO
      - LOG_FORMAT=json
      - LOG_CORRELATION_ID=true
```

### Log Schema

SomaBrain uses structured JSON logs:

```json
{
  "timestamp": "2025-10-15T14:30:45.123Z",
  "level": "INFO",
  "service": "somabrain-api",
  "version": "0.1.0",
  "correlation_id": "req_abc123",
  "tenant_id": "org_acme",
  "operation": "recall",
  "duration_ms": 45,
  "status": "success",
  "details": {
    "query": "database optimization",
    "results_count": 5,
    "similarity_threshold": 0.3
  }
}
```

### Log Aggregation with ELK Stack

Set up log aggregation using Elasticsearch, Logstash, and Kibana:

```yaml
# docker-compose.logging.yml
version: '3.8'
services:
  elasticsearch:
    image: elasticsearch:8.10.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  logstash:
    image: logstash:8.10.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    depends_on:
      - elasticsearch

  kibana:
    image: kibana:8.10.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```

**Logstash Configuration**:
```ruby
# logstash.conf
input {
  beats {
    port => 5044
  }
}

filter {
  if [fields][service] == "somabrain" {
    json {
      source => "message"
    }

    # Parse correlation IDs
    if [correlation_id] {
      mutate {
        add_field => { "trace_id" => "%{correlation_id}" }
      }
    }

    # Extract tenant information
    if [tenant_id] {
      mutate {
        add_field => { "tenant" => "%{tenant_id}" }
      }
    }

    # Performance categorization
    if [duration_ms] {
      if [duration_ms] > 1000 {
        mutate { add_tag => ["slow_request"] }
      }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "somabrain-logs-%{+YYYY.MM.dd}"
  }
}
```

---

## Health Checks and Service Discovery

### Application Health Checks

SomaBrain provides comprehensive health endpoints:

```bash
# Basic health check
curl http://localhost:9696/health
{
  "status": "healthy",
  "timestamp": "2025-10-15T14:30:45Z",
  "version": "0.1.0",
  "checks": {
    "database": {"status": "healthy", "response_time_ms": 12},
    "redis": {"status": "healthy", "response_time_ms": 5},
    "vector_index": {"status": "healthy", "size_mb": 890}
  }
}

# Detailed health check with dependencies
curl http://localhost:9696/health/detailed
{
  "status": "healthy",
  "components": {
    "api_server": {
      "status": "healthy",
      "uptime_seconds": 86400,
      "memory_usage_mb": 512,
      "cpu_usage_percent": 15.3
    },
    "postgresql": {
      "status": "healthy",
      "connection_pool": {
        "active": 12,
        "idle": 8,
        "max": 20
      },
      "query_performance": {
        "avg_duration_ms": 23,
        "slow_queries": 0
      }
    },
    "redis": {
      "status": "healthy",
      "memory_usage_mb": 256,
      "keyspace_hits_ratio": 0.97,
      "connected_clients": 5
    }
  }
}

# Readiness check (for Kubernetes)
curl http://localhost:9696/ready
{
  "ready": true,
  "dependencies_ready": {
    "database": true,
    "redis": true,
    "vector_index": true
  }
}

# Liveness check (for Kubernetes)
curl http://localhost:9696/live
{
  "alive": true,
  "pid": 1234,
  "uptime_seconds": 86400
}
```

### Kubernetes Health Probes

Configure Kubernetes health probes:

```yaml
# k8s/somabrain-deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: somabrain-api
spec:
  template:
    spec:
      containers:
      - name: somabrain-api
        image: somabrain/api:latest
        ports:
        - containerPort: 9696

        # Startup probe - allow time for initialization
        startupProbe:
          httpGet:
            path: /health
            port: 9696
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 10

        # Readiness probe - service ready for traffic
        readinessProbe:
          httpGet:
            path: /ready
            port: 9696
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3

        # Liveness probe - container is alive
        livenessProbe:
          httpGet:
            path: /live
            port: 9696
          initialDelaySeconds: 60
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3

        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

---

## Performance Monitoring

### Response Time Monitoring

Track API response times and identify bottlenecks:

```promql
# Average response time by operation
rate(somabrain_request_duration_seconds_sum[5m]) / rate(somabrain_request_duration_seconds_count[5m]) by (operation)

# 95th percentile response time trend
histogram_quantile(0.95, rate(somabrain_request_duration_seconds_bucket[5m])) by (operation)

# Slow operations (>1 second)
increase(somabrain_request_duration_seconds_bucket{le="1"}[5m]) / increase(somabrain_request_duration_seconds_count[5m])
```

### Memory Performance Monitoring

Monitor cognitive memory operations:

```promql
# Vector encoding performance
rate(somabrain_vector_encoding_duration_seconds_sum[5m]) / rate(somabrain_vector_encoding_duration_seconds_count[5m])

# Similarity computation performance
histogram_quantile(0.90, rate(somabrain_similarity_computation_duration_seconds_bucket[5m]))

# Memory recall accuracy (similarity scores)
histogram_quantile(0.50, rate(somabrain_similarity_scores_bucket[5m]))

# Reasoning operation success rate
rate(somabrain_reasoning_successful_total[5m]) / rate(somabrain_reasoning_operations_total[5m])
```

### Capacity Planning Metrics

Monitor resource utilization for capacity planning:

```promql
# Memory growth rate
deriv(somabrain_memories_total[1h]) * 24  # memories per day

# Storage growth rate
deriv(somabrain_storage_used_bytes[1h]) * 24 * 60 * 60  # bytes per day

# Request rate growth
deriv(rate(somabrain_requests_total[1h])[24h:1h])  # request rate change

# Resource utilization trends
avg_over_time(container_memory_usage_bytes{name="somabrain-api"}[24h]) / avg_over_time(container_spec_memory_limit_bytes{name="somabrain-api"}[24h])
```

---

## Alerting and Notifications

### AlertManager Configuration

Configure AlertManager for notifications:

```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'smtp.company.com:587'
  smtp_from: 'alerts@company.com'

route:
  group_by: ['alertname', 'tenant']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'default-receiver'
  routes:
  - match:
      severity: critical
    receiver: 'critical-alerts'
  - match:
      service: somabrain
    receiver: 'somabrain-team'

receivers:
- name: 'default-receiver'
  email_configs:
  - to: 'ops@company.com'
    subject: 'SomaBrain Alert: {{ .GroupLabels.alertname }}'

- name: 'critical-alerts'
  email_configs:
  - to: 'oncall@company.com'
    subject: 'CRITICAL: SomaBrain Alert'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/...'
    channel: '#critical-alerts'

- name: 'somabrain-team'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/...'
    channel: '#somabrain-ops'
    title: 'SomaBrain Alert: {{ .GroupLabels.alertname }}'
    text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
```

### Custom Alert Rules

Define application-specific alerts:

```yaml
# Custom SomaBrain alert rules
groups:
- name: somabrain.business.rules
  rules:

  # Tenant memory quota alert
  - alert: SomaBrainTenantQuotaExceeded
    expr: somabrain_tenant_memory_usage_bytes / somabrain_tenant_memory_limit_bytes > 0.90
    for: 5m
    labels:
      severity: warning
      tenant: "{{ $labels.tenant }}"
    annotations:
      summary: "Tenant {{ $labels.tenant }} memory usage at {{ $value | humanizePercentage }}"

  # Reasoning operation failures
  - alert: SomaBrainReasoningFailureRate
    expr: rate(somabrain_reasoning_failed_total[5m]) / rate(somabrain_reasoning_total[5m]) > 0.10
    for: 3m
    labels:
      severity: warning
    annotations:
      summary: "SomaBrain reasoning failure rate is {{ $value | humanizePercentage }}"

  # Vector index performance degradation
  - alert: SomaBrainVectorIndexSlow
    expr: histogram_quantile(0.95, rate(somabrain_vector_similarity_duration_seconds_bucket[5m])) > 0.5
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Vector similarity computation is slow: {{ $value }}s at 95th percentile"

  # Data consistency issues
  - alert: SomaBrainDataInconsistency
    expr: abs(somabrain_memories_postgres_count - somabrain_memories_redis_count) > 100
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "Memory count mismatch between PostgreSQL and Redis"
```

---

## Troubleshooting Monitoring Issues

### Common Monitoring Problems

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Metrics not appearing | No data in Prometheus UI | Check Prometheus scraping configuration and network connectivity |
| High cardinality metrics | Prometheus performance issues | Review metric labels and use recording rules |
| Missing alerts | No notifications for known issues | Verify AlertManager configuration and routing rules |
| Log parsing errors | Incomplete log data in Kibana | Check Logstash filters and field mappings |
| Health check failures | Service marked unhealthy | Review health check thresholds and dependencies |

### Monitoring Verification Steps

```bash
# 1. Verify Prometheus is scraping metrics
curl http://prometheus:9090/api/v1/targets

# 2. Check metric availability
curl http://prometheus:9090/api/v1/query?query=up{job="somabrain-api"}

# 3. Test AlertManager configuration
curl -X POST http://alertmanager:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{
    "labels": {"alertname": "TestAlert", "severity": "critical"},
    "annotations": {"summary": "Test alert"},
    "startsAt": "'$(date -Iseconds)'"
  }]'

# 4. Verify log flow
curl -X POST "http://elasticsearch:9200/somabrain-logs-*/_search" \
  -H "Content-Type: application/json" \
  -d '{"query": {"match": {"service": "somabrain-api"}}}'

# 5. Test health endpoints
curl http://localhost:9696/health
curl http://localhost:9696/metrics
```

**Verification**: Monitoring is working correctly when metrics are collected, dashboards show data, and test alerts are delivered.

---

**Common Errors**: See [FAQ](../user-manual/faq.md) for monitoring troubleshooting.

**References**:
- [Architecture Guide](architecture.md) for system component understanding
- [Deployment Guide](deployment.md) for production setup context
- [Backup and Recovery](backup-and-recovery.md) for operational procedures
- [Runbooks](runbooks/somabrain-api.md) for incident response procedures
