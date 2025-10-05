# Memory Recall Regression Test

This guide explains how to validate the real Somabrain deployment to ensure the
public API (port 9696) and SomaMemory service (port 9595) store and recall
persona records correctly.

## Overview

- **Live-only workflow** – there are no mocks or local simulators. All checks
  run against the genuine services exposed by your environment.
- **Regression test** – `tests/test_synthetic_memory_recall.py` writes a
  temporary persona through the REST API, fetches it back, verifies SomaMemory
  can recall it, and finally deletes the record.
- **SFM response shape** – HTTP recalls now return
  `{ "matches": [{ "payload": {...}, "score": <float>, "coord": "x,y,z" }, ...] }`.
  The client normalizes this into `RecallHit` objects (payload, score, coordinate)
  before the application layer consumes the results.
- **Bulk + scoreful endpoints** – the memory client first attempts to persist
  batches via `/store_bulk` and uses `/recall_with_scores` when present. Both
  fall back to the legacy `/store` and `/recall` endpoints if the deployment
  has not yet upgraded.
- **Graph maintenance** – new helpers wrap `/unlink` and `/prune` so tests can
  validate edge removal and degree trimming against the real service.
- **Skip guards** – helper utilities in
  `somabrain/testing/synthetic_memory.py` verify network availability and skip
  the test automatically if the stack is unreachable.

## Prerequisites

1. `sb-api` listening on `http://localhost:9696` (set `SOMA_API_URL` if using a
   different host).
2. SomaMemory HTTP service on `http://localhost:9595` (override with
   `SOMABRAIN_MEMORY_HTTP_ENDPOINT` if needed).
3. Redis reachable at `REDIS_HOST:REDIS_PORT` (defaults to `127.0.0.1:6379`).

If you are developing against a remote cluster, create the necessary
port-forwards before running the test.

## Running the regression test

```bash
pytest tests/test_synthetic_memory_recall.py
```

The test flow:

1. Confirm Redis and both HTTP services are reachable; otherwise pytest marks
   the scenario as skipped.
2. PUT a new persona with a unique identifier via the Somabrain API.
3. GET the persona and check the persisted payload matches the request.
4. POST a recall query to SomaMemory and assert the persona identifier appears
   in the returned memories.
5. DELETE the persona to leave no residue.

## Troubleshooting

- **Skip: Redis unavailable** – ensure `redis-cli -h <host> -p <port> ping`
  succeeds or update `REDIS_HOST`/`REDIS_PORT` in the environment.
- **Skip: API service unavailable** – port-forward `sb-api` or adjust
  `SOMA_API_URL` to point at a reachable instance.
- **Skip: Memory service unavailable** – port-forward `sb-memory-http` or set
  `SOMABRAIN_MEMORY_HTTP_ENDPOINT` appropriately.
- **HTTP 5xx responses** – inspect the respective service logs; the regression
  test surfaces the response body for quick diagnostics.
