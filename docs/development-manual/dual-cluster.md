# Running two local clusters (9696 and 9999)

This guide shows how to run a second SOMABRAIN Docker cluster in parallel to your default local stack. The secondary cluster exposes the API on port 9999 and remaps other host ports to avoid conflicts.

## What’s included

- scripts/dev_up_9999.sh: helper to start the 9999 stack and generate ports.9999.json.
- Single canonical docker-compose.yml and a generated `.env` drive both stacks.

## Start the secondary cluster

```bash
# From the repo root
./scripts/dev_up_9999.sh --with-monitoring
```

- API health: http://localhost:9999/health
- Ports summary: `ports.9999.json`

## Bring it down

```bash
docker compose -p somabrain-9999 -f docker-compose.yml --env-file .env down
```

## Notes

- The secondary cluster is fully isolated via a unique compose project name `somabrain-9999`, a distinct network, and separate volumes.
- In-cluster service DNS names (e.g., `somabrain_redis`) remain the same inside each project; they do not cross-talk.
- Host ports are remapped to the 30100+ range to avoid the defaults used by the 9696 stack.
