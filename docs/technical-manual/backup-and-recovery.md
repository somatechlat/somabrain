# Backup and Recovery Procedures

**Purpose**: This document provides comprehensive disaster recovery procedures for SomaBrain production environments.

**Audience**: SREs, platform engineers, and incident response teams.

**Prerequisites**: Access to backup systems, cloud storage, and understanding of SomaBrain data architecture.

---

## Backup Strategy Overview

SomaBrain implements a multi-tier backup strategy covering all critical data:

- **Redis Working Memory**: Real-time snapshots and AOF logs
- **PostgreSQL Metadata**: Daily full backups with point-in-time recovery
- **Kafka Event Streams**: Topic snapshots and cross-region replication
- **Configuration State**: Kubernetes manifests and environment configurations
- **Memory Embeddings**: Vector store backups via memory service

### Backup Schedule
| Component | Frequency | Retention | Storage Location |
|-----------|-----------|-----------|------------------|
| Redis RDB | Every 6 hours | 7 days | S3://backups/redis/ |
| PostgreSQL Full | Daily at 02:00 UTC | 30 days | S3://backups/postgres/ |
| PostgreSQL WAL | Continuous | 7 days | S3://backups/postgres/wal/ |
| Kafka Topics | Daily at 03:00 UTC | 14 days | S3://backups/kafka/ |
| Configurations | On change | 90 days | Git repository + S3 |
| Memory Vectors | Daily at 04:00 UTC | 30 days | S3://backups/memory/ |

---

## Redis Backup & Recovery

### Automated Redis Backup
```bash
#!/bin/bash
# scripts/backup-redis.sh

BACKUP_DIR="/tmp/redis-backup-$(date +%Y%m%d_%H%M%S)"
S3_BUCKET="s3://company-backups/somabrain/redis"

# Create RDB snapshot
redis-cli -h redis.somabrain-prod.svc.cluster.local BGSAVE
while [ "$(redis-cli -h redis.somabrain-prod.svc.cluster.local LASTSAVE)" = "$(redis-cli -h redis.somabrain-prod.svc.cluster.local LASTSAVE)" ]; do
  sleep 1
done

# Copy RDB file
kubectl cp somabrain-prod/redis-0:/data/dump.rdb "$BACKUP_DIR/dump.rdb"

# Backup AOF if enabled
kubectl cp somabrain-prod/redis-0:/data/appendonly.aof "$BACKUP_DIR/appendonly.aof"

# Upload to S3 with encryption
aws s3 cp "$BACKUP_DIR" "$S3_BUCKET/$(date +%Y%m%d_%H%M%S)/" \
  --recursive --sse aws:kms --sse-kms-key-id alias/somabrain-backups

# Cleanup local files
rm -rf "$BACKUP_DIR"

# Verify backup
aws s3 ls "$S3_BUCKET/$(date +%Y%m%d_%H%M%S)/"
```

### Redis Recovery Procedure
```bash
# 1. Stop Redis service
kubectl scale deployment redis --replicas=0 -n somabrain-prod

# 2. Download backup from S3
RESTORE_DATE="20251015_140000"  # Specify restore point
aws s3 cp "s3://company-backups/somabrain/redis/$RESTORE_DATE/" /tmp/restore/ --recursive

# 3. Replace Redis data files
kubectl cp /tmp/restore/dump.rdb somabrain-prod/redis-0:/data/dump.rdb
kubectl cp /tmp/restore/appendonly.aof somabrain-prod/redis-0:/data/appendonly.aof

# 4. Set proper permissions
kubectl exec -n somabrain-prod redis-0 -- chown redis:redis /data/dump.rdb /data/appendonly.aof

# 5. Start Redis service
kubectl scale deployment redis --replicas=1 -n somabrain-prod

# 6. Verify data restoration
kubectl exec -n somabrain-prod redis-0 -- redis-cli ping
kubectl exec -n somabrain-prod redis-0 -- redis-cli dbsize
```

---

## PostgreSQL Backup & Recovery

### Automated PostgreSQL Backup
```bash
#!/bin/bash
# scripts/backup-postgres.sh

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/tmp/postgres-backup-$BACKUP_DATE"
S3_BUCKET="s3://company-backups/somabrain/postgres"

mkdir -p "$BACKUP_DIR"

# Full database dump
kubectl exec -n somabrain-prod postgres-0 -- pg_dump -U somabrain -d somabrain \
  --format=custom --compress=9 --verbose > "$BACKUP_DIR/somabrain.dump"

# Schema-only dump for rapid restore testing
kubectl exec -n somabrain-prod postgres-0 -- pg_dump -U somabrain -d somabrain \
  --schema-only --format=plain > "$BACKUP_DIR/schema.sql"

# Backup global objects (roles, tablespaces)
kubectl exec -n somabrain-prod postgres-0 -- pg_dumpall --globals-only \
  > "$BACKUP_DIR/globals.sql"

# WAL archiving status
kubectl exec -n somabrain-prod postgres-0 -- psql -U somabrain -d somabrain \
  -c "SELECT * FROM pg_stat_archiver;" > "$BACKUP_DIR/wal_status.txt"

# Upload to S3
aws s3 cp "$BACKUP_DIR" "$S3_BUCKET/$BACKUP_DATE/" \
  --recursive --sse aws:kms --sse-kms-key-id alias/somabrain-backups

# Cleanup
rm -rf "$BACKUP_DIR"

# Verify backup integrity
aws s3 ls "$S3_BUCKET/$BACKUP_DATE/" | grep -E "(dump|sql)$"
```

### PostgreSQL Point-in-Time Recovery
```bash
#!/bin/bash
# scripts/restore-postgres-pitr.sh

RESTORE_TIME="2025-10-15 14:00:00 UTC"  # Specify recovery target time
BACKUP_DATE="20251015_020000"           # Base backup date

# 1. Stop PostgreSQL
kubectl scale statefulset postgres --replicas=0 -n somabrain-prod

# 2. Download base backup
aws s3 cp "s3://company-backups/somabrain/postgres/$BACKUP_DATE/" /tmp/restore/ --recursive

# 3. Download WAL files
aws s3 sync "s3://company-backups/somabrain/postgres/wal/" /tmp/restore/wal/

# 4. Restore base backup
kubectl exec -n somabrain-prod postgres-0 -- rm -rf /var/lib/postgresql/data/*
kubectl cp /tmp/restore/somabrain.dump somabrain-prod/postgres-0:/tmp/

# 5. Start PostgreSQL in recovery mode
cat > /tmp/recovery.conf << EOF
restore_command = 'cp /tmp/wal/%f %p'
recovery_target_time = '$RESTORE_TIME'
recovery_target_action = 'promote'
EOF

kubectl cp /tmp/recovery.conf somabrain-prod/postgres-0:/var/lib/postgresql/data/

# 6. Start PostgreSQL
kubectl scale statefulset postgres --replicas=1 -n somabrain-prod

# 7. Monitor recovery
kubectl logs -f statefulset/postgres -n somabrain-prod | grep recovery

# 8. Verify recovery completion
kubectl exec -n somabrain-prod postgres-0 -- psql -U somabrain -d somabrain \
  -c "SELECT pg_is_in_recovery();"
```

---

## Kafka Backup & Recovery

### Kafka Topic Backup
```bash
#!/bin/bash
# scripts/backup-kafka.sh

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/tmp/kafka-backup-$BACKUP_DATE"
S3_BUCKET="s3://company-backups/somabrain/kafka"

mkdir -p "$BACKUP_DIR"

# Backup topic configurations
kubectl exec -n somabrain-prod kafka-0 -- kafka-configs.sh \
  --bootstrap-server localhost:9092 --describe --entity-type topics \
  > "$BACKUP_DIR/topic-configs.txt"

# Backup consumer group offsets
for group in $(kubectl exec -n somabrain-prod kafka-0 -- kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 --list); do
  kubectl exec -n somabrain-prod kafka-0 -- kafka-consumer-groups.sh \
    --bootstrap-server localhost:9092 --describe --group "$group" \
    > "$BACKUP_DIR/offsets-$group.txt"
done

# Backup topic data using MirrorMaker2
kubectl exec -n somabrain-prod kafka-0 -- kafka-mirror-maker.sh \
  --consumer.config /opt/kafka/config/backup-consumer.properties \
  --producer.config /opt/kafka/config/backup-producer.properties \
  --whitelist "audit.*,metrics.*" \
  --offset.storage.topic __backup_offsets

# Upload to S3
aws s3 cp "$BACKUP_DIR" "$S3_BUCKET/$BACKUP_DATE/" \
  --recursive --sse aws:kms

# Cleanup
rm -rf "$BACKUP_DIR"
```

---

## Configuration Backup & Recovery

### Kubernetes Configuration Backup
```bash
#!/bin/bash
# scripts/backup-k8s-config.sh

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/tmp/k8s-config-$BACKUP_DATE"
NAMESPACE="somabrain-prod"

mkdir -p "$BACKUP_DIR"

# Backup all ConfigMaps
kubectl get configmaps -n "$NAMESPACE" -o yaml > "$BACKUP_DIR/configmaps.yaml"

# Backup all Secrets (encrypted)
kubectl get secrets -n "$NAMESPACE" -o yaml > "$BACKUP_DIR/secrets.yaml"

# Backup Deployments
kubectl get deployments -n "$NAMESPACE" -o yaml > "$BACKUP_DIR/deployments.yaml"

# Backup Services
kubectl get services -n "$NAMESPACE" -o yaml > "$BACKUP_DIR/services.yaml"

# Backup PVCs
kubectl get pvc -n "$NAMESPACE" -o yaml > "$BACKUP_DIR/pvcs.yaml"

# Backup Ingress
kubectl get ingress -n "$NAMESPACE" -o yaml > "$BACKUP_DIR/ingress.yaml"

# Create manifest bundle
tar -czf "$BACKUP_DIR.tar.gz" -C /tmp "k8s-config-$BACKUP_DATE"

# Upload encrypted bundle
aws s3 cp "$BACKUP_DIR.tar.gz" "s3://company-backups/somabrain/configs/" \
  --sse aws:kms --sse-kms-key-id alias/somabrain-backups

# Cleanup
rm -rf "$BACKUP_DIR" "$BACKUP_DIR.tar.gz"
```

---

## Disaster Recovery Procedures

### Complete Environment Recovery

**Scenario**: Total environment loss, rebuild from backups

**Recovery Time Objective (RTO)**: 4 hours
**Recovery Point Objective (RPO)**: 1 hour

#### Phase 1: Infrastructure Recovery (60 minutes)
```bash
# 1. Deploy Kubernetes cluster
terraform apply -var-file="prod.tfvars" infra/

# 2. Install operators and base services
helm install cert-manager jetstack/cert-manager --namespace cert-manager --create-namespace
helm install ingress-nginx ingress-nginx/ingress-nginx

# 3. Create namespace and RBAC
kubectl create namespace somabrain-prod
kubectl apply -f k8s/rbac/
```

#### Phase 2: Data Recovery (120 minutes)
```bash
# 1. Deploy PostgreSQL and restore data
helm install postgres bitnami/postgresql -f values/postgres-prod.yaml
./scripts/restore-postgres-pitr.sh

# 2. Deploy Redis and restore data
helm install redis bitnami/redis -f values/redis-prod.yaml
./scripts/restore-redis.sh

# 3. Deploy Kafka and restore topics
helm install kafka bitnami/kafka -f values/kafka-prod.yaml
./scripts/restore-kafka.sh
```

#### Phase 3: Application Recovery (60 minutes)
```bash
# 1. Restore configurations
aws s3 cp s3://company-backups/somabrain/configs/latest.tar.gz /tmp/
tar -xzf /tmp/latest.tar.gz
kubectl apply -f k8s-config-*/

# 2. Deploy SomaBrain application
helm install somabrain somabrain/somabrain -f values/prod.yaml

# 3. Verify service health
kubectl get pods -n somabrain-prod
curl -f https://api.somabrain.company.com/health
```

### Partial Service Recovery

**Scenario**: Single component failure with data corruption

#### Redis Recovery
```bash
# 1. Identify corruption
kubectl logs deployment/somabrain -n somabrain-prod | grep -i "redis\|corruption"

# 2. Isolate Redis instance
kubectl patch service redis -n somabrain-prod -p '{"spec":{"selector":{"app":"redis-backup"}}}'

# 3. Restore from backup
./scripts/restore-redis.sh "$(date -d '2 hours ago' +%Y%m%d_%H%M%S)"

# 4. Validate restore
redis-cli -h redis.somabrain-prod.svc.cluster.local ping
redis-cli -h redis.somabrain-prod.svc.cluster.local dbsize

# 5. Switch traffic back
kubectl patch service redis -n somabrain-prod -p '{"spec":{"selector":{"app":"redis"}}}'
```

---

## Backup Validation & Testing

### Monthly DR Drill Checklist
- [ ] Verify all backup jobs completed successfully in past 7 days
- [ ] Test Redis restore in staging environment
- [ ] Test PostgreSQL PITR in isolated environment
- [ ] Validate Kafka topic restoration
- [ ] Test configuration restore process
- [ ] Measure actual RTO/RPO vs targets
- [ ] Document any issues and update procedures

### Backup Integrity Validation
```bash
#!/bin/bash
# scripts/validate-backups.sh

# Test Redis backup restoration
REDIS_BACKUP=$(aws s3 ls s3://company-backups/somabrain/redis/ | tail -1 | awk '{print $4}')
./scripts/test-redis-restore.sh "$REDIS_BACKUP"

# Test PostgreSQL backup integrity
PG_BACKUP=$(aws s3 ls s3://company-backups/somabrain/postgres/ | tail -1 | awk '{print $4}')
kubectl exec test-postgres -- pg_restore --list "/tmp/$PG_BACKUP/somabrain.dump"

# Verify backup encryption
aws s3api head-object --bucket company-backups --key "somabrain/redis/$REDIS_BACKUP/dump.rdb" \
  --query ServerSideEncryption
```

### Automated Backup Monitoring
```yaml
# monitoring/backup-alerts.yml
groups:
- name: backup-alerts
  rules:
  - alert: BackupJobFailed
    expr: backup_job_success{job="redis-backup"} == 0
    for: 30m
    labels:
      severity: critical
    annotations:
      summary: "Redis backup job failed"
      description: "Redis backup has not completed successfully in the last 6 hours"

  - alert: BackupDataMissing
    expr: time() - backup_last_success_timestamp > 86400
    labels:
      severity: warning
    annotations:
      summary: "Backup data is stale"
      description: "No successful backup completed in the last 24 hours"
```

---

**Verification**: All backup and recovery procedures tested monthly with documented RTO/RPO measurements.

**Common Errors**:
- Backup corruption → Verify checksums and retry from alternate backup
- Storage access failures → Check IAM permissions and network connectivity
- Incomplete restores → Validate backup integrity and storage capacity

**References**:
- [Architecture Documentation](../architecture.md) for data flow understanding
- [Monitoring Guide](../monitoring.md) for backup alerting setup
- [Security Policies](../security/) for encryption and access controls
- [Runbooks](../runbooks/) for component-specific recovery procedures