> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# Memory Recall Regression Test

This guide explains how to validate the real Somabrain deployment to ensure the
public API (port 9696) stores and recalls persona records correctly.

## Overview

- **Live-only workflow** – there are no mocks or local simulators. All checks
  run against the genuine services exposed by your environment.
- **Regression test** – `tests/test_synthetic_memory_recall.py` writes a
  temporary persona through the REST API, fetches it back, verifies recall
  responses, and finally deletes the record.
- **SFM response shapes** – HTTP recalls now return
  `{"matches": [...]}` or `{"results": [...]}` depending on the endpoint
  (`/recall_with_scores`, `/hybrid_recall_with_scores`, `/keyword_search`). The memory
  client normalizes each shape into `RecallHit` objects (payload, score, coordinate)
  before the application layer consumes the results.
- **Bulk + scoreful endpoints** – the memory client first attempts to persist
  batches via `/store_bulk` and uses `/recall_with_scores` when present. Both
  fall back to the legacy `/store` and `/recall` endpoints if the deployment
  has not yet upgraded.
- **Aggregated recall** – `MemoryClient.recall()` fan-outs to vector (`/recall_with_scores`),
  hybrid (`/hybrid_recall_with_scores`), and lexical (`/keyword_search`) endpoints, merges
  the results, deduplicates them, and applies the same lexical/quality weighting that the
  application stack expects. Regression runs should therefore see keyword-only memories surface
  even when the vector result set is empty.
- **Graph maintenance** – new helpers wrap `/unlink` and `/prune` so tests can
  validate edge removal and degree trimming against the real service.
- **Skip guards** – helper utilities in
  `somabrain/testing/synthetic_memory.py` verify network availability and skip
  the test automatically if the stack is unreachable.

## Prerequisites

1. `sb-api` listening on `http://localhost:9696` (set `SOMA_API_URL` if using a
   different host).
2. Redis reachable at `REDIS_HOST:REDIS_PORT` (defaults to `127.0.0.1:6379`).

If you are developing against a remote cluster, create the necessary
port-forwards before running the test.

## Running the regression test

```bash
pytest tests/test_synthetic_memory_recall.py
```

The test flow:

1. Confirm Redis and the API endpoint are reachable; otherwise pytest marks
   the scenario as skipped.
2. PUT a new persona with a unique identifier via the Somabrain API.
3. GET the persona and check the persisted payload matches the request.
4. POST a recall query to Somabrain and assert the persona identifier appears
   in the returned memories.
5. DELETE the persona to leave no residue.

## Troubleshooting

- **Skip: Redis unavailable** – ensure `redis-cli -h <host> -p <port> ping`
  succeeds or update `REDIS_HOST`/`REDIS_PORT` in the environment.
- **Skip: API service unavailable** – port-forward `sb-api` or adjust
  `SOMA_API_URL` to point at a reachable instance.
- **HTTP 5xx responses** – inspect the respective service logs; the regression
  test surfaces the response body for quick diagnostics.
