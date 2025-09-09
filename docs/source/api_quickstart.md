## Quickstart — remember & recall

These are minimal, canonical examples for the HTTP API. Adjust host/port as needed (the project commonly runs under uvicorn on port 8000).

Remember (store a memory)

- Endpoint: POST /remember
- Body: JSON matching the RememberRequest/MemoryPayload shapes (see `/openapi.json` for exact types).

Example curl (canonical):

```sh
curl -X POST http://127.0.0.1:8000/remember \
  -H "Content-Type: application/json" \
  -d '{
    "coord": null,
    "payload": {
      "task": "write docs",
      "importance": 1,
      "memory_type": "episodic",
      "timestamp": 1693750000.123,
      "who": "agent_zero",
      "did": "tested",
      "what": "remember endpoint",
      "where": "terminal",
      "when": "2025-09-03T20:35:00Z",
      "why": "API test"
    }
  }'
```

Recall (search memories)

- Endpoint: POST /recall
- Body: `RecallRequest` { query: string, top_k?: int, universe?: string }

Example curl (canonical):

```sh
curl -X POST http://127.0.0.1:8000/recall \
  -H "Content-Type: application/json" \
  -d '{"query":"remember endpoint","top_k":5}'
```

Notes
- Use `X-Tenant-ID` to scope tenant operations (default `public`).
- If the server is configured with an API token, add `Authorization: Bearer <token>`.
- For programmatic clients prefer numeric `timestamp` (epoch seconds) and ISO `when` strings.

See `docs/source/api.md` for detailed per-endpoint notes and `openapi.json` for exact types.
