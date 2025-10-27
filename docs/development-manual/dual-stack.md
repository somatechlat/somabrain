## Dual-stack local development (9696 + 9999)

This repo supports running two isolated Docker Compose stacks concurrently:

- Main stack (default project) exposes API on host 9696
- Branch/experimental stack exposes API on host 9999, fully isolated (distinct networks/volumes)

### Start the 9999 stack

Use the helper script to assign non-conflicting ports and bring up the branch stack:

- scripts/dev_up_9999.sh

What it does:
- Uses `-p somabrain-9999` to project-scope all resources (no container_name usage)
- Maps `9999:9696` for the API and remaps infra ports into the 30100+ range
- Writes `ports.9999.json` for quick discovery of host-mapped ports

### OPA policy for integrator

An example policy is provided at `ops/opa/policies/integrator.rego` with package `soma.policy.integrator`.
To enable integrator OPA gating in the 9999 stack, ensure env contains:

- `SOMABRAIN_OPA_URL=http://somabrain_opa:8181`
- `SOMABRAIN_OPA_POLICY=soma.policy.integrator`

The integrator will POST `{"input":{...}}` to `/v1/data/soma/policy/integrator` and expect a result of the form `{ "allow": bool, "leader": optional string }`.

### Isolation guarantees

- No `container_name` is used; networks and volumes are project-scoped
- Do not run `docker compose down` without specifying `-p somabrain-9999` to avoid touching the main stack

### Observability

- New metrics:
  - `somabrain_integrator_leader_entropy{tenant}`: entropy of domain weights [0..1]
  - `somabrain_outbox_event_e2e_seconds{topic}`: latency from outbox enqueue to DB apply
  - `somabrain_outbox_applier_applied_total{topic}` / `somabrain_outbox_applier_errors_total{topic}`

Scrape via the API `/metrics` endpoint in each stack.

### Kafka dual listeners (host + in-cluster)

The local Kafka broker runs with two named listeners to avoid host/container mismatches:

- INTERNAL listener: `somabrain_kafka:9092` for inter-broker and in-cluster clients (containers)
- EXTERNAL listener: `localhost:30102` mapped to the broker's `9094` for host clients (your laptop)

Key settings (from `.env`):

- `KAFKA_CFG_LISTENERS=INTERNAL://0.0.0.0:9092,EXTERNAL://0.0.0.0:9094,CONTROLLER://0.0.0.0:9093`
- `KAFKA_CFG_ADVERTISED_LISTENERS=INTERNAL://somabrain_kafka:9092,EXTERNAL://localhost:${KAFKA_BROKER_HOST_PORT}`
- `KAFKA_CFG_INTER_BROKER_LISTENER_NAME=INTERNAL`
- `KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,INTERNAL:PLAINTEXT,EXTERNAL:PLAINTEXT`

Use `SOMABRAIN_KAFKA_URL=kafka://127.0.0.1:30102` for host-side tools and keep container services on `kafka://somabrain_kafka:9092`.
