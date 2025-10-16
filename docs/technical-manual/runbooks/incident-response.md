# Incident Response Runbook

**Purpose**: General incident handling procedures, escalation protocols, and emergency response for SomaBrain production environments.

**Audience**: SREs, DevOps engineers, on-call personnel, and incident commanders.

**Prerequisites**: Access to production systems, monitoring dashboards, and communication channels.

---

## Quick Navigation

- [Incident Classification](#incident-classification)
- [Immediate Response](#immediate-response)
- [Communication Protocols](#communication-protocols)
- [Investigation Procedures](#investigation-procedures)
- [Recovery Actions](#recovery-actions)
- [Post-Incident Review](#post-incident-review)
- [Escalation Matrix](#escalation-matrix)

---

## Incident Classification

### Severity Levels

| Severity | Impact | Response Time | Examples |
|----------|---------|---------------|----------|
| **P0 - Critical** | Complete service unavailable | 15 minutes | API down, data corruption, security breach |
| **P1 - High** | Major functionality impaired | 1 hour | High error rates, significant performance degradation |
| **P2 - Medium** | Minor functionality affected | 4 hours | Non-critical feature issues, minor performance impact |
| **P3 - Low** | Minimal impact | 24 hours | Documentation errors, minor cosmetic issues |

### SomaBrain-Specific Incident Types

#### Memory System Failures
- **Working Memory Unavailable**: Redis down or inaccessible
- **Long-term Memory Loss**: Memory service connectivity issues
- **Memory Corruption**: Inconsistent or corrupted cognitive data
- **Cognitive Performance**: Slow recall or reasoning operations

#### API Service Issues
- **Complete Outage**: SomaBrain API unresponsive
- **Partial Functionality**: Some endpoints failing
- **Authentication Failures**: Auth service issues
- **Rate Limiting Problems**: Excessive throttling or bypass

#### Data Platform Issues
- **Audit Trail Failures**: Events not being logged
- **Database Connectivity**: Postgres access issues
- **Message Queue Problems**: Kafka broker issues
- **Monitoring Blindness**: Observability system failures

---

## Immediate Response

### First 5 Minutes - Incident Detection
```bash
# 1. Confirm incident scope
curl -f http://localhost:9696/health || echo "API DOWN"

# 2. Check system status
docker compose ps  # For containerized deployment
systemctl status somabrain  # For service deployment

# 3. Quick health assessment
curl -s http://localhost:9696/metrics | grep -E "(up|error|latency)"

# 4. Check recent logs
docker compose logs --tail=50 somabrain
# OR
journalctl -u somabrain --since "5 minutes ago"
```

### Incident Declaration Checklist
- [ ] **Severity determined** using classification matrix
- [ ] **Incident commander assigned** (on-call rotation)
- [ ] **Communication channel created** (#incident-YYYYMMDD-HHMM)
- [ ] **Initial status posted** to stakeholders
- [ ] **Monitoring focused** on affected components
- [ ] **Log collection started** for affected timeframe

### Initial Assessment Commands
```bash
# Check all SomaBrain components
echo "=== API Health ==="
curl -f http://localhost:9696/health

echo "=== Redis Status ==="
redis-cli ping

echo "=== Postgres Status ==="
psql -h postgres-host -U soma -d somabrain -c "SELECT 1;"

echo "=== Kafka Status ==="
kafka-topics.sh --bootstrap-server kafka:9092 --list

echo "=== System Resources ==="
df -h
free -h
top -bn1 | head -20
```

---

## Communication Protocols

### Internal Communication

#### Incident Channel Creation
```bash
# Create dedicated Slack channel
# Format: #incident-YYYYMMDD-HHMM-brief-description
# Example: #incident-20241016-1430-api-outage

# Initial message template:
🚨 INCIDENT DECLARED 🚨
Severity: P1
Summary: SomaBrain API experiencing high error rates
IC: @john.doe
Start Time: 2024-10-16 14:30 UTC
Status: Investigating

Components Affected:
- SomaBrain API (500 errors)
- Memory operations (degraded)

Current Actions:
- Investigating error spike in logs
- Checking Redis connectivity
- Monitoring system resources
```

#### Status Update Template
```
⏰ UPDATE - [TIME] UTC
Status: [Investigating/Identified/Monitoring/Resolved]
Duration: [X minutes]

What we know:
- [Key findings]
- [Root cause if identified]

Current actions:
- [What we're doing now]
- [Next steps]

Impact:
- [Customer impact description]
- [Affected functionality]

ETA: [Best estimate for resolution]
```

### External Communication

#### Customer Status Page Updates
```markdown
**INVESTIGATING** - We are investigating reports of increased response times

**IDENTIFIED** - We have identified the issue with memory retrieval operations

**MONITORING** - A fix has been applied and we are monitoring the results

**RESOLVED** - This incident has been resolved
```

#### Escalation Triggers
- **15 minutes**: No progress on P0 incident
- **1 hour**: No progress on P1 incident  
- **Customer complaints**: Multiple reports received
- **Media attention**: Public visibility of incident
- **Data breach suspected**: Security team involvement

---

## Investigation Procedures

### Log Analysis Workflow
```bash
# 1. Collect logs from incident timeframe
START_TIME="2024-10-16 14:25:00"
END_TIME="2024-10-16 14:35:00"

# SomaBrain API logs
docker compose logs somabrain --since "$START_TIME" --until "$END_TIME" > api_logs.txt

# System logs
journalctl --since "$START_TIME" --until "$END_TIME" > system_logs.txt

# 2. Look for error patterns
grep -E "(ERROR|FATAL|Exception)" api_logs.txt | sort | uniq -c | sort -nr

# 3. Check for resource exhaustion
grep -E "(memory|disk|cpu)" system_logs.txt

# 4. Identify error correlation
grep -A5 -B5 "first_error_timestamp" api_logs.txt
```

### Performance Investigation
```bash
# Check current performance
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 5}'

# Monitor real-time metrics
watch -n 5 'curl -s http://localhost:9696/metrics | grep -E "(request_duration|error_total|memory_usage)"'

# Check database performance
psql -h postgres-host -U soma -d somabrain -c "
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC LIMIT 10;"
```

### Root Cause Analysis Checklist
- [ ] **Timeline established** - When did the issue start?
- [ ] **Change correlation** - Recent deployments or config changes?
- [ ] **Resource constraints** - CPU, memory, disk, network limits?
- [ ] **External dependencies** - Third-party service issues?
- [ ] **Error patterns** - Specific error messages or codes?
- [ ] **Load analysis** - Traffic spikes or unusual patterns?
- [ ] **Configuration drift** - Settings changed from baseline?

---

## Recovery Actions

### Standard Recovery Procedures

#### Service Recovery
```bash
# 1. Graceful restart attempt
docker compose restart somabrain

# 2. If graceful restart fails, force restart
docker compose down
docker compose up -d

# 3. Verify service health
timeout 60 bash -c 'until curl -f http://localhost:9696/health; do sleep 5; done'

# 4. Run smoke tests
python tests/smoke_test.py
```

#### Database Recovery
```bash
# 1. Check database connectivity
psql -h postgres-host -U soma -d somabrain -c "SELECT version();"

# 2. If connection fails, check service
systemctl status postgresql
systemctl restart postgresql

# 3. Verify SomaBrain tables
psql -h postgres-host -U soma -d somabrain -c "
SELECT count(*) FROM audit_log WHERE created_at > NOW() - INTERVAL '1 hour';"

# 4. If data corruption suspected, restore from backup
# See postgres-operations.md for detailed recovery procedures
```

#### Memory System Recovery
```bash
# 1. Redis recovery
redis-cli ping || systemctl restart redis

# 2. Clear corrupted cache if needed
redis-cli flushdb  # ONLY if corruption confirmed

# 3. Verify memory operations
curl -X POST http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -d '{"payload": {"content": "test recovery"}}'

curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{"query": "test recovery"}'
```

#### Traffic Management
```bash
# 1. Enable maintenance mode (if available)
curl -X POST http://localhost:9696/admin/maintenance \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"enabled": true}'

# 2. Scale up resources (Kubernetes)
kubectl scale deployment somabrain --replicas=5

# 3. Update load balancer if needed
# Update upstream servers or enable backup pools

# 4. Gradual traffic restoration
# Increase traffic percentage slowly: 10% -> 25% -> 50% -> 100%
```

### Rollback Procedures
```bash
# 1. Application rollback (if recent deployment)
docker compose down
docker tag somabrain:previous somabrain:latest
docker compose up -d

# 2. Configuration rollback
git checkout HEAD~1 -- config/
docker compose restart somabrain

# 3. Database rollback (EXTREME CAUTION)
# Only if data corruption and recent backup available
# See postgres-operations.md for point-in-time recovery
```

---

## Post-Incident Review

### Immediate Post-Resolution (Within 2 hours)
- [ ] **Incident closed** in tracking system
- [ ] **Final status update** posted to all channels
- [ ] **Customer communication** sent if external impact
- [ ] **Monitoring normalized** - alerts cleared
- [ ] **Quick lessons** documented while fresh

### Post-Incident Review Process (Within 48 hours)

#### Data Collection
```bash
# Package incident artifacts
mkdir incident_$(date +%Y%m%d_%H%M%S)
cd incident_$(date +%Y%m%d_%H%M%S)

# Copy logs
cp ../api_logs.txt .
cp ../system_logs.txt .

# Export metrics for incident timeframe
curl "http://prometheus:9090/api/v1/query_range?query=up&start=2024-10-16T14:25:00Z&end=2024-10-16T14:35:00Z&step=15s" > metrics.json

# Create timeline
echo "14:30 - Initial alert received" > timeline.txt
echo "14:32 - Incident declared" >> timeline.txt
echo "14:35 - Root cause identified" >> timeline.txt
echo "14:40 - Fix applied" >> timeline.txt
echo "14:45 - Service restored" >> timeline.txt
```

#### PIR Document Template
```markdown
# Post-Incident Review - [DATE] - [INCIDENT TITLE]

## Summary
- **Incident ID**: INC-YYYYMMDD-###
- **Severity**: P1
- **Duration**: 15 minutes
- **Impact**: 500 users affected, 2.5% error rate
- **Root Cause**: Redis memory exhaustion

## Timeline
| Time | Event | Actions Taken |
|------|-------|---------------|
| 14:30 | Alert triggered | On-call paged |
| 14:32 | Incident declared | IC assigned, channel created |
| 14:35 | Root cause identified | Redis memory at 100% |
| 14:40 | Fix applied | Increased memory, cleared cache |
| 14:45 | Service restored | Error rate normalized |

## What Went Well
- Fast detection (2 minutes)
- Clear communication
- Effective troubleshooting

## What Went Wrong
- No proactive memory monitoring
- No auto-scaling for Redis
- Documentation outdated

## Action Items
- [ ] Implement Redis memory alerts (@john.doe, 2024-10-20)
- [ ] Add auto-scaling configuration (@jane.smith, 2024-10-25)
- [ ] Update runbook procedures (@team, 2024-10-18)

## Lessons Learned
- Need better capacity planning
- Monitoring gaps in memory subsystem
- Recovery procedures worked well
```

---

## Escalation Matrix

### On-Call Rotation
| Role | Primary | Secondary | Escalation |
|------|---------|-----------|------------|
| **SRE On-Call** | +1-555-0101 | +1-555-0102 | Engineering Manager |
| **Security On-Call** | +1-555-0201 | +1-555-0202 | Security Manager |
| **Engineering On-Call** | +1-555-0301 | +1-555-0302 | CTO |
| **Product On-Call** | +1-555-0401 | +1-555-0402 | VP Product |

### Escalation Triggers and Contacts

#### Technical Escalation
- **15 minutes P0**: Engineering Manager
- **30 minutes P0**: CTO + VP Engineering  
- **1 hour P0**: CEO notification
- **Multi-service impact**: Architecture team lead
- **Data integrity issues**: Data team lead + Legal

#### Business Escalation
- **Customer complaints**: Customer Success Manager
- **Revenue impact**: VP Sales + CFO
- **Media inquiries**: Marketing + Legal
- **Regulatory concerns**: Compliance Officer
- **Partner SLA breach**: VP Partnerships

#### Security Escalation
- **Suspected breach**: CISO immediately
- **Data exposure**: Legal + Compliance + CISO
- **Authentication bypass**: Security team + Engineering lead
- **External threat**: Law enforcement liaison (if needed)

### Contact Information
```
Emergency Hotline: +1-555-BRAIN-1 (24/7)
Incident Commander Rotation: https://oncall.somabrain.com
Status Page Admin: status-admin@somabrain.com
Executive Notifications: exec-incidents@somabrain.com
Legal/Compliance: legal-emergency@somabrain.com
```

---

## Verification Checklist

After incident resolution, verify:
- [ ] **All services healthy**: Check /health endpoints
- [ ] **Performance normalized**: Latency and error rates normal  
- [ ] **Monitoring active**: All alerts and dashboards functional
- [ ] **Customer impact resolved**: No ongoing user reports
- [ ] **Documentation updated**: Runbooks reflect any changes made
- [ ] **Team notified**: All stakeholders aware of resolution
- [ ] **Incident logged**: Complete record in incident management system

---

## Common Incident Patterns

| Pattern | Typical Cause | Quick Fix | Prevention |
|---------|---------------|-----------|------------|
| **Memory Service Timeout** | Redis overload | Restart Redis, clear cache | Memory alerting, scaling |
| **Database Lock Contention** | Long-running queries | Kill blocking queries | Query optimization |
| **High Error Rate Spike** | Deployment issue | Rollback deployment | Canary releases |
| **Authentication Failures** | Token expiration | Refresh auth service | Token monitoring |
| **Gradual Performance Degradation** | Memory leaks | Restart services | Resource monitoring |

---

## References

- [SomaBrain API Runbook](somabrain-api.md) for service-specific procedures
- [Redis Operations](redis-operations.md) for memory system recovery
- [Postgres Operations](postgres-operations.md) for database recovery  
- [Kafka Operations](kafka-operations.md) for message queue issues
- [Monitoring Guide](../monitoring.md) for observability setup
- [Security Policies](../security/) for security incident procedures