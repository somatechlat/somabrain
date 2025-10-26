# SomaBrain API Operations Runbook

**Purpose**: Operational procedures for managing the SomaBrain API service in production.

**Audience**: SREs, DevOps engineers, and on-call personnel.

**Prerequisites**: Access to production systems, monitoring dashboards, and basic SomaBrain architecture knowledge.

---

## Service Overview

The SomaBrain API is the primary FastAPI service handling cognitive memory operations. It exposes REST endpoints for memory storage, recall, and system introspection.

### Key Endpoints
- `GET /health` - Health check aggregating all dependencies
- `GET /metrics` - Prometheus metrics export
- `POST /remember` - Store new memories with semantic encoding
- `POST /recall` - Retrieve memories based on semantic queries
- `POST /plan` - Generate reasoning plans based on stored knowledge

### Dependencies
- **Redis**: Working memory cache and session state
- **PostgreSQL**: Persistent storage for metadata and audit logs
- **Kafka**: Event streaming for audit trails (optional)
- **OPA**: Policy engine for authorization
- **Memory Service**: Long-term memory HTTP service

---

## Health Monitoring

### Health Check Interpretation
```bash
# Check service health
curl -f https://api.somabrain.company.com/health

# Healthy response (200 OK)
{
  "status": "healthy",
  "timestamp": "2025-10-15T12:00:00Z",
  "components": {
    "redis": {"status": "healthy", "latency_ms": 1.2},
    "postgres": {"status": "healthy", "latency_ms": 2.1},
    "kafka": {"status": "healthy", "latency_ms": 0.8},
    "opa": {"status": "healthy", "latency_ms": 1.0}
  },
  "version": "v0.1.0",
  "mode": "production"
}

# Degraded response (503 Service Unavailable)
{
  "status": "degraded",
  "components": {
    "redis": {"status": "unhealthy", "error": "Connection timeout"}
  }
}
```

### Key Metrics to Monitor
| Metric | Normal Range | Alert Threshold |
|--------|-------------|-----------------|
| `somabrain_requests_total` | Varies by load | Rate change >50% |
| `somabrain_request_duration_seconds` | p95 <100ms | p95 >500ms |
| `somabrain_memory_operations_total` | Steady growth | Error rate >1% |
| `somabrain_density_trace_error_total` | 0 | >0 |
| `somabrain_redis_connection_errors` | 0 | >5/min |

---

## Common Incidents & Resolutions

### 1. Service Returns 503 Health Check Failures

**Symptoms**:
- `/health` endpoint returns HTTP 503
- Load balancer marks service unhealthy
- User requests being dropped

**Diagnosis**:
```bash
# Check health endpoint details
curl -i https://api.somabrain.company.com/health

# Check component connectivity
kubectl logs deployment/somabrain -n somabrain-prod | grep -i "health\|redis\|postgres"

# Test direct component access
redis-cli -h redis.somabrain-prod.svc.cluster.local ping
psql -h postgres.somabrain-prod.svc.cluster.local -U somabrain -c "SELECT 1;"
```

**Resolution Steps**:
1. Identify failing component from health response
2. For Redis failures: Check Redis service status and memory usage
3. For PostgreSQL failures: Verify connection pool and query performance
4. For OPA failures: Check policy engine logs and configuration
5. Restart affected components if necessary
6. Monitor health recovery

### 2. High Memory Operation Latency

**Symptoms**:
- `/remember` and `/recall` endpoints slow (>1s response time)
- `somabrain_request_duration_seconds` p95 elevated
- User complaints about slow cognitive responses

**Diagnosis**:
```bash
# Check request latency metrics
curl -s https://api.somabrain.company.com/metrics | grep duration_seconds

# Analyze slow operations
kubectl logs deployment/somabrain -n somabrain-prod | grep "SLOW\|latency" | tail -20

# Check memory service performance
curl -w "Time: %{time_total}s\n" -s https://memory.somabrain.company.com/health
```

**Resolution Steps**:
1. Check memory service health and performance
2. Verify Redis cache hit rates and memory usage
3. Review PostgreSQL query performance and connection pools
4. Scale horizontally if CPU/memory constrained
5. Clear problematic cache entries if identified
6. Consider memory service scaling

### 3. Authentication/Authorization Failures

**Symptoms**:
- Requests returning HTTP 401/403 errors
- `somabrain_auth_failures_total` metric increasing
- Valid user tokens being rejected

**Diagnosis**:
```bash
# Check OPA policy engine
curl -f http://opa.somabrain-prod.svc.cluster.local:8181/health

# Review authentication logs
kubectl logs deployment/somabrain -n somabrain-prod | grep -i "auth\|jwt\|token"

# Test JWT token validation
curl -X POST https://api.somabrain.company.com/recall \
  -H "Authorization: Bearer ${TEST_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "k": 1}'
```

**Resolution Steps**:
1. Verify OPA policy engine is responsive
2. Check JWT secret configuration matches issuer
3. Validate token expiration and signing algorithm
4. Review OPA policies for syntax errors
5. Restart OPA service if policies corrupted
6. Re-issue tokens if JWT secret rotated

### 4. Memory Integrity Violations

**Symptoms**:
- `somabrain_density_trace_error_total` > 0
- Mathematical invariant violations in logs
- Inconsistent recall results

**Diagnosis**:
```bash
# Check density matrix health
curl -s https://api.somabrain.company.com/metrics | grep density_trace_error

# Review mathematical violations
kubectl logs deployment/somabrain -n somabrain-prod | grep -i "trace\|psd\|invariant"

# Test memory consistency
curl -X POST https://api.somabrain.company.com/recall \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{"query": "known_test_memory", "k": 5}'
```

**Resolution Steps**:
1. Identify source of trace violations from logs
2. Check for concurrent memory modifications
3. Validate Redis data integrity
4. Restore from last known good density matrix backup
5. Re-initialize density matrix if corruption detected
6. Review recent code changes for mathematical bugs

---

## Scaling Operations

### Horizontal Scaling
```bash
# Scale up API replicas
kubectl scale deployment somabrain --replicas=10 -n somabrain-prod

# Monitor scaling progress
kubectl get pods -n somabrain-prod -w

# Verify load distribution
curl -s https://api.somabrain.company.com/metrics | grep requests_total
```

### Vertical Scaling
```yaml
# Update resource limits
apiVersion: apps/v1
kind: Deployment
metadata:
  name: somabrain
spec:
  template:
    spec:
      containers:
      - name: somabrain
        resources:
          requests:
            memory: "4Gi"
            cpu: "2000m"
          limits:
            memory: "8Gi"
            cpu: "4000m"
```

### Auto-scaling Configuration
```bash
# Check HPA status
kubectl get hpa somabrain-hpa -n somabrain-prod

# Adjust scaling thresholds
kubectl patch hpa somabrain-hpa -n somabrain-prod -p '{"spec":{"metrics":[{"type":"Resource","resource":{"name":"cpu","target":{"type":"Utilization","averageUtilization":60}}}]}}'
```

---

## Maintenance Procedures

### Rolling Updates
```bash
# Update to new image version
kubectl set image deployment/somabrain somabrain=somabrain:v0.2.0 -n somabrain-prod

# Monitor rollout
kubectl rollout status deployment/somabrain -n somabrain-prod

# Rollback if issues
kubectl rollout undo deployment/somabrain -n somabrain-prod
```

### Configuration Updates
```bash
# Update ConfigMap
kubectl patch configmap somabrain-config -n somabrain-prod --patch '{"data":{"SOMABRAIN_RATE_RPS":"150"}}'

# Restart pods to pick up config
kubectl rollout restart deployment/somabrain -n somabrain-prod
```

### Cache Maintenance
```bash
# Clear Redis working memory cache
redis-cli -h redis.somabrain-prod.svc.cluster.local FLUSHDB

# Verify cache cleared
redis-cli -h redis.somabrain-prod.svc.cluster.local INFO memory
```

---

## Emergency Procedures

### Service Outage Response

**Immediate Actions (5 minutes)**:
1. Acknowledge alerts and notify team
2. Check health endpoint and identify failing components
3. Scale to more replicas if capacity issue
4. Enable maintenance mode if data corruption suspected

**Investigation (15 minutes)**:
1. Analyze metrics for root cause
2. Review recent deployments and configuration changes
3. Check infrastructure status (network, storage, compute)
4. Identify blast radius and affected users

**Recovery (30 minutes)**:
1. Implement immediate fix or rollback
2. Verify service recovery via health checks
3. Monitor metrics for stability
4. Communicate status to stakeholders

### Data Recovery
```bash
# Emergency memory service failover
kubectl patch service memory-service -n somabrain-prod -p '{"spec":{"selector":{"app":"memory-service-backup"}}}'

# Restore from backup if corruption detected
./scripts/restore-from-backup.sh $(date -d "1 hour ago" +%Y%m%d_%H%M%S)

# Validate restore success
curl -X POST https://api.somabrain.company.com/recall -d '{"query": "validation_test", "k": 1}'
```

---

## Monitoring References

- Use Prometheus UI for ad-hoc queries and Alertmanager for alert triage. External dashboards are not used in this project.

## Alert Runbook Links

- [Redis Operations](redis-operations.md) for Redis-specific issues
- [Postgres Operations](postgres-operations.md) for database issues
- [Kafka Operations](kafka-operations.md) for event streaming problems
- [Incident Response](incident-response.md) for general incident procedures

---

**Verification**: Service operational status confirmed via health checks and metrics dashboards.

**Common Errors**:
- Container startup failures → Check resource limits and image availability
- Network connectivity issues → Verify service mesh and DNS configuration
- Performance degradation → Review resource utilization and scaling policies

**References**:
- [Architecture Documentation](../architecture.md) for system understanding
- [Deployment Guide](../deployment.md) for configuration details
- [Monitoring Setup](../monitoring.md) for observability configuration