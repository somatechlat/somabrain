# Backup and Restore Runbook

## Purpose
Provide step‑by‑step instructions for backing up and restoring the SomaBrain PostgreSQL database and Kafka topics in a production environment.

## Prerequisites
- Access to the Kubernetes cluster where SomaBrain is deployed.
- `kubectl` configured for the target cluster.
- `pg_dump` and `pg_restore` available locally (or use a container image with these tools).
- Access to the Kafka broker (`somabrain_kafka`) and the `kafka-topics.sh` utility.

## Backup PostgreSQL
1. Identify the PostgreSQL pod:
   ```bash
   POD=$(kubectl get pods -l app=postgres -o jsonpath="{.items[0].metadata.name}")
   ```
2. Execute a dump inside the pod and copy it locally:
   ```bash
   kubectl exec $POD -- pg_dump -U $POSTGRES_USER $POSTGRES_DB > somabrain_backup_$(date +%Y%m%d).sql
   ```
3. Store the dump in a secure location (S3, encrypted archive, etc.).

## Restore PostgreSQL
1. Ensure the target database is empty or the existing data is no longer needed.
2. Copy the backup file to the pod (or stream it directly):
   ```bash
   cat somabrain_backup_20240101.sql | kubectl exec -i $POD -- psql -U $POSTGRES_USER $POSTGRES_DB
   ```
3. Verify the restore:
   ```bash
   kubectl exec $POD -- psql -U $POSTGRES_USER -c "SELECT count(*) FROM somabrain.memory;"
   ```

## Backup Kafka Topics
1. List topics to back up:
   ```bash
   kubectl exec -it $(kubectl get pod -l app=kafka -o jsonpath="{.items[0].metadata.name}") -- kafka-topics.sh --bootstrap-server localhost:9092 --list
   ```
2. Use `kafka-exporter` or `kafka-mirror-maker` to copy topic data to a backup cluster, or use `kafka-console-consumer` to export messages to files:
   ```bash
   kubectl exec -it $KAFKA_POD -- kafka-console-consumer.sh \
       --bootstrap-server localhost:9092 \
       --topic my_topic \
       --from-beginning > my_topic_$(date +%Y%m%d).json
   ```
3. Store the exported files securely.

## Restore Kafka Topics
1. Re‑create the topic if needed:
   ```bash
   kubectl exec -it $KAFKA_POD -- kafka-topics.sh \
       --create --topic my_topic \
       --partitions 3 --replication-factor 2 \
       --bootstrap-server localhost:9092
   ```
2. Produce the saved messages back into the topic:
   ```bash
   cat my_topic_20240101.json | \
     kubectl exec -i $KAFKA_POD -- kafka-console-producer.sh \
       --bootstrap-server localhost:9092 \
       --topic my_topic
   ```
3. Verify the message count matches the original backup.

---
*This runbook is intended for operators with cluster admin privileges. Adjust namespace selectors and resource names as appropriate for your deployment.*
