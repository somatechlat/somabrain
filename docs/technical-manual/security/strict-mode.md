> :warning: SomaBrain must run on real services. No mocks, no stubs, no fake data.

# Backend Enforcement Mode (No-Stubs Contract)

**Purpose**: Document the controls that keep SomaBrain from silently falling back to dummy implementations.

**Audience**: Operators, SREs, and developers responsible for enforcing backend-enforced deployments.

**Prerequisites**: Understanding of the runtime configuration documented in `../configuration.md` and service dependencies described in `../architecture.md`.

---

## Activation

Set the environment variable and restart the process:

```bash
export SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1
```

When enabled, any attempt to invoke a stub, dummy, or placeholder path raises immediately with a clear error. This guarantees end-to-end realism in CI and production.

---

## Goals

| Goal | Why It Matters |
|------|----------------|
| Eliminate hidden quality drift | Stub predictors or fake recall mask regressions |
| Deterministic reproducibility | Identical inputs produce identical embeddings and rankings |
| Early surfacing of infra gaps | Failing fast in CI prevents late-stage outages |
| Observability truthfulness | Metrics and health endpoints reflect actual serving conditions |

---

## Enforcement Points

| Component | Enforcement | Failure Condition (Strict) | Remediation |
|-----------|-------------|-----------------------------|-------------|
| Predictor | Reject `stub|baseline` providers | Startup raises | Set `SOMABRAIN_PREDICTOR_PROVIDER=mahal` or `llm` |
| Embedder | Blocks dummy embedder injection | Import raises when missing | Ensure `somabrain.embeddings` loads successfully |
| Working Memory | Disallows dummy WM | Import raises if Redis absent | Provide a real Redis backend |
| Recall Path | Rejects stub fallbacks | Runtime error when no HTTP + no local data | Configure the memory endpoint or seed real payloads |
| RAG Pipeline | Blocks stub retrievers | Runtime error | Configure real retriever backends or disable the route |
| Stub Usage | `_audit_stub_usage` raises | Any attempt increments the counter | Remove or replace stub code |

---

## Health & Readiness Contract

`/health` returns realism diagnostics such as:

```json
{
  "predictor_provider": "mahal",
  "external_backends_required": true,
  "embedder": {"provider": "tiny", "dim": 256},
  "stub_counts": {},
  "ready": true,
  "memory_items": 42
}
```

An enforcement-enabled deployment is **ready** only when:
1. Predictor is non-stub.
2. Embedder initializes successfully.
3. Memory HTTP service responds or at least one mirrored payload exists locally.

Agents must gate work on `ready: true` responses.

---

## In-Process Recall Path

If the external memory endpoint is not configured, backend enforcement uses deterministic similarity:

1. Embed the query with the active embedder.
2. Embed each locally mirrored payload.
3. Rank via cosine similarity and return the top results.
4. When no payloads exist, raise an instructive error—never fabricate data.

---

## Predictor Precedence

1. `SOMABRAIN_PREDICTOR_PROVIDER` environment variable.
2. `config.yaml` `predictor_provider` entry.
3. Fallback `stub` (blocked when enforcement is active).

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `BACKEND ENFORCEMENT: predictor provider 'stub' is not permitted` | Env/config left at default | Export `SOMABRAIN_PREDICTOR_PROVIDER=mahal` |
| `BACKEND ENFORCEMENT: embedder missing` | Dependency failed to load | Ensure `somabrain.embeddings` initialises |
| Recall runtime error about stub path | No memory endpoint and empty local payloads | Seed at least one `remember` call or configure the HTTP service |
| RAG enforcement failure | Stub retriever branch executed | Configure real retriever or disable the route |

---

## Bypass (Development Only)

Temporary bypass is allowed for isolated debugging—not CI or production:

```bash
export SOMABRAIN_ALLOW_BACKEND_FALLBACKS=1
```

The `tests/conftest.py` fixture respects this flag and will not auto-enable backend enforcement when set.

---

## Metrics To Consider

| Metric | Type | Purpose |
|--------|------|---------|
| `somabrain_stub_fallback_blocked_total` | Counter | Counts prevented stub usages (should stay at 0) |
| `somabrain_inprocess_recall_total` | Counter | Tracks deterministic fallback frequency |
| `somabrain_recall_source` | Counter (labelled) | Distinguishes HTTP vs in-process recall |

---

## Migration Checklist

- [ ] Set `SOMABRAIN_PREDICTOR_PROVIDER` explicitly in every environment.
- [ ] Export `SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1` in CI and production.
- [ ] Gate consumers on `/health` `ready` status.
- [ ] Verify `stub_counts` is empty after warm-up.
- [ ] Add dashboard panels for strict-mode metrics.
