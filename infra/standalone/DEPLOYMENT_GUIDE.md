# SomaBrain Standalone Deployment Guide

Last updated: 2026-04-01

This guide reflects the current `infra/standalone/docker-compose.yml` stack.
The standalone profile is Vault-first, single-tenant, and still depends on an
external memory endpoint unless you override `SOMABRAIN_MEMORY_HTTP_ENDPOINT`.

## What the stack actually contains

The compose file currently defines 16 default services (17 with the `dev` profile):

- Always-on infrastructure and app services: Redis, Kafka, Kafka exporter,
  Schema Registry, OPA, Prometheus, Jaeger, Postgres, Vault, Vault init,
  Postgres exporter, API app, `cog`, outbox publisher, MinIO, integrator triplet.
- One optional one-shot job under the `dev` profile:
  `somabrain_standalone_db_migrate`.

Important architecture notes:

- Standalone mode strips AAAS apps and middleware in
  `somabrain.settings.standalone`.
- Secrets are seeded into Vault by `somabrain_standalone_vault_init`, then read
  back by the Python settings bootstrap through `vault_client.py`.
- The external memory service is not part of this compose file. By default the
  containers call `http://host.docker.internal:10101`.

## Required environment values

Start from [`infra/standalone/.env.example`](./.env.example) and set at least:

- `SOMABRAIN_VAULT_TOKEN`
- `POSTGRES_PASSWORD`
- `SOMABRAIN_JWT_SECRET`
- `SOMABRAIN_MEMORY_HTTP_TOKEN`
- `SUPERVISOR_HTTP_PASS`

Optional but commonly overridden:

- `SOMABRAIN_MEMORY_HTTP_ENDPOINT` if your external memory service is not on
  `host.docker.internal:10101`
- `SOMABRAIN_WORKERS`
- `SOMA_DEPLOY_MODE` / `SOMABRAIN_MODE`

## Bring the stack up

```bash
cd /path/to/somabrain
cp infra/standalone/.env.example infra/standalone/.env

docker compose \
  -f infra/standalone/docker-compose.yml \
  --env-file infra/standalone/.env \
  up -d
```

If you also want the one-shot migration container:

```bash
docker compose \
  -f infra/standalone/docker-compose.yml \
  --env-file infra/standalone/.env \
  --profile dev \
  up -d somabrain_standalone_db_migrate
```

## Health checks

Verify the control plane first:

```bash
docker compose -f infra/standalone/docker-compose.yml ps
curl -s http://localhost:30200/v1/sys/health | jq
curl -s http://localhost:30101/health | jq
```

Useful service endpoints exposed to the host:

| Service | Host port | Notes |
|---------|-----------|-------|
| API | `30101` | Main Django/Ninja API |
| Kafka | `30102` | External listener |
| OPA | `30104` | Policy API |
| Prometheus | `30105` | Metrics UI |
| Postgres | `30106` | Database |
| Schema Registry | `30108` | Kafka schemas |
| MinIO | `30109` | Object storage |
| MinIO console | `30110` | Storage UI |
| Jaeger UI | `30111` | Tracing UI |
| Vault | `30200` | Secret management |
| Integrator health | `30115` | Integrator worker probe |
| Segmentation health | `30116` | Segmentation worker probe |

## Secrets flow

The actual bootstrap sequence is:

1. `somabrain_standalone_vault` starts in dev mode on port `30200`.
2. `somabrain_standalone_vault_init` mounts a KV-v2 engine at `somabrain/`.
3. `vault_init` writes:
   `somabrain/database`, `somabrain/redis`, `somabrain/auth`, and
   `somabrain/runtime`.
4. App containers start with `VAULT_ADDR` and `VAULT_TOKEN` only.
5. `somabrain.settings.django_core` and `somabrain.settings.infra` fetch the
   runtime secrets and derive DSNs/tokens inside the process.

## Troubleshooting

`VaultNotConfigured`

- Check `docker logs somabrain_standalone_vault`
- Check `docker logs somabrain_standalone_vault_init`
- Verify `SOMABRAIN_VAULT_TOKEN` matches the value in `.env`

API healthy but memory-backed routes fail

- Confirm the external memory service is reachable from containers
- If needed, override `SOMABRAIN_MEMORY_HTTP_ENDPOINT`
- Verify the token stored in Vault under `somabrain/runtime.memory_http_token`

Database connection failures

- Confirm Postgres is healthy on `30106`
- Inspect the secret that `vault_init` wrote:

```bash
docker exec somabrain_standalone_vault vault kv get somabrain/database
```

## Verification snippets

```bash
docker exec somabrain_standalone_app python -c \
  "from somabrain.core.rust_bridge import is_rust_available; print(is_rust_available())"

docker exec somabrain_standalone_app python -c \
  "from somabrain.runtime.manager import initialize_runtime; print(initialize_runtime())"
```
