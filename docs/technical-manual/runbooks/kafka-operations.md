# Kafka Operations Runbook

**Purpose**: Step-by-step operational procedures for managing and troubleshooting Apache Kafka in SomaBrain production environments.

**Audience**: SREs, DevOps engineers, and platform teams responsible for Kafka operations.

**Prerequisites**: Access to production environment, Kafka CLI tools, and monitoring dashboards.

---

## Quick Navigation

- [Health Monitoring](#health-monitoring)
- [Topic Management](#topic-management)
- [Consumer Group Operations](#consumer-group-operations)
- [Performance Tuning](#performance-tuning)
- [Backup & Recovery](#backup--recovery)
- [Troubleshooting](#troubleshooting)
- [Emergency Procedures](#emergency-procedures)

---

## Health Monitoring

### Basic Health Check
```bash
# Check broker health
kafka-broker-api-versions.sh --bootstrap-server kafka:9092
# Expected: List of API versions

# Check cluster metadata
kafka-metadata-shell.sh --snapshot /var/kafka-logs/__cluster_metadata-0/00000000000000000000.log
# Expected: Cluster configuration details

# List all topics
kafka-topics.sh --bootstrap-server kafka:9092 --list
# Expected: audit_events, somabrain_events, outbox_events
```

### Key Metrics to Monitor
| Metric | Normal Range | Alert Threshold | Action |
|--------|--------------|-----------------|---------|
| **Broker CPU** | < 70% | > 85% | Scale up or optimize |
| **Disk Usage** | < 80% | > 90% | Clean logs or add storage |
| **Network I/O** | < 80% bandwidth | > 90% | Check for data spikes |
| **Under-replicated Partitions** | 0 | > 0 | Investigate broker issues |
| **Consumer Lag** | < 1000 messages | > 10000 | Scale consumers |
| **JVM Heap Usage** | < 75% | > 85% | Increase heap size |

### SomaBrain-Specific Health Checks
```bash
# Check audit events topic
kafka-console-consumer.sh --bootstrap-server kafka:9092 \
  --topic audit_events --from-beginning --max-messages 5

# Verify outbox publisher is working
kafka-console-consumer.sh --bootstrap-server kafka:9092 \
  --topic outbox_events --from-beginning --max-messages 5

# Check topic partition status
kafka-topics.sh --bootstrap-server kafka:9092 \
  --describe --topic audit_events
```

---

## Topic Management

### SomaBrain Topic Configuration
```bash
# Create audit events topic (if missing)
kafka-topics.sh --bootstrap-server kafka:9092 --create \
  --topic audit_events \
  --partitions 2 \
  --replication-factor 1 \
  --config cleanup.policy=delete \
  --config retention.ms=604800000 \
  --config compression.type=snappy

# Create outbox events topic
kafka-topics.sh --bootstrap-server kafka:9092 --create \
  --topic outbox_events \
  --partitions 2 \
  --replication-factor 1 \
  --config cleanup.policy=delete \
  --config retention.ms=259200000

# Create somabrain events topic
kafka-topics.sh --bootstrap-server kafka:9092 --create \
  --topic somabrain_events \
  --partitions 4 \
  --replication-factor 1 \
  --config cleanup.policy=delete \
  --config retention.ms=2592000000
```

### Topic Maintenance Operations
```bash
# Increase partition count (can only increase)
kafka-topics.sh --bootstrap-server kafka:9092 --alter \
  --topic audit_events --partitions 4

# Change topic configuration
kafka-configs.sh --bootstrap-server kafka:9092 --alter \
  --entity-type topics --entity-name audit_events \
  --add-config retention.ms=1209600000

# Delete old topic (careful!)
kafka-topics.sh --bootstrap-server kafka:9092 --delete \
  --topic old_topic_name

# Describe topic details
kafka-topics.sh --bootstrap-server kafka:9092 \
  --describe --topic audit_events
```

### Message Operations
```bash
# Produce test message
echo "test message" | kafka-console-producer.sh \
  --bootstrap-server kafka:9092 --topic audit_events

# Consume from specific offset
kafka-console-consumer.sh --bootstrap-server kafka:9092 \
  --topic audit_events --offset 100 --partition 0

# Get topic offset information
kafka-run-class.sh kafka.tools.GetOffsetShell \
  --bootstrap-server kafka:9092 --topic audit_events --time -1
```

---

## Consumer Group Operations

### SomaBrain Consumer Groups
```bash
# List all consumer groups
kafka-consumer-groups.sh --bootstrap-server kafka:9092 --list
# Expected: outbox_publisher_group, audit_processor_group

# Check outbox publisher status
kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --group outbox_publisher_group --describe

# Check audit processor status
kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --group audit_processor_group --describe
```

### Consumer Group Management
```bash
# Reset consumer group offset to beginning
kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --group outbox_publisher_group --reset-offsets \
  --to-earliest --topic outbox_events --execute

# Reset to specific timestamp
kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --group audit_processor_group --reset-offsets \
  --to-datetime 2024-01-01T00:00:00.000 \
  --topic audit_events --execute

# Delete consumer group (when no active consumers)
kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --group old_group_name --delete
```

### Consumer Lag Monitoring
```bash
# Monitor consumer lag in real-time
watch -n 5 "kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --group outbox_publisher_group --describe"

# Get lag for all groups
kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --all-groups --describe --state

# Script to check critical lag
#!/bin/bash
LAG=$(kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --group outbox_publisher_group --describe | \
  awk 'NR>1 {sum+=$5} END {print sum}')
if [ "$LAG" -gt 10000 ]; then
  echo "CRITICAL: Consumer lag is $LAG messages"
  exit 1
fi
```

---

## Performance Tuning

### Broker Configuration
```bash
# Increase heap size for high throughput
export KAFKA_HEAP_OPTS="-Xmx4G -Xms4G"

# Optimize JVM GC settings
export KAFKA_JVM_PERFORMANCE_OPTS="-XX:+UseG1GC -XX:MaxGCPauseMillis=20 -XX:InitiatingHeapOccupancyPercent=35"

# Configure broker properties
kafka-configs.sh --bootstrap-server kafka:9092 --alter \
  --entity-type brokers --entity-name 1 \
  --add-config num.network.threads=8,num.io.threads=16
```

### Producer Optimization
```bash
# Configure producer for high throughput
kafka-producer-perf-test.sh --topic audit_events \
  --num-records 100000 --record-size 1024 \
  --throughput 10000 --bootstrap-server kafka:9092 \
  --producer-props acks=1 \
  compression.type=snappy \
  batch.size=16384 \
  linger.ms=10
```

### Consumer Optimization
```bash
# Test consumer performance
kafka-consumer-perf-test.sh --topic audit_events \
  --bootstrap-server kafka:9092 \
  --messages 100000 \
  --consumer-props fetch.min.bytes=1048576 \
  max.poll.records=500 \
  session.timeout.ms=30000
```

### Disk and Network Tuning
```bash
# Check disk I/O
iostat -x 1

# Monitor network usage
iftop -i eth0

# Optimize log segment settings
kafka-configs.sh --bootstrap-server kafka:9092 --alter \
  --entity-type topics --entity-name audit_events \
  --add-config segment.bytes=1073741824,segment.ms=604800000
```

---

## Backup & Recovery

### Log Backup
```bash
# Create backup directory
mkdir -p /backup/kafka/$(date +%Y%m%d)

# Backup topic data (export messages)
kafka-console-consumer.sh --bootstrap-server kafka:9092 \
  --topic audit_events --from-beginning \
  --timeout-ms 60000 > /backup/kafka/$(date +%Y%m%d)/audit_events.log

# Backup topic metadata
kafka-topics.sh --bootstrap-server kafka:9092 --describe > \
  /backup/kafka/$(date +%Y%m%d)/topics_metadata.txt

# Backup consumer group offsets
kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --all-groups --describe > \
  /backup/kafka/$(date +%Y%m%d)/consumer_groups.txt
```

### Restore Procedures
```bash
# Restore topic (recreate with same config)
# First get original config from backup
grep "audit_events" /backup/kafka/YYYYMMDD/topics_metadata.txt

# Recreate topic with original settings
kafka-topics.sh --bootstrap-server kafka:9092 --create \
  --topic audit_events --partitions 2 --replication-factor 1

# Restore messages
cat /backup/kafka/YYYYMMDD/audit_events.log | \
  kafka-console-producer.sh --bootstrap-server kafka:9092 \
  --topic audit_events
```

### Automated Backup Script
```bash
#!/bin/bash
# Daily Kafka backup script
BACKUP_DIR="/backup/kafka/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup critical topics
for topic in audit_events outbox_events somabrain_events; do
  echo "Backing up $topic..."
  timeout 300 kafka-console-consumer.sh \
    --bootstrap-server kafka:9092 \
    --topic "$topic" --from-beginning \
    --timeout-ms 60000 > "$BACKUP_DIR/${topic}.log"
done

# Backup metadata
kafka-topics.sh --bootstrap-server kafka:9092 --describe > \
  "$BACKUP_DIR/topics_metadata.txt"

# Compress backup
tar -czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"
rm -rf "$BACKUP_DIR"

echo "Backup completed: $BACKUP_DIR.tar.gz"
```

---

## Troubleshooting

### Broker Not Starting
**Symptoms**: Kafka service fails to start, connection refused
```bash
# Check Kafka logs
tail -f /var/log/kafka/server.log

# Check JVM heap space
grep "OutOfMemoryError" /var/log/kafka/server.log

# Verify disk space
df -h /var/kafka-logs

# Check port conflicts
netstat -tlnp | grep :9092

# Verify ZooKeeper connectivity (if using ZooKeeper mode)
echo "ruok" | nc zookeeper 2181
```

**Solution Steps**:
1. Increase JVM heap: `export KAFKA_HEAP_OPTS="-Xmx2G -Xms2G"`
2. Clean corrupted logs: `rm -rf /var/kafka-logs/__cluster_metadata-0/*.log`
3. Check and fix file permissions: `chown -R kafka:kafka /var/kafka-logs`
4. Restart with clean startup: `systemctl restart kafka`

### High Consumer Lag
**Symptoms**: Messages not processed, growing backlog
```bash
# Identify lagging consumers
kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --describe --all-groups | grep -v "^$\|GROUP\|TOPIC" | \
  awk '$5 > 1000 {print $1,$2,$5}'

# Check consumer thread health
ps aux | grep outbox_publisher

# Monitor partition distribution
kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --group outbox_publisher_group --describe
```

**Solution Steps**:
1. Scale up consumer instances
2. Increase consumer parallelism: `SOMABRAIN_OUTBOX_BATCH_SIZE=200`
3. Reset consumer offset if corruption: Use reset commands above
4. Check for consumer code issues in application logs

### Disk Space Issues
**Symptoms**: Broker stops accepting writes, log errors
```bash
# Check disk usage
df -h /var/kafka-logs

# Find largest log segments
du -sh /var/kafka-logs/*/* | sort -hr | head -10

# Check log retention settings
kafka-configs.sh --bootstrap-server kafka:9092 \
  --describe --entity-type topics
```

**Solution Steps**:
1. Reduce retention time: `kafka-configs.sh --alter --add-config retention.ms=86400000`
2. Force log cleanup: `kafka-log-dirs.sh --bootstrap-server kafka:9092`
3. Delete unnecessary topics
4. Add more disk space

### Network Connectivity Issues
**Symptoms**: Timeouts, connection errors
```bash
# Test broker connectivity
telnet kafka 9092

# Check network statistics
ss -tuln | grep :9092

# Test from different network
curl -v telnet://kafka:9092

# Check iptables rules
iptables -L | grep 9092
```

**Solution Steps**:
1. Verify firewall configuration
2. Check advertised.listeners setting
3. Test DNS resolution: `nslookup kafka`
4. Restart networking service if needed

---

## Emergency Procedures

### Broker Failure
**Immediate Actions**:
1. Check if broker can be restarted: `systemctl restart kafka`
2. If hardware failure, redirect traffic to healthy brokers
3. Monitor under-replicated partitions
4. Scale up replacement broker if needed

### Data Corruption
**Immediate Actions**:
1. Stop affected broker: `systemctl stop kafka`
2. Backup corrupted data: `cp -r /var/kafka-logs /backup/corrupted-$(date +%s)`
3. Clean corrupted segments: `rm -f /var/kafka-logs/TOPIC-PARTITION/*.index`
4. Let Kafka rebuild indexes on restart
5. Start broker: `systemctl start kafka`

### Performance Emergency
**Immediate Actions**:
1. Increase JVM heap: `export KAFKA_HEAP_OPTS="-Xmx8G -Xms8G"`
2. Enable compression: `compression.type=snappy` on producers
3. Increase consumer parallelism
4. Monitor and scale horizontally

### Security Incident
**Immediate Actions**:
1. Enable SASL authentication if not already enabled
2. Rotate all certificates and passwords
3. Audit all topic access logs
4. Implement IP whitelist if possible
5. Review all consumer group memberships

---

## Verification Checklist

After any Kafka operation, verify:
- [ ] All brokers are running: `systemctl status kafka`
- [ ] Topics are accessible: `kafka-topics.sh --list`
- [ ] SomaBrain can produce events: Check audit log generation
- [ ] Outbox publisher is consuming: Check consumer group lag
- [ ] No error logs: `tail /var/log/kafka/server.log`
- [ ] Disk space is adequate: `df -h /var/kafka-logs`
- [ ] Network connectivity: `telnet kafka 9092`

---

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Not enough replicas` | Insufficient brokers | Add brokers or reduce replication factor |
| `Offset out of range` | Consumer offset invalid | Reset consumer group offset |
| `Request timed out` | Network/performance issue | Check network and tune timeouts |
| `Topic already exists` | Attempting to recreate | Use --if-not-exists flag or different name |
| `InvalidReplicationFactor` | More replicas than brokers | Reduce replication factor |
| `UnknownTopicOrPartition` | Topic deleted/not created | Recreate topic with proper configuration |

---

## References

- [SomaBrain API Runbook](somabrain-api.md) for application-level events
- [Monitoring Guide](../monitoring.md) for Kafka dashboard setup
- [Security Policies](../security/secrets-policy.md) for Kafka authentication
- [Backup & Recovery](../backup-and-recovery.md) for disaster recovery
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/) for advanced configuration