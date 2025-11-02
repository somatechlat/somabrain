## Services and Ports

This matrix summarizes the Docker Compose services and their default container ports, along with the typical host ports used by the helper scripts.

Host ports
- scripts/dev_up.sh: picks free ports automatically (API starts at 9696 and increments if busy). Writes .env and ports.json.
- scripts/dev_up_9999.sh: uses a stable API host port 9999 and fixed 3010x/30108 host ports for infra. Writes .env and ports.9999.json.

| Service | Container Port | Default Host Port (9999 stack) |
|---|---:|---:|
| somabrain_app (API) | 9696 | 9999 |
| somabrain_redis | 6379 | 30100 |
| somabrain_kafka (EXTERNAL listener) | 9094 | 30102 |
| somabrain_kafka_exporter | 9308 | 30103 |
| somabrain_opa | 8181 | 30104 |
| somabrain_prometheus | 9090 | 30105 |
| somabrain_postgres | 5432 | 30106 |
| somabrain_postgres_exporter | 9187 | 30107 |
| somabrain_schema_registry | 8081 | 30108 |

Notes
- The Kafka INTERNAL listener remains on 9092 inside the Docker network (somabrain_kafka:9092); host-side clients should use the EXTERNAL listener on the mapped host port.
- On Linux (Docker Engine), host.docker.internal may not resolve inside containers by default; see the deployment guide for alternatives.
- The API is considered ready when memory_ok and embedder_ok are true in GET /health (with strict flags enabled).
  
