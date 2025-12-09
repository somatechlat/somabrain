# API Reference

This document provides a summary of the SomaBrain API endpoints.

## Core Memory Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Checks Redis, Postgres, Kafka, OPA, memory backend, embedder, and circuit breaker state. |
| `POST /memory/remember` | Store a memory with signals (importance, novelty, ttl), attachments, links, and policy tags. Returns coordinate, WM promotion status, and signal feedback. |
| `POST /memory/remember/batch` | Bulk memory ingestion with per-item success/failure tracking and signal feedback. |
| `POST /memory/recall` | Unified retrieval backed by the full retrieval pipeline (vector, wm, graph, lexical retrievers). Supports streaming, session pinning, and tiered memory. |
| `POST /memory/recall/stream` | Chunked recall for streaming large result sets. |
| `GET /memory/context/{session_id}` | Retrieve pinned recall session results. |
| `GET /memory/metrics` | Per-tenant memory metrics (WM items, circuit breaker state). |

## Context & Adaptation

| Endpoint | Description |
|----------|-------------|
| `POST /context/evaluate` | Builds a prompt, returns weighted memories, residual vector, and working-memory snapshot. |
| `POST /context/feedback` | Updates tenant-specific retrieval/utility weights; emits gain/bound metrics. |
| `GET /context/adaptation/state` | Inspect current weights, effective learning rate, configured gains, and bounds. |

## Planning & Actions

| Endpoint | Description |
|----------|-------------|
| `POST /plan/suggest` | Suggest a plan derived from the semantic graph around a task key. |
| `POST /act` | Execute an action/task and return step results with salience scoring. |
| `POST /delete` | Delete a memory at the given coordinate. |
| `POST /recall/delete` | Delete a memory by coordinate via the recall API. |

## Neuromodulation & Sleep

| Endpoint | Description |
|----------|-------------|
| `GET/POST /neuromodulators` | Read or set neuromodulator levels (dopamine, serotonin, noradrenaline, acetylcholine). |
| `POST /sleep/run` | Trigger NREM/REM consolidation cycles. |
| `GET /sleep/status` | Check sleep/consolidation status for current tenant. |
| `GET /sleep/status/all` | Admin view: list sleep status for all known tenants. |

## Admin & Operations

| Endpoint | Description |
|----------|-------------|
| `GET /admin/services` | List all cognitive services managed by Supervisor. |
| `GET /admin/services/{name}` | Get status of a specific service. |
| `POST /admin/services/{name}/start` | Start a cognitive service. |
| `POST /admin/services/{name}/stop` | Stop a cognitive service. |
| `POST /admin/services/{name}/restart` | Restart a cognitive service. |
| `GET /admin/outbox` | List transactional outbox events (pending/failed/sent) with tenant filtering. |
| `POST /admin/outbox/replay` | Mark failed outbox events for replay. |
| `GET /admin/features` | Get current feature flag status and overrides. |
| `POST /admin/features` | Update feature flag overrides (full-local mode only). |
| `POST /memory/admin/rebuild-ann` | Rebuild ANN indexes for tiered memory. |
