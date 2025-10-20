# SomaBrain — Project Progress Log

Purpose
- A living, lightweight log to track milestones, decisions, and next steps.

Status Summary
- Core scaffolding complete: FastAPI service, WM, salience, stub predictor (Cerebellum alias), memory client integration.
- Local memory mode validated; example quickstart runs.
- Architecture (biology + HRR) documented; roadmap set.
- HRR QuantumLayer implemented (feature-flagged); HRR cleanup signal exposed in `/recall` behind config; metrics added.
- Reflection v2 implemented: episodic clustering + semantic summaries; configurable thresholds.

Milestones
- [x] Integrate `somafractalmemory` locally (editable install)
- [x] Fix pyproject TOML issue for editable install
- [x] Add FastAPI endpoints: /act, /recall, /remember, /reflect, /personality, /health, /metrics
- [x] Implement WM + deterministic embeddings (256‑D)
- [x] Implement salience (novelty + error) and stub predictor
- [x] Add Prometheus metrics middleware and counters
- [x] Write SomaBrain summary and Architecture docs
- [x] Add multi-tenancy: per-tenant WM, namespace mapping, basic rate limiter, short-TTL recall cache
- [x] Add auth (optional bearer token) and per-tenant daily write quotas
 - [x] Reflection MVP: summarize recent episodics from tenant WM into semantic memory; link to sources when possible
 - [x] HRR cleanup signal + metrics in `/recall` when enabled
 - [x] Reflection v2: clustering episodics and writing semantic summaries

Next Up
- [ ] HRR influence on ranking/salience (feature-flagged re-ranking)
- [ ] Graph reasoning: k‑hop queries via memory graph; Hebbian edge updates
- [ ] Personality persistence and influence in /act planning
- [ ] Migration endpoints: /migrate/export, /migrate/import (manifest + JSONL)
- [ ] Predictor providers (LLM/ML) with latency budgets + fallbacks
- [ ] Security: API tokens required mode and input normalization in ThalamusRouter

Decisions
- Default memory backend: local (in‑proc) for dev; HTTP for prod — configurable
- Per‑process WM for now; document stickiness; revisit shared WM if needed
- Deterministic embeddings in MVP; HRR path as next milestone for superposition

Risks / Watchlist
- Salience calibration across tasks/domains — add auto‑tune hooks
- Predictor dependency (LLM latency) — degrade to novelty‑only; set budgets
- Schema/versioning — introduce version headers and migration early

Notes
- Keep this file updated after significant changes.
- Include brief rationale for scope changes or major design decisions.
