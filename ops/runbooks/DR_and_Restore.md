# Disaster Recovery (DR) & Constitution Restore

## Automated Backups
- **Redis:** Use `redis-cli --rdb` or managed service snapshotting (see cloud provider docs). Schedule daily backups to S3 or GCS with retention policy.
- **Kafka:** Enable log segment replication and periodic snapshots. Use MirrorMaker2 for multi-region replication.
- **Postgres:** Use `pg_dump` or managed backup. Schedule daily full and hourly incremental backups to object storage.

## Multi-Region Replication
- **Redis:** Use Redis Enterprise/Cloud multi-region or Redis Sentinel with cross-region replicas.
- **Kafka:** Use MirrorMaker2 or Confluent Replicator for cross-region topic replication.
- **Postgres:** Use streaming replication or managed cross-region read replicas.

## Constitution Restore Workflow
1. Retrieve latest constitution snapshot from object storage (S3/GCS).
2. Validate signatures and version.
3. Restore to Redis/Postgres using `somabrain/constitution/cloud.py`.
4. Restart SomaBrain services to reload constitution.

## DR Drill Checklist
- Simulate region loss; restore from backup in alternate region.
- Validate data integrity and service health.
- Document RTO/RPO and update runbook after each drill.
