# RFC-0001: Centralized Modes for SomaBrain

- Status: Proposed
- Authors: Core Platform
- Created: 2025-10-19
- Target branch: V3.0_regulariazation

## Summary

Introduce a single authoritative mode switch (SOMABRAIN_MODE ∈ {dev, staging, prod}) that drives a unified set of derived flags consumed across the entire system. Retire ambiguous flags and remove duplicated env checks. The goal is to eliminate drift between services and ensure consistent behavior without mocks while allowing safe relaxations in development.

## Motivation

- Current flags (e.g., SOMABRAIN_DISABLE_AUTH, SOMABRAIN_FORCE_FULL_STACK) are used inconsistently.
- Memstore and API auth weren’t aligned, causing blocked retrieval in dev.
- We need reproducible, real-service runs (no mocks), with controlled relaxations only in dev.

## Non-goals

- Changing core algorithms/behavior across modes. Modes only gate policy/auth/rates/caps, not algorithmic logic.
- Introducing new third-party dependencies.

## Modes and derived flags

Single source: SOMABRAIN_MODE in process env; resolved centrally into a config object used everywhere.

Derived flags (representative):
- api_auth_enabled (bool)
- reset_enabled (bool)
- request_rate_limits (struct)
- memstore_auth_required (bool)
- memstore_endpoint (str)
- memstore_token_source (str)
- opa_policy_bundle (enum: allow-dev|staging|prod)
- log_level (str)
- metrics_sampling (struct)
- safety_caps (struct: top_k_max, wm_cap, lr_bounds)

Behavior by mode (summary):
- DEV: Real services; policy relaxations; dev token for memstore (or local proxy); OPA allow-dev; generous-but-safe caps; verbose logs.
- STAGING: Auth enforced; staging tokens; real OPA policies; realistic rates/caps; sandbox tenants only.
- PROD: Strict auth/policy/quotas; conservative caps; full audit/SLO; no dev overrides.

## Deprecations

- SOMABRAIN_FORCE_FULL_STACK: remove. Use require_external_backends only.
- SOMABRAIN_DISABLE_AUTH: no longer user-controlled; becomes a derived flag from mode.
- Legacy memstore API fallbacks (/search vector): remove; standardize on /memories and /memories/search. Keep network fallback host.docker.internal → 127.0.0.1.
- Scattered safety caps: consolidate into central config.

## Affected components

- API: somabrain/api/*.py
- Learning: somabrain/learning/adaptation.py
- Context: somabrain/context/builder.py
- Memory client: somabrain/memory_client.py (single gateway)
- Policy/Auth hub: services/sah/__init__.py and ops/opa/policies/*
- Workers: somabrain/workers/*
- Benchmarks: benchmarks/*.py
- Deploy/Infra: docker-compose.yml, infra/helm/charts/**
- Observability: observability/*, ops/prometheus/*, grafana_dashboard.json

## Rollout plan

- Sprint 0 (this RFC): agree on modes, derived flags, deprecations, and acceptance criteria.
- Sprint 1: Central config in common/config/settings.py; startup self-check logs.
- Sprint 2: API gating by mode (auth/reset/rate); audits.
- Sprint 3: Memstore + OPA selection by mode; remove legacy adapter fallbacks.
- Sprint 4: Workers + benchmarks read central flags; no mocks.
- Sprint 5: Compose/Helm profiles; secrets wiring; remove ambiguous envs.
- Sprint 6: Validation suite (health, auth, memstore, 200-iter learning).
- Sprint 7: Cleanup + guardrails (remove deprecated flags; CI policy checks; docs).

## Acceptance criteria

- DEV: 200-iteration benchmark returns non-zero retrieval_count; target rank tracked; memstore auth working with dev token.
- STAGING: JWT/OPA enforced; memstore token required; 200-iteration sandbox run respects limits.
- PROD: Strict controls; smoke only; no dev overrides present.

## Risks and mitigations

- Drift between services → central config; startup self-check summaries.
- Secret leakage → dev tokens local only; staging/prod via secret managers.
- Networking ambiguity → document host.docker.internal vs 127.0.0.1; add health preflights.

## Backwards compatibility

- Provide deprecation warnings for removed flags for one minor version window.
- Map legacy flags to mode-derived equivalents when possible.
