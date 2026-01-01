> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# Disaster Recovery & Constitution Restore

## Automated Backups
- **Redis**: `redis-cli --rdb` or managed snapshots. Store daily backups in S3/GCS with retention policies.
- **Kafka**: Enable log segment replication and regular snapshots. Use MirrorMaker2 for multi-region replication.
- **Postgres**: Run `pg_dump` (daily full + hourly incremental) to object storage.

## Multi-Region Replication
- **Redis**: Redis Enterprise/Cloud multi-region or Sentinel with cross-region replicas.
- **Kafka**: MirrorMaker2 or Confluent Replicator to mirror topics across regions.
- **Postgres**: Streaming replication or managed cross-region read replicas.

## Constitution Restore Workflow
+ Retrieve latest constitution snapshot from object storage.
+ Validate signatures and versions.
+ Restore via `somabrain/constitution/cloud.py` into Redis/Postgres.
+ Restart SomaBrain services so the constitution reloads.

## DR Drill Checklist
- Simulate region loss and restore from backup in alternate region.
- Validate data integrity plus system health.
- Record RTO/RPO outcomes and update this runbook after each drill.
