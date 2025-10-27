# Quick Start Tutorial

**Purpose** Walk through a minimal “remember → recall” loop against a live SomaBrain instance.

**Audience** First-time users who already have the stack running locally.

**Prerequisites**
- Followed the [Installation Guide](installation.md) and confirmed `/health` returns HTTP 200.
- A memory backend listening on port 9595.
  - For host runs (uvicorn on your machine): `http://localhost:9595`.
  - For Docker containers (macOS/Windows): `http://host.docker.internal:9595`.
  - Verify wiring at `GET /diagnostics` and check `memory_endpoint`.
- Authentication disabled (`SOMABRAIN_DISABLE_AUTH=1`) or a valid bearer token. If auth is enabled, add `-H "Authorization: Bearer <token>"` to the examples.

---

## 1. Store a Memory

`/remember` accepts either the legacy payload shape (`{"task": ..., "content": ...}`) or the explicit schema with a `payload` object. The example below uses the explicit schema defined in `somabrain/schemas.py::RememberRequest`.

```bash
curl -sS http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -d '{
        "payload": {
          "task": "geography.fact",
          "content": "Paris is the capital of France.",
          "memory_type": "episodic",
          "importance": 0.9,
          "timestamp": "2024-01-10T10:00:00Z"
        }
      }' | jq
```

Expected response (field names come directly from `RememberResponse`):

```json
{
  "ok": true,
  "success": true,
  "namespace": "somabrain_ns:public",
  "trace_id": "140351384443504",
  "deadline_ms": null,
  "idempotency_key": null,
  "breaker_open": null,
  "queued": null
}
```

If `breaker_open`/`queued` are `true`, the API could not reach the memory service. Either start the backend or set `SOMABRAIN_REQUIRE_MEMORY=0` while testing.

---

## 2. Recall the Memory

`/recall` returns working-memory hits (`wm`) and long-term candidates (`memory`). The legacy `results` list mirrors the `memory` field for backward compatibility.

```bash
curl -sS http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{
        "query": "capital of France",
        "top_k": 5
      }' | jq '.results[:1]'
```

Example output:

```json
[
  {
    "task": "geography.fact",
    "content": "Paris is the capital of France.",
    "memory_type": "episodic",
    "importance": 0.9,
    "score": 0.86,
    "_source": "ltm",
    "_wm_hit": false
  }
]
```

Scores come from `somabrain.scoring.UnifiedScorer` (combination of cosine similarity, FD projection, and recency decay). If the array is empty, confirm the memory backend persisted the write.

---

## 3. (Optional) Capture Feedback

Close the loop by submitting user feedback, which drives the live adaptation engine (`somabrain/learning/adaptation.py`):

```bash
curl -sS http://localhost:9696/context/feedback \
  -H "Content-Type: application/json" \
  -d '{
        "session_id": "demo-session",
        "query": "capital of France",
        "prompt": "Summarise the capital of France.",
        "response_text": "Paris is the capital of France.",
        "utility": 0.9,
        "reward": 0.9
      }' | jq
```

Successful responses contain:

```json
{
  "accepted": true,
  "adaptation_applied": true
}
```

The retrieval and utility weights are now updated and persisted to Redis. Inspect `/context/adaptation/state` to view the new values.

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `503 memory backend unavailable` when calling `/remember` | HTTP memory service not reachable | Start the backend on port 9595 or disable the requirement for dev testing |
| `/recall` returns empty lists | Write queued or memory backend empty | Check `/remember` response flags and the memory service logs |
| `401 missing bearer token` | Auth enabled | Set `SOMABRAIN_DISABLE_AUTH=1` for local testing or provide the correct API token |
| High latency (>1 s) | Kafka/Redis not ready | Wait for health probes, then retry |
| `/healthz` shows `"memory_ok": false` in Docker | Using `127.0.0.1` inside the container | Set `SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://host.docker.internal:9595` and verify via `GET /diagnostics` |

If problems persist, consult the [FAQ](faq.md) and the [Technical Manual](../technical-manual/troubleshooting.md) for deeper diagnostics.
