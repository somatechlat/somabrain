# Fallback Audit — Messaging & Serialization

Date: 2025-11-08

This audit enumerates all fallback patterns discovered in the repository (messaging
client, serialization, optional import fallbacks), classifies their risk, and
provides prioritized remediation recommendations. No code changes are included in
this report — it is an inventory and plan to act on.

## Scope & Method
- Searched the codebase for optional imports, try/except import patterns, and
  environment-driven fallbacks (e.g., Avro → JSON). Focused on runtime services
  under `somabrain/` and `somabrain/services/`, helper scripts, CI, and
  configuration.
- Keywords: `confluent_kafka`, `from kafka import`, `load_schema`, `AvroSerde`,
  `*_FORCE_JSON`, `try: ... except Exception: ...` used to drop optional deps.

## Executive Summary
- The repository contains layered fallbacks in three main areas:
  1. Messaging libraries: `confluent-kafka` vs `kafka-python` (aka `kafka`).
  2. Serialization: Avro (via `libs.kafka_cog`) vs JSON (with `*_FORCE_JSON` toggles).
  3. Optional runtime features (metrics, schema loader, OPA, memory clients) that
     are imported under try/except and set to None if missing.
- Several core services (notably `learner_online`) mix client libraries or accept
  degraded fallback modes. This caused prior outages (kafka-python timeouts) and
  makes production behaviour brittle and environment-dependent.

## Key Findings (by category)

### 1) Messaging client fallbacks (confluent vs kafka-python)
Files and patterns:
- `somabrain/services/learner_online.py`
  - Imports both `from kafka import KafkaConsumer, KafkaProducer` and
    `from confluent_kafka import Producer as CfProducer` and branches at runtime.
  - Producer selection: prefers confluent, falls back to kafka-python; consumer
    uses kafka-python. Mixed APIs and semantics in the same process.
- `somabrain/services/reward_producer.py`
  - Attempts confluent producer import and kafka-python fallback.
- `somabrain/services/teach_feedback_processor.py`
  - Both clients referenced; runtime chooses based on availability.
- `somabrain/workers/outbox_publisher.py`
  - Conditional import of confluent producer; fallback path exists.
- Other files using `kafka-python` directly (producers/consumers):
  - `somabrain/services/segmentation_service.py`
  - `somabrain/services/integrator_hub.py`
  - `somabrain/services/orchestrator_service.py`
  - `somabrain/workers/wm_updates_cache.py`
  - `somabrain/cog/producer.py`, `somabrain/audit/producer.py`

Impact and risk:
- Mixed client APIs change delivery semantics (acks, retries, flush behavior).
- Observed production issue: `kafka-python` timeouts caused config updates to fail
  while confluent-based manual publish succeeded.
- CI sometimes only installed `kafka-python`, allowing tests to pass while
  production required `confluent-kafka` — hidden mismatch.

### 2) Serialization fallbacks (Avro ↔ JSON)
Files and patterns:
- `libs.kafka_cog.avro_schemas` and `libs.kafka_cog.serde` used as optional
  imports across services. Common pattern: try import; on Exception set to `None`.
- Services with fallback-to-JSON or `*_FORCE_JSON` envs:
  - `somabrain/services/learner_online.py` — `LEARNER_FORCE_JSON`
  - `somabrain/services/reward_producer.py` — `REWARD_FORCE_JSON`
  - `somabrain/services/segmentation_service.py`, `integrator_hub.py`,
    `wm_updates_cache.py`, `cog/producer.py` — similar patterns for Avro serde.

Impact and risk:
- Avro is the canonical schema format for topics in the roadmap. Silent fallback
  to JSON changes runtime message format and may break consumers expecting Avro.
- Force-JSON flags are useful for development but should be explicitly gated in
  production mode — currently they can be toggled and cause silent format drift.

### 3) Optional dependency fallbacks (metrics, OPA, memory clients)
Files and patterns:
- `somabrain/metrics.py` imports may fail and services continue with `metrics=None`.
- OPA, memory clients, and other infra (Redis, DB optional wrappers) are wrapped
  in try/except and can be missing without startup failure.

Impact and risk:
- Silent degradation of observability or authorization may occur without clear
  startup failure. This obscures root cause during incidents.

### 4) Scripts & CI
- Several helper scripts and smoke tests accept either client (confluent or
  kafka-python) and are used in local validation: `scripts/e2e_reward_smoke.py`,
  `scripts/e2e_teach_feedback_smoke.py`, `scripts/kafka_smoke_test.py`.
- `.github/workflows/ci.yml` installs `kafka-python` in some jobs (observed via
  install lines), which can cause CI to miss issues present when `confluent-kafka`
  is required in production.

## Risk Classification (prioritized)
- High risk (core service reliability): mixed Kafka clients in `learner_online.py`.
- High risk (deployment mismatch): CI and images not guaranteeing `confluent-kafka`.
- Medium risk: Avro-to-JSON silent fallbacks across multiple services.
- Low-to-medium risk: silent disabling of non-critical dependencies (metrics, OPA)
  — acceptable for some dev contexts but should be explicit.

## Recommendations (practical & prioritized)

1. Enforce a single Kafka client for production runtimes — prefer `confluent-kafka`.
   - Remove runtime fallback branches in core services and fail fast with an
     explicit error message if `confluent-kafka` is missing.
   - Rationale: librdkafka-backed client has stronger delivery semantics and an
     admin API for topic creation.

2. Make Avro usage explicit and fail-fast in production mode.
   - If Avro schemas and/or schema-registry are required in production, load
     the necessary schemas at startup and error if missing. Keep `*_FORCE_JSON`
     flags for local dev only and clearly annotate them in `env.example`.

3. Replace silent try/except import patterns for critical dependencies with
   explicit checks and gating via feature flags. Log clear startup messages
   about missing optional components and whether the service is running in
   degraded mode.

4. Update CI and base images to include `confluent-kafka` (and librdkafka) and
   change CI smoke jobs to exercise the confluent client path.

5. Leave developer-oriented scripts tolerant (they can keep fallbacks), but
   mark them `dev/` and avoid using them as production acceptance tests.

6. Create a small integration smoke test that uses `confluent-kafka` to validate
   the full reward→learner→config_update→integrator flow and include it in CI.

## Suggested Remediation Plan (phased)
- Phase 0 (Docs/CI): Update `docs/technical-manual/learning-loop.md` and
  `config/env.example` to state `confluent-kafka` as required for prod and mark
  `*_FORCE_JSON` flags as dev-only. Update CI job(s) to install `confluent-kafka`.
- Phase 1 (High priority): Change `somabrain/services/learner_online.py` to
  require `confluent-kafka` for both produce and consume (or at minimum require
  `confluent` for produce and ensure consumer semantics are compatible). Run
  smoke tests and validate `/tau` endpoint updates.
- Phase 2: Convert core producers/consumers in `reward_producer.py`,
  `segmentation_service.py`, `integrator_hub.py`, `cog/producer.py`,
  `outbox_publisher.py` to `confluent-kafka` APIs.
- Phase 3: Add startup checks for Avro schemas and optional hardening.

## Testing Checklist (post-change)
- Build image that contains `librdkafka` and `confluent-kafka` Python wheel.
- Run stack and execute an end-to-end smoke: POST reward → observe learner
  logs → consume `cog.config.updates` → check `/tau` endpoint change.
- Run CI job updated to use confluent; ensure tests pass and fail when client
  missing.

## Appendix — Notable files & quick references
- `somabrain/services/learner_online.py`
  - Dual imports: `from kafka import KafkaConsumer, KafkaProducer` and
    `from confluent_kafka import Producer as CfProducer`.
  - Runtime behavior: prefer confluent producer, fallback to kafka-python; uses
    kafka-python consumer.
- `somabrain/services/reward_producer.py` — Producer fallback logic; `REWARD_FORCE_JSON` toggle.
- `somabrain/services/teach_feedback_processor.py` — Uses both clients and Avro
  serde conditional loading.
- `somabrain/workers/outbox_publisher.py` — conditional confluent producer import.
- `somabrain/services/segmentation_service.py`, `integrator_hub.py`,
  `orchestrator_service.py`, `wm_updates_cache.py`, `cog/producer.py`,
  `audit/producer.py` — rely on `kafka-python` imports; conditional Avro serde.
- `scripts/` — many smoke scripts accept either client and may install
  `kafka-python` in CI flows.

## Closing notes
This report is intended as an operational audit and a prioritized plan. The most
urgent single change is to remove the kafka-client fallback in `learner_online.py`
and ensure the build image and CI provide `confluent-kafka` (librdkafka). After
that, the rest of the core services should be migrated, and Avro semantics
should be enforced in production.

If you approve, I can now generate a patch that implements the conservative
first fix (fail-fast `confluent-kafka` in `learner_online.py`) and update
`env.example` and CI placeholders, or produce a per-file change list to review
before coding.
