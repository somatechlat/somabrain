# Full-Power Recall Defaults

Date: 2025-11-06

This document explains SomaBrain's default recall behavior and how to tune or roll it back using environment variables.

## Summary

The recall API now runs in "full power" mode by default:

- Retrievers: `vector, wm, graph, lexical`
- Rerank: `auto` (prefers HRR → MMR → cosine based on availability)
- Session learning: enabled (`persist=true`), recording:
  - a per-query recall session memory
  - `retrieved_with` links from the session to each top candidate
  - cached candidates used for resilient retrieval

These defaults maximize relevance, diversity, and learning across calls while remaining strictly grounded in real backends.

## Environment Variables

Use these to override or roll back behavior without code changes.

- `SOMABRAIN_RECALL_FULL_POWER=1|0` (default 1)
  - Master switch for full-power defaults.
- `SOMABRAIN_RECALL_SIMPLE_DEFAULTS=1`
  - Forces conservative behavior: `rerank=cosine`, `persist=false`, `retrievers=vector,wm,graph`.
- `SOMABRAIN_RECALL_DEFAULT_RERANK=auto|mmr|hrr|cosine`
- `SOMABRAIN_RECALL_DEFAULT_PERSIST=1|0`
- `SOMABRAIN_RECALL_DEFAULT_RETRIEVERS=vector,wm,graph,lexical`

Notes:
- When `rerank=auto` and the quantum layer is available (`use_hrr=true`), the pipeline uses HRR reranking; otherwise it falls back to MMR, then cosine.
- The unified retrieval pipeline always performs rank fusion across retrievers and pins exact id/key/coord hits at the top.

## Operational Impact

- Session learning writes `recall session` items and `retrieved_with` links to the real memory backend. These are guarded by the circuit breaker and OPA/JWT.
- Graph retrieval leverages learned links to improve future recall quality.
- Metrics reflect candidate counts, fusion, and rerank method; use `/metrics` to monitor retrieval behavior.

## Client Compatibility

- Existing clients that omit `retrievers`, `rerank`, or `persist` now inherit the full-power defaults.
- To revert at the client level, specify explicit values in your request or set environment flags at the server.

## Best Practices

- Keep `SOMABRAIN_RECALL_FULL_POWER=1` in production for better quality and learning.
- Set `use_hrr=true` to unlock HRR reranking under `rerank=auto`.
- For controlled experiments or cost-sensitive paths, use `SOMABRAIN_RECALL_SIMPLE_DEFAULTS=1` or override the specific default flags.
