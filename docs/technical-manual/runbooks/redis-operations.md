# Redis Operations Runbook

**Purpose**: Step-by-step operational procedures for managing and troubleshooting Redis in SomaBrain production environments.

**Audience**: SREs, DevOps engineers, and platform teams responsible for Redis operations.

**Prerequisites**: Access to production environment, Redis CLI tools, and monitoring dashboards.

---

## Quick Navigation

- [Health Monitoring](#health-monitoring)
- [Common Operations](#common-operations)
- [Performance Tuning](#performance-tuning)
- [Backup & Recovery](#backup--recovery)
- [Troubleshooting](#troubleshooting)
- [Emergency Procedures](#emergency-procedures)

---

## Health Monitoring

### Basic Health Check
```bash
# Check Redis connectivity
redis-cli -h redis-host -p 6379 ping
# Expected: PONG

# Check memory usage
redis-cli -h redis-host -p 6379 info memory
# Monitor: used_memory_human, used_memory_peak_human

# Check connected clients
redis-cli -h redis-host -p 6379 info clients
# Monitor: connected_clients, blocked_clients
```

### Key Metrics to Monitor
| Metric | Normal Range | Alert Threshold | Action |
|--------|--------------|-----------------|---------|
| **Memory Usage** | < 80% of max | > 90% | Scale up or flush unused keys |
| **Connected Clients** | < 1000 | > 1500 | Investigate connection leaks |
| **CPU Usage** | < 70% | > 85% | Check for expensive operations |
| **Hit Rate** | > 95% | < 90% | Review cache strategy |
| **Evicted Keys** | 0 | > 100/min | Increase memory or TTL tuning |

### Verification Commands
```bash
# Check SomaBrain working memory health
redis-cli -h redis-host -p 6379 --scan --pattern "tenant:*" | wc -l
# Should show tenant memory counts

# Verify TTL settings
redis-cli -h redis-host -p 6379 ttl "tenant:example:wm:active"
# Should show positive TTL value

# Check for memory leaks
redis-cli -h redis-host -p 6379 memory usage "tenant:example:wm:active"
# Monitor memory per key
```

---

## Common Operations

### Working Memory Management
```bash
# List all tenant working memories
redis-cli -h redis-host -p 6379 --scan --pattern "tenant:*:wm:*"

# Check specific tenant memory usage
redis-cli -h redis-host -p 6379 hgetall "tenant:production_agent:wm:active"

# Clear tenant working memory (emergency)
redis-cli -h redis-host -p 6379 del "tenant:TENANT_NAME:wm:active"

# Set working memory TTL (extend session)
redis-cli -h redis-host -p 6379 expire "tenant:TENANT_NAME:wm:active" 3600
```

### Cache Statistics
```bash
# Get detailed statistics
redis-cli -h redis-host -p 6379 info stats

# Check keyspace information
redis-cli -h redis-host -p 6379 info keyspace

# Monitor command statistics
redis-cli -h redis-host -p 6379 monitor
# Use sparingly - impacts performance
```

### Configuration Management
```bash
# View current configuration
redis-cli -h redis-host -p 6379 config get "*"

# Set memory policy (if needed)
redis-cli -h redis-host -p 6379 config set maxmemory-policy allkeys-lru

# Set maximum memory limit
redis-cli -h redis-host -p 6379 config set maxmemory 2gb

# Save configuration to disk
redis-cli -h redis-host -p 6379 config rewrite
```

---

## Performance Tuning

### Memory Optimization
```bash
# Enable memory compression
redis-cli -h redis-host -p 6379 config set hash-max-ziplist-entries 512
redis-cli -h redis-host -p 6379 config set hash-max-ziplist-value 64

# Optimize list compression
redis-cli -h redis-host -p 6379 config set list-compress-depth 1

# Set appropriate eviction policy
redis-cli -h redis-host -p 6379 config set maxmemory-policy volatile-lru
```

### Connection Tuning
```bash
# Increase timeout for long operations
redis-cli -h redis-host -p 6379 config set timeout 300

# Set TCP keepalive
redis-cli -h redis-host -p 6379 config set tcp-keepalive 60

# Optimize client buffer limits
redis-cli -h redis-host -p 6379 config set client-output-buffer-limit "normal 32mb 8mb 60"
```

### Persistence Tuning
```bash
# Configure RDB snapshots
redis-cli -h redis-host -p 6379 config set save "900 1 300 10 60 10000"

# Disable persistence for pure cache workloads
redis-cli -h redis-host -p 6379 config set save ""
redis-cli -h redis-host -p 6379 config set appendonly no
```

---

## Backup & Recovery

### Manual Backup
```bash
# Create immediate snapshot
redis-cli -h redis-host -p 6379 bgsave
# Check completion: redis-cli -h redis-host -p 6379 lastsave

# Export specific keys (tenant backup)
redis-cli -h redis-host -p 6379 --scan --pattern "tenant:TENANT_NAME:*" | \
  xargs redis-cli -h redis-host -p 6379 mget > tenant_backup.txt

# Full database dump
redis-cli -h redis-host -p 6379 --rdb /backup/redis-dump-$(date +%Y%m%d).rdb
```

### Recovery Procedures
```bash
# Stop Redis service
systemctl stop redis

# Replace RDB file
cp /backup/redis-dump-YYYYMMDD.rdb /var/lib/redis/dump.rdb
chown redis:redis /var/lib/redis/dump.rdb

# Start Redis service
systemctl start redis

# Verify data integrity
redis-cli -h redis-host -p 6379 dbsize
```

### Automated Backup Verification
```bash
#!/bin/bash
# Backup verification script
BACKUP_FILE="/backup/redis-dump-$(date +%Y%m%d).rdb"
if [ -f "$BACKUP_FILE" ]; then
    SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE")
    if [ "$SIZE" -gt 1024 ]; then
        echo "✅ Backup successful: $SIZE bytes"
    else
        echo "❌ Backup failed: File too small"
        exit 1
    fi
else
    echo "❌ Backup failed: File not found"
    exit 1
fi
```

---

## Troubleshooting

### High Memory Usage
**Symptoms**: Memory usage > 90%, evictions occurring
```bash
# Identify large keys
redis-cli -h redis-host -p 6379 --bigkeys

# Find memory usage per key type
redis-cli -h redis-host -p 6379 --memkeys

# Check for memory leaks (keys without TTL)
redis-cli -h redis-host -p 6379 --scan --pattern "*" | \
  while read key; do 
    ttl=$(redis-cli -h redis-host -p 6379 ttl "$key")
    if [ "$ttl" = "-1" ]; then 
      echo "No TTL: $key"
    fi
  done
```

**Solution Steps**:
1. Increase memory allocation if legitimate usage
2. Set TTL on persistent keys: `redis-cli expire key 3600`
3. Clear unused tenant data: `redis-cli del "tenant:old_tenant:*"`
4. Optimize data structures or move to long-term storage

### Connection Issues
**Symptoms**: Connection refused, timeout errors
```bash
# Check Redis process
ps aux | grep redis-server

# Check listening ports
netstat -tlnp | grep :6379

# Test connectivity
telnet redis-host 6379

# Check system resources
free -h
df -h
```

**Solution Steps**:
1. Restart Redis service: `systemctl restart redis`
2. Check firewall rules: `iptables -L | grep 6379`
3. Verify Redis configuration: `redis-cli config get bind`
4. Check system resources and restart if needed

### Performance Degradation
**Symptoms**: Slow response times, high CPU usage
```bash
# Check slow queries
redis-cli -h redis-host -p 6379 slowlog get 10

# Monitor real-time commands
redis-cli -h redis-host -p 6379 monitor | head -50

# Check blocked clients
redis-cli -h redis-host -p 6379 client list | grep blocked
```

**Solution Steps**:
1. Identify expensive operations in slowlog
2. Optimize client code to avoid blocking operations
3. Increase Redis memory if swapping occurs
4. Consider Redis clustering for high load

### Data Corruption
**Symptoms**: Inconsistent data, Redis crashes
```bash
# Check Redis logs
tail -f /var/log/redis/redis-server.log

# Verify RDB file integrity
redis-check-rdb /var/lib/redis/dump.rdb

# Check AOF file integrity
redis-check-aof /var/lib/redis/appendonly.aof
```

**Solution Steps**:
1. Stop Redis: `systemctl stop redis`
2. Fix AOF if corrupted: `redis-check-aof --fix /var/lib/redis/appendonly.aof`
3. Restore from backup if RDB corrupted
4. Start Redis: `systemctl start redis`

---

## Emergency Procedures

### Redis Service Down
**Immediate Actions**:
1. Check service status: `systemctl status redis`
2. Review logs: `journalctl -u redis -f`
3. Attempt restart: `systemctl restart redis`
4. If restart fails, restore from backup

### Memory Emergency (OOM)
**Immediate Actions**:
1. Clear non-essential cache: `redis-cli flushdb`
2. Increase memory limit temporarily: `redis-cli config set maxmemory 4gb`
3. Set aggressive eviction: `redis-cli config set maxmemory-policy allkeys-lru`
4. Scale horizontally if possible

### Data Loss Emergency
**Immediate Actions**:
1. Stop all writes to Redis
2. Assess data loss scope: `redis-cli dbsize`
3. Restore from latest backup
4. Notify affected tenants and applications
5. Document incident for post-mortem

### Security Breach
**Immediate Actions**:
1. Change Redis password: `redis-cli config set requirepass NEW_PASSWORD`
2. Restrict network access: Update firewall rules
3. Audit all data access: Review logs
4. Rotate all application credentials
5. Follow security incident response procedure

---

## Verification Checklist

After any Redis operation, verify:
- [ ] Redis service is running: `systemctl status redis`
- [ ] Memory usage is normal: `redis-cli info memory`
- [ ] SomaBrain can connect: `curl http://somabrain-api/health`
- [ ] Working memory functions: Test remember/recall operations
- [ ] No error logs: `journalctl -u redis --since "5 minutes ago"`
- [ ] Backup integrity: Verify latest backup exists and is valid

---

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `NOAUTH Authentication required` | Missing/wrong password | Set AUTH: `redis-cli -a PASSWORD` |
| `OOM command not allowed` | Memory limit exceeded | Increase memory or clear cache |
| `Connection refused` | Redis service down | Restart service: `systemctl restart redis` |
| `READONLY You can't write against a read only replica` | Connected to replica | Connect to master instance |
| `MOVED` errors | Redis cluster topology changed | Update client cluster configuration |

---

## References

- [SomaBrain API Runbook](somabrain-api.md) for application-level operations
- [Monitoring Guide](../monitoring.md) for dashboard setup
- [Security Policies](../security/secrets-policy.md) for Redis authentication
- [Backup & Recovery](../backup-and-recovery.md) for disaster recovery procedures
- [Redis Official Documentation](https://redis.io/documentation) for advanced configuration