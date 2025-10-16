# Postgres Operations Runbook

**Purpose**: Step-by-step operational procedures for managing and troubleshooting PostgreSQL in SomaBrain production environments.

**Audience**: DBAs, SREs, DevOps engineers, and platform teams responsible for database operations.

**Prerequisites**: Access to production environment, PostgreSQL client tools, and monitoring dashboards.

---

## Quick Navigation

- [Health Monitoring](#health-monitoring)
- [Database Operations](#database-operations)
- [User and Security Management](#user-and-security-management)
- [Performance Tuning](#performance-tuning)
- [Backup & Recovery](#backup--recovery)
- [Troubleshooting](#troubleshooting)
- [Emergency Procedures](#emergency-procedures)

---

## Health Monitoring

### Basic Health Check
```bash
# Check PostgreSQL service status
systemctl status postgresql

# Test database connectivity
psql -h postgres-host -U soma -d somabrain -c "SELECT version();"

# Check database size
psql -h postgres-host -U soma -d somabrain -c "
SELECT pg_database.datname,
       pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_database
ORDER BY pg_database_size(pg_database.datname) DESC;"
```

### Key Metrics to Monitor
| Metric | Normal Range | Alert Threshold | Action |
|--------|--------------|-----------------|---------|
| **Connection Count** | < 80% max_connections | > 90% | Check for connection leaks |
| **Database Size** | < 80% disk | > 90% | Archive/cleanup old data |
| **Cache Hit Ratio** | > 95% | < 90% | Increase shared_buffers |
| **Transaction Rate** | Baseline ±20% | ±50% | Investigate load changes |
| **Lock Waits** | < 1% of queries | > 5% | Identify blocking queries |
| **Replication Lag** | < 5 seconds | > 30 seconds | Check network/load |

### SomaBrain-Specific Health Checks
```sql
-- Check SomaBrain database health
\c somabrain

-- Verify key tables exist
SELECT schemaname, tablename, tableowner 
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;

-- Check recent audit log entries
SELECT count(*) as recent_audits
FROM audit_log 
WHERE created_at > NOW() - INTERVAL '1 hour';

-- Monitor outbox table size
SELECT pg_size_pretty(pg_total_relation_size('outbox_events')) as outbox_size;

-- Check for long-running queries
SELECT now() - pg_stat_activity.query_start AS duration,
       query,
       state
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
  AND state = 'active';
```

---

## Database Operations

### Connection Management
```sql
-- Check current connections
SELECT datname, count(*) as connections
FROM pg_stat_activity
GROUP BY datname
ORDER BY connections DESC;

-- Identify idle connections
SELECT pid, usename, application_name, state, 
       now() - state_change as idle_time
FROM pg_stat_activity
WHERE state = 'idle'
  AND now() - state_change > interval '30 minutes';

-- Terminate idle connections (careful!)
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
  AND now() - state_change > interval '1 hour'
  AND datname = 'somabrain';
```

### Schema Management
```sql
-- Create SomaBrain database (initial setup)
CREATE DATABASE somabrain OWNER soma;

-- Connect to SomaBrain database
\c somabrain

-- Create audit log table
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255),
    event_type VARCHAR(100),
    event_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    user_id VARCHAR(255)
);

-- Create outbox events table
CREATE TABLE IF NOT EXISTS outbox_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100),
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending'
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_audit_log_tenant_created 
ON audit_log(tenant_id, created_at);

CREATE INDEX IF NOT EXISTS idx_outbox_status_created 
ON outbox_events(status, created_at);
```

### Table Maintenance
```sql
-- Analyze table statistics
ANALYZE audit_log;
ANALYZE outbox_events;

-- Vacuum tables to reclaim space
VACUUM VERBOSE audit_log;
VACUUM VERBOSE outbox_events;

-- Reindex for performance
REINDEX TABLE audit_log;
REINDEX TABLE outbox_events;

-- Check table bloat
SELECT schemaname, tablename,
       attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
  AND tablename IN ('audit_log', 'outbox_events');
```

### Data Archiving
```sql
-- Archive old audit logs (older than 30 days)
CREATE TABLE audit_log_archive (LIKE audit_log);

INSERT INTO audit_log_archive
SELECT * FROM audit_log
WHERE created_at < NOW() - INTERVAL '30 days';

-- Verify archive count
SELECT count(*) FROM audit_log_archive;

-- Delete archived records
DELETE FROM audit_log
WHERE created_at < NOW() - INTERVAL '30 days';

-- Clean up processed outbox events
DELETE FROM outbox_events
WHERE status = 'processed'
  AND processed_at < NOW() - INTERVAL '7 days';
```

---

## User and Security Management

### User Administration
```sql
-- Create SomaBrain application user
CREATE USER somabrain_app WITH PASSWORD 'secure_password';

-- Grant necessary permissions
GRANT CONNECT ON DATABASE somabrain TO somabrain_app;
GRANT USAGE ON SCHEMA public TO somabrain_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO somabrain_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO somabrain_app;

-- Create read-only monitoring user
CREATE USER somabrain_monitor WITH PASSWORD 'monitor_password';
GRANT CONNECT ON DATABASE somabrain TO somabrain_monitor;
GRANT USAGE ON SCHEMA public TO somabrain_monitor;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO somabrain_monitor;

-- List all users and permissions
\du
```

### Security Configuration
```sql
-- Enable row-level security (if needed)
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Create tenant isolation policy
CREATE POLICY tenant_isolation ON audit_log
FOR ALL TO somabrain_app
USING (tenant_id = current_setting('app.current_tenant', true));

-- Check active connections and their privileges
SELECT datname, usename, application_name, 
       client_addr, state, query
FROM pg_stat_activity
WHERE datname = 'somabrain';
```

### Password and Authentication
```bash
# Update PostgreSQL user password
psql -h postgres-host -U postgres -c "
ALTER USER soma PASSWORD 'new_secure_password';"

# Enable SSL (in postgresql.conf)
ssl = on
ssl_cert_file = '/path/to/server.crt'
ssl_key_file = '/path/to/server.key'

# Configure authentication (in pg_hba.conf)
# Allow local connections with md5
local   somabrain   soma                    md5
# Allow network connections with SSL
hostssl somabrain   soma    10.0.0.0/8     md5
```

---

## Performance Tuning

### Configuration Optimization
```sql
-- Check current configuration
SHOW ALL;

-- Key performance settings (postgresql.conf)
-- shared_buffers = 256MB          # 25% of RAM
-- effective_cache_size = 1GB      # 75% of RAM  
-- work_mem = 4MB                  # Per operation
-- maintenance_work_mem = 64MB     # For maintenance
-- max_connections = 100           # Adjust based on load
-- checkpoint_completion_target = 0.9
-- wal_buffers = 16MB
-- random_page_cost = 1.1          # For SSD storage
```

### Query Performance Analysis
```sql
-- Enable query logging (postgresql.conf)
-- log_statement = 'all'
-- log_min_duration_statement = 1000  # Log queries > 1 second

-- Check slow queries
SELECT query, calls, total_time, mean_time, rows
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;

-- Identify missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
  AND tablename IN ('audit_log', 'outbox_events');

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

### Index Optimization
```sql
-- Create performance indexes based on queries
CREATE INDEX CONCURRENTLY idx_audit_log_event_type_created
ON audit_log(event_type, created_at);

CREATE INDEX CONCURRENTLY idx_outbox_events_tenant_status
ON outbox_events(tenant_id, status) WHERE status = 'pending';

-- Monitor index bloat
SELECT schemaname, tablename, indexname,
       pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Connection Pooling
```bash
# Install and configure PgBouncer
sudo apt-get install pgbouncer

# Configure pgbouncer.ini
[databases]
somabrain = host=localhost port=5432 dbname=somabrain

[pgbouncer]
listen_port = 6432
listen_addr = *
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
default_pool_size = 20
max_client_conn = 100
```

---

## Backup & Recovery

### Automated Backup Setup
```bash
#!/bin/bash
# PostgreSQL backup script for SomaBrain
BACKUP_DIR="/backup/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="somabrain"
DB_HOST="postgres-host"
DB_USER="soma"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Full database backup
pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
  --format=custom --compress=9 --verbose \
  --file="$BACKUP_DIR/somabrain_full_$DATE.backup"

# Schema-only backup
pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
  --schema-only --format=plain \
  --file="$BACKUP_DIR/somabrain_schema_$DATE.sql"

# Data-only backup for critical tables
pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
  --data-only --format=custom \
  --table=audit_log --table=outbox_events \
  --file="$BACKUP_DIR/somabrain_data_$DATE.backup"

# Compress and timestamp
tar -czf "$BACKUP_DIR/somabrain_backup_$DATE.tar.gz" \
  "$BACKUP_DIR/somabrain_"*"_$DATE."*

# Clean up individual files
rm "$BACKUP_DIR/somabrain_"*"_$DATE.backup"
rm "$BACKUP_DIR/somabrain_"*"_$DATE.sql"

# Retain only last 7 days of backups
find "$BACKUP_DIR" -name "somabrain_backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/somabrain_backup_$DATE.tar.gz"
```

### Point-in-Time Recovery Setup
```bash
# Enable WAL archiving (postgresql.conf)
wal_level = replica
archive_mode = on
archive_command = 'cp %p /backup/postgresql/wal_archive/%f'
max_wal_senders = 3
checkpoint_timeout = 15min
```

### Recovery Procedures
```bash
# Full database restore
createdb -h postgres-host -U postgres somabrain_restore

pg_restore -h postgres-host -U postgres -d somabrain_restore \
  --verbose --clean --if-exists \
  /backup/postgresql/somabrain_backup_20241016.tar.gz

# Point-in-time recovery
pg_basebackup -h postgres-host -U postgres -D /var/lib/postgresql/restore \
  -Ft -z -P

# Create recovery.conf
echo "restore_command = 'cp /backup/postgresql/wal_archive/%f %p'" > \
  /var/lib/postgresql/restore/recovery.conf
echo "recovery_target_time = '2024-10-16 14:30:00'" >> \
  /var/lib/postgresql/restore/recovery.conf
```

### Backup Verification
```bash
#!/bin/bash
# Verify backup integrity
BACKUP_FILE="/backup/postgresql/somabrain_backup_20241016.tar.gz"

# Extract backup
tar -xzf "$BACKUP_FILE" -C /tmp/

# Test restore to temporary database
createdb test_restore_$(date +%s)
pg_restore -d test_restore_$(date +%s) /tmp/somabrain_full_*.backup

# Verify table counts match
psql -d test_restore_$(date +%s) -c "
SELECT 'audit_log' as table_name, count(*) FROM audit_log
UNION ALL
SELECT 'outbox_events' as table_name, count(*) FROM outbox_events;"

# Clean up
dropdb test_restore_$(date +%s)
rm -rf /tmp/somabrain_*
```

---

## Troubleshooting

### Connection Issues
**Symptoms**: Connection refused, timeout errors
```bash
# Check PostgreSQL service
systemctl status postgresql

# Check listening ports
netstat -tlnp | grep :5432

# Test local connectivity
psql -h localhost -U soma -d somabrain

# Check configuration
grep -E "listen_addresses|port" /etc/postgresql/*/main/postgresql.conf
```

**Solution Steps**:
1. Restart PostgreSQL: `systemctl restart postgresql`
2. Check firewall: `ufw status | grep 5432`
3. Verify pg_hba.conf authentication rules
4. Check disk space: `df -h /var/lib/postgresql`

### Performance Issues
**Symptoms**: Slow queries, high CPU usage
```sql
-- Find blocking queries
SELECT blocked_locks.pid AS blocked_pid,
       blocked_activity.usename AS blocked_user,
       blocking_locks.pid AS blocking_pid,
       blocking_activity.usename AS blocking_user,
       blocked_activity.query AS blocked_statement,
       blocking_activity.query AS blocking_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity 
     ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks 
     ON blocking_locks.locktype = blocked_locks.locktype
     AND blocking_locks.DATABASE IS NOT DISTINCT FROM blocked_locks.DATABASE
     AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
     AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
     AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
     AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
     AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
     AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
     AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
     AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
     AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity 
     ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.GRANTED;
```

**Solution Steps**:
1. Kill blocking queries: `SELECT pg_terminate_backend(PID);`
2. Increase shared_buffers and work_mem
3. Create missing indexes based on slow query log
4. Run VACUUM and ANALYZE on affected tables

### Disk Space Issues
**Symptoms**: Database stops accepting writes
```bash
# Check disk usage
df -h /var/lib/postgresql

# Find largest tables
psql -d somabrain -c "
SELECT tablename,
       pg_size_pretty(pg_total_relation_size(tablename::regclass)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(tablename::regclass) DESC;"

# Check WAL file accumulation
ls -la /var/lib/postgresql/*/main/pg_wal/ | wc -l
```

**Solution Steps**:
1. Archive old audit logs (see Data Archiving section)
2. Run VACUUM FULL on large tables during maintenance window
3. Clean up old WAL files: `pg_archivecleanup /backup/postgresql/wal_archive $(ls /var/lib/postgresql/*/main/pg_wal/ | tail -1)`
4. Add more disk space

### Replication Issues
**Symptoms**: Replica lag, replication stopped
```sql
-- Check replication status on master
SELECT client_addr, state, sent_lsn, write_lsn, flush_lsn, replay_lsn,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;

-- Check replication lag on replica
SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) AS lag_seconds;
```

**Solution Steps**:
1. Check network connectivity between master and replica
2. Verify replication user permissions
3. Check for disk space issues on replica
4. Restart replication: `SELECT pg_reload_conf();`

---

## Emergency Procedures

### Database Corruption
**Immediate Actions**:
1. Stop accepting writes: Put application in read-only mode
2. Assess corruption scope: `SELECT * FROM pg_stat_database;`
3. Attempt repair: `REINDEX DATABASE somabrain;`
4. If repair fails, restore from backup
5. Document corruption details for analysis

### Lost Connection Emergency
**Immediate Actions**:
1. Check PostgreSQL process: `ps aux | grep postgres`
2. Review logs: `tail -f /var/log/postgresql/postgresql-*.log`
3. Restart service: `systemctl restart postgresql`
4. If restart fails, restore from backup to new instance
5. Update application connection strings

### Data Loss Emergency
**Immediate Actions**:
1. Stop all write operations immediately
2. Assess data loss scope and timeframe
3. Restore from most recent backup
4. Apply WAL files for point-in-time recovery if available
5. Notify stakeholders and document incident

### Security Breach
**Immediate Actions**:
1. Change all database passwords immediately
2. Review pg_hba.conf and restrict access
3. Audit all recent database activity
4. Check for unauthorized schema changes
5. Enable additional logging and monitoring

---

## Verification Checklist

After any PostgreSQL operation, verify:
- [ ] PostgreSQL service is running: `systemctl status postgresql`
- [ ] Database is accessible: `psql -h postgres-host -U soma -d somabrain -c "SELECT 1;"`
- [ ] SomaBrain can connect: Check application health endpoint
- [ ] Key tables exist and have data: Check audit_log and outbox_events
- [ ] No error logs: `tail /var/log/postgresql/postgresql-*.log`
- [ ] Backup completed successfully: Check backup file exists and size
- [ ] Replication is working (if configured): Check lag metrics

---

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `FATAL: password authentication failed` | Wrong password/user | Update credentials in pg_hba.conf |
| `FATAL: database does not exist` | Database not created | Create database: `createdb somabrain` |
| `ERROR: permission denied` | Insufficient privileges | Grant permissions: `GRANT ALL ON DATABASE` |
| `ERROR: could not extend file` | Disk space full | Free disk space or add storage |
| `WARNING: there is no transaction in progress` | Application connection issues | Check connection pooling settings |
| `ERROR: deadlock detected` | Conflicting transactions | Implement retry logic in application |

---

## References

- [SomaBrain API Runbook](somabrain-api.md) for application-level database operations
- [Monitoring Guide](../monitoring.md) for PostgreSQL dashboard setup
- [Security Policies](../security/secrets-policy.md) for database authentication
- [Backup & Recovery](../backup-and-recovery.md) for disaster recovery procedures
- [PostgreSQL Documentation](https://www.postgresql.org/docs/) for advanced configuration