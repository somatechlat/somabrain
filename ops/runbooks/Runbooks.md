> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# SomaBrain Runbooks

## Constitution Rotation
1. Generate new constitution and threshold signatures.
2. Validate signatures using `scripts/constitution_sign.py`.
3. Publish to object storage and update Redis/Postgres.
4. Restart services to load new constitution.
5. Monitor metrics and audit logs for successful rotation.

## Kafka Upgrade
1. Snapshot all topics and consumer offsets.
2. Deploy new Kafka version in parallel or rolling fashion.
3. Migrate topics and verify replication.
4. Cut over consumers and producers.
5. Monitor for lag, errors, and data loss.

## Memory Integrity Incident
1. Detect via integrity worker or alert.
2. Isolate affected memory tier (Redis/Postgres/vector).
3. Restore from latest backup.
4. Reconcile and validate memory graph.
5. Document incident and update runbook.

## Agent SLM Rollback
1. Detect regression or outage in agent SLM.
2. Roll back to previous SLM version or config.
3. Validate agent health and metrics.
4. Notify stakeholders and document root cause.

## Onboarding
1. Provision new tenant/namespace.
2. Generate and distribute credentials.
3. Validate access and run smoke tests.
4. Provide onboarding docs and support contacts.
