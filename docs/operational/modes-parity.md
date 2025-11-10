# SomaBrain Modes and Parity (Canonical)

This document defines the single source of truth for runtime modes and their
operational guarantees. It exists to ensure local runs match production behavior.

## Mode Taxonomy

- `SOMABRAIN_MODE=full-local` (canonical local mode)
  - Avro-only, fail-fast producers/consumers; no JSON fallbacks.
  - All core services enabled: integrator, reward ingestion, learner/calibration,
    drift detection/rollback, memory, segmentation (if required).
  - Same Kafka topics/schemas and metrics as prod; local Kafka deployment.
  - Health and metrics endpoints available for ops; bound to localhost when possible.
- `SOMABRAIN_MODE=prod`
  - Identical semantics to `full-local`; cloud infra and secrets differ.
- `SOMABRAIN_MODE=ci`
  - Strict semantics; services may run pared-down, but no protocol relaxations.

## Single Source of Truth (SSOT)

A central resolver maps `SOMABRAIN_MODE` -> feature matrix:

- enable_integrator, enable_reward_ingest, enable_learner, enable_drift,
  enable_segmentation, enable_metrics, enable_health_http, opa_gate, etc.
- strictness: avro_required=true, producer_fail_fast=true, no_fallbacks=true.

Services consume this matrix instead of scattered `ENABLE_*` flags.

## Endpoint Policy

- Keep metrics and health endpoints as part of parity; bind to localhost in `full-local`.
- Drift HTTP introspection has been removed. Use Prometheus and `scripts/drift_dump.py`.
- Optional debug endpoints (like `/tau`) are gated by mode or disabled.

## Docker Parity Profile

A single compose profile brings up the entire stack locally with `SOMABRAIN_MODE=full-local`.
This is the only supported local run mode.

## Invariants

- Avro-only serialization in services and monitoring.
- Fail-fast Kafka for enabled features.
- No deprecated clients or JSON fallbacks.
- Mode assertions: `full-local` implies all core services enabled and strictness on.

## Migration Plan (Sprints)

1) Inventory flags and define mode taxonomy.
2) Implement SSOT resolver and wire services to consume it (keep legacy flags as temporary overrides with warnings).
3) Add docker compose profile and update docs/README.
4) Extend invariants for mode assertions; remove legacy flags after grace period.
5) Validate parity via end-to-end checklist.

## Validation Checklist

- Kafka topics exist; Avro schemas load; producers/consumers initialized.
- Integrator, learner, drift, reward services running.
- Temperature scaling and acceptance working; metrics emitted.
- Drift baselines persist; rollback events Avro-emitted; `drift_dump.py` prints baselines.
- Context builder enforces per-tenant entropy cap; integrator fusion entropy cap enforced.
- Health endpoints OK; Prometheus scraping; OTel configured.
