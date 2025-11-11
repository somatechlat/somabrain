## Environment Variables

This page lists the key environment variables that control SomaBrain in both local dev and production-like deployments. Defaults reflect the repository’s developer-prod posture (strict real backends, full stack).

Important: Learning gains/bounds and adaptation parameters are now centralized in code. Legacy `SOMABRAIN_LEARNING_*` overrides were removed in favor of runtime configuration and Avro `config_update` messages from the learner. See Technical Manual → Fusion / Consistency / Drift.

### Core runtime
- SOMABRAIN_MODE: execution mode. Typical values: enterprise (dev), production (prod).
- SOMABRAIN_HOST: bind address inside the container (default 0.0.0.0).
- SOMABRAIN_PORT: container listen port (default 9696).
- SOMABRAIN_HOST_PORT: host port mapped to the API. Set via .env by scripts/dev_up.sh.

### Enforcement and features
- SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS: 1 to enforce real backends (no dev fallbacks).
- SOMABRAIN_FORCE_FULL_STACK: 1 to require all backing services for readiness.
- SOMABRAIN_REQUIRE_MEMORY: 1 to require external memory to be reachable for readiness.
- SOMABRAIN_PREDICTOR_PROVIDER: predictor backend (mahal|baseline).

### External services (containers use Docker DNS names)
- SOMABRAIN_REDIS_URL: e.g., redis://somabrain_redis:6379/0
- SOMABRAIN_POSTGRES_DSN: e.g., postgresql://soma:soma_pass@somabrain_postgres:5432/somabrain
- SOMABRAIN_KAFKA_URL: e.g., kafka://somabrain_kafka:9092
- SOMABRAIN_OPA_URL: e.g., http://somabrain_opa:8181

### Memory backend
- SOMABRAIN_MEMORY_HTTP_ENDPOINT: HTTP endpoint for long‑term memory.
  - Host runs: http://localhost:9595
  - Containers (Docker Desktop): http://host.docker.internal:9595
- SOMABRAIN_MEMORY_HTTP_TOKEN: bearer token for the memory service (if required).

### Auth and security
- SOMABRAIN_JWT_SECRET: JWT signing secret (required when auth enabled).
- SOMABRAIN_API_TOKEN: optional static token if you use simple header-based auth.
- SOMA_OPA_FAIL_CLOSED: (removed) OPA runs fail-closed by default; posture derived from mode.

### Consistency enforcement (runtime-config flags, not env)

These are code-level runtime flags (see `somabrain/runtime_config.py`) surfaced for awareness. Tune via runtime override file in full-local mode or code defaults in other modes.

- consistency_kappa_min: minimum acceptable κ before enforcement (default 0.55)
- consistency_fail_count: consecutive violations before degraded (default 3)
- consistency_kappa_hysteresis: recovery margin (default 0.05)
- consistency_drop_frame: drop frames with leader=action under degraded κ (default true)
- consistency_alert_enabled: log alert on transition to degraded (default true)

### Outbox/journaling (durability under outages)
 
- SOMABRAIN_OUTBOX_BATCH_SIZE, SOMABRAIN_OUTBOX_MAX_DELAY, SOMABRAIN_OUTBOX_POLL_INTERVAL, SOMABRAIN_OUTBOX_MAX_RETRIES: outbox worker tuning.

### Kafka KRaft (single-node dev defaults)
The scripts write sane defaults into .env for a single-node, dual-listener Kafka broker. Key variables include KAFKA_BROKER_HOST_PORT, KAFKA_CFG_LISTENERS, and KAFKA_CFG_ADVERTISED_LISTENERS.

Notes
- scripts/dev_up.sh writes .env with resolved values and a ports.json with the effective host-port mappings (API fixed at 9696).
- Health and readiness reflect these flags: external_backends_required, full_stack, memory_ok, embedder_ok, retrieval_ready.
