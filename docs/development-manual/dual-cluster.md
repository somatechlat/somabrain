# Running two local clusters (9696 and 9999)

This guide shows how to run a second SOMABRAIN Docker cluster in parallel to your default local stack. The secondary cluster exposes the API on port 9999 and remaps other host ports to avoid conflicts.

## What’s included

- docker-compose.9999.yml: compose override with unique project name, network, volumes, and container names.
- .env.9999.local: environment file for the 9999 stack.
- scripts/dev_up_9999.sh: helper to start the 9999 stack and generate ports.9999.json.

## Start the secondary cluster

```bash
# From the repo root
./scripts/dev_up_9999.sh
```

- API health: http://localhost:9999/health
- Ports summary: `ports.9999.json`

## Bring it down

```bash
docker compose -p somabrain-9999 -f docker-compose.yml -f docker-compose.9999.yml --env-file .env.9999.local down
```

## Notes

- The secondary cluster is fully isolated via a unique compose project name `somabrain-9999`, a distinct network, and separate volumes.
- In-cluster service DNS names (e.g., `somabrain_redis`) remain the same inside each project; they do not cross-talk.
- Host ports are remapped to the 30100+ range to avoid the defaults used by the 9696 stack.
