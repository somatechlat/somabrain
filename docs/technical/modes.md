# Runtime Modes (ISO/IEC 12207§6.4.7)

**Purpose**: Define runtime modes and operational guarantees for local/prod parity.

**Audience**: SREs, platform engineers, developers.

---

## Mode Taxonomy

| Mode | Description | Use Case |
|------|-------------|----------|
| `full-local` | Complete stack on localhost | Local development with full parity |
| `prod` | Production deployment | Cloud infrastructure |
| `ci` | Continuous integration | Automated testing |

---

## Mode Configuration

### full-local

**Characteristics**:
- Avro-only serialization (no JSON fallbacks)
- All core services enabled: integrator, reward, learner, drift, segmentation
- Same Kafka topics/schemas as prod
- Local Kafka/Redis/Postgres/OPA deployment
- Health and metrics endpoints on localhost

**Environment**:
```bash
SOMABRAIN_MODE=full-local
SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1
SOMABRAIN_FORCE_FULL_STACK=1
```

### prod

**Characteristics**:
- Identical semantics to `full-local`
- Cloud infrastructure (managed Kafka, Redis, Postgres)
- External secrets management
- TLS/mTLS enabled

**Environment**:
```bash
SOMABRAIN_MODE=prod
SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1
SOMABRAIN_FORCE_FULL_STACK=1
```

### ci

**Characteristics**:
- Strict semantics (no protocol relaxations)
- Services may run pared-down for speed
- Real Kafka/Redis/Postgres via Docker Compose
- Optional test bypass via `SOMABRAIN_REQUIRE_INFRA=0` for unit isolation

**Environment**:
```bash
SOMABRAIN_MODE=ci
SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1
```

---

## Feature Matrix

**Single Source of Truth (SSOT)**: Central resolver maps `SOMABRAIN_MODE` to feature flags.

| Feature | full-local | prod | ci |
|---------|------------|------|-----|
| Integrator | ✅ | ✅ | ✅ |
| Reward Ingest | ✅ | ✅ | ✅ |
| Learner | ✅ | ✅ | ✅ |
| Drift Detection | ✅ | ✅ | ✅ |
| Segmentation | ✅ | ✅ | ✅ |
| Metrics | ✅ | ✅ | ✅ |
| Health HTTP | ✅ | ✅ | ✅ |
| OPA Gate | ✅ | ✅ | ✅ |
| Avro Required | ✅ | ✅ | ✅ |
| Fail-Fast Producers | ✅ | ✅ | ✅ |
| No Fallbacks | ✅ | ✅ | ✅ |

---

## Endpoint Policy

**Metrics & Health**:
- Always enabled for observability
- Bind to `localhost` in `full-local` mode
- Bind to `0.0.0.0` in `prod` mode (behind ingress)

**Debug Endpoints**:
- Gated by mode or disabled in prod
- Examples: `/tau`, `/diagnostics`

**Removed**:
- Drift HTTP introspection (use Prometheus + `scripts/drift_dump.py`)

---

## Docker Compose Profile

**Command**:
```bash
docker compose --profile full-local up -d
```

**Services**:
- `somabrain_app` - API server
- `somabrain_cog` - Cognitive services (supervisor)
- `somabrain_kafka` - Message broker
- `somabrain_redis` - Working memory cache
- `somabrain_postgres` - Metadata storage
- `somabrain_opa` - Policy engine
- `somabrain_prometheus` - Metrics collection
- `somabrain_outbox_publisher` - Event publisher

---

## Invariants

**Enforced by Mode**:
1. Avro-only serialization for all cognitive topics
2. Fail-fast Kafka producers (no silent failures)
3. No retired clients or JSON fallbacks
4. Mode assertions: `full-local` implies all core services enabled

**Validation**:
- `tests/invariants/test_mode_config.py` - Mode configuration tests
- `tests/invariants/test_strict_mode.py` - Strict mode enforcement
- `tests/invariants/test_no_fallbacks.py` - No fallback detection

---

## Migration from Legacy Flags

**Deprecated Flags** (removed):
- `SOMABRAIN_DISABLE_KAFKA` - Kafka now mandatory
- `ENABLE_*` scattered flags - Use mode-based feature matrix

**Migration Path**:
1. Set `SOMABRAIN_MODE` explicitly
2. Remove legacy `ENABLE_*` flags from env
3. Verify services start with mode-based config
4. Update CI/CD pipelines to use mode profiles

---

## Validation Checklist

**Infrastructure**:
- [ ] Kafka topics exist and schemas load
- [ ] Avro producers/consumers initialized
- [ ] Redis connection established
- [ ] Postgres migrations applied
- [ ] OPA policies loaded

**Services**:
- [ ] Integrator running and emitting frames
- [ ] Learner consuming rewards
- [ ] Drift detector monitoring entropy
- [ ] Reward producer publishing events

**Observability**:
- [ ] Health endpoints return 200 OK
- [ ] Prometheus scraping metrics
- [ ] OTel tracing configured
- [ ] Alerts loaded in Alertmanager

**Cognitive Features**:
- [ ] Temperature scaling active
- [ ] Entropy caps enforced
- [ ] Drift baselines persist
- [ ] Context builder respects tenant limits

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Services fail to start | Missing mode config | Set `SOMABRAIN_MODE` explicitly |
| Kafka connection errors | Broker not ready | Wait for health check, verify `KAFKA_BOOTSTRAP` |
| Avro deserialization errors | Schema mismatch | Run `scripts/ci/check_avro_compat.py` |
| OPA policy failures | Policies not loaded | Check `ops/opa/policies/` mount |

---

## Related Documentation

- [Deployment](deployment.md) - Deployment procedures
- [Configuration](configuration.md) - Environment variables
- [Strict Mode](../operational/strict-mode.md) - Strict mode enforcement
