> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# Strict Real Mode (No-Stubs Contract)

Strict mode guarantees that every cognitive path exercised in tests or production uses **real, deterministic implementations**—never silent fallbacks or placeholder stubs. It is activated by setting:

```
export SOMABRAIN_STRICT_REAL=1
```

When enabled, any attempt to invoke a stub / dummy / placeholder path raises immediately with a
clear error to force explicit configuration.

## Goals
| Goal | Why It Matters |
|------|----------------|
| Eliminate hidden quality drift | Stub predictors or fake recall mask regressions. |
| Deterministic reproducibility | Identical inputs → identical embeddings / recall ranking. |
| Early surfacing of infra gaps | Failing fast in CI prevents flaky late-stage failures. |
| Observability truthfulness | Metrics/health represent actual serving conditions. |

## Enforcement Points
| Component | Enforcement | Failure Condition (Strict) | Remediation |
|-----------|-------------|-----------------------------|-------------|
| Predictor | Reject `stub|baseline` provider | Process startup raises | Set `SOMABRAIN_PREDICTOR_PROVIDER=mahal` or `llm` |
| Embedder | No dummy embedder injection | Import raises if missing | Ensure `make_embedder` succeeds (defaults to deterministic tiny) |
| Working Memory | No dummy WM | Import raises if WM absent | Allow initialization or configure capacity appropriately |
| Recall | Disallow pure stub recent-payload fallback | Runtime error if no HTTP and no local data | Expose a real memory endpoint or seed memories (in-process real similarity used if payloads exist) |
| RAG pipeline | Stub retrievers blocked | Runtime error | Configure real retriever backends / indices |
| Stub Usage | `record_stub(path)` raises | Any attempt to count stub | Remove or replace code using stub fallback |

## Health & Readiness Contract
`/health` returns realism diagnostics:
```json
{
  "predictor_provider": "mahal",
  "strict_real": true,
  "embedder": {"provider": "tiny", "dim": 256},
  "stub_counts": {},
  "ready": true,
  "memory_items": 42
}
```
A strict-mode deployment is considered **ready** when:
1. Predictor is non-stub
2. Embedder initialized
3. Memory HTTP healthy OR at least one in-process memory payload present

Agents MUST gate task consumption on `ready=true`.

## In-Process Recall (Deterministic Path)
If the external memory endpoint is not configured, strict mode uses real deterministic similarity:
1. Embed query with active embedder.
2. Embed each locally mirrored payload (task/content/text/description heuristic).
3. Rank via cosine; return top_k.
4. If no payloads exist, raise instructive error (never silently fabricate data).

## Predictor Precedence
1. `SOMABRAIN_PREDICTOR_PROVIDER` (env)
2. `config.yaml` `predictor_provider`
3. Fallback `stub` (rejected under strict)

## Typical Errors & Fixes
| Error | Cause | Fix |
|-------|-------|-----|
| `STRICT REAL MODE: predictor provider 'stub' not permitted` | Env/config left at default | Export `SOMABRAIN_PREDICTOR_PROVIDER=mahal` |
| `STRICT REAL MODE: embedder missing` | Early import ordering / failed dependency | Ensure `somabrain.embeddings` loads (has no external requirements) |
| Recall runtime error about stub path | No memory endpoint & empty local payload set | Seed at least one `remember` or configure the external memory API |
| RAG strict failure | Stub retriever branch executed | Configure real retriever OR feature-flag route off |

## Migration Checklist
- [ ] All environments set `SOMABRAIN_PREDICTOR_PROVIDER` explicitly (no implicit stub).
- [ ] CI pipeline exports `SOMABRAIN_STRICT_REAL=1`.
- [ ] `/health` consumed by agents; gating implemented.
- [ ] No `record_stub` call sites reached in normal flows (verify `stub_counts` empty after warmup).
- [ ] Operational dashboards include readiness & predictor provider panels.

## Metrics To Add (Optional Enhancements)
| Metric | Type | Purpose |
|--------|------|---------|
| `somabrain_stub_fallback_blocked_total` | Counter | Counts prevented stub usages (should stay 0) |
| `somabrain_inprocess_recall_total` | Counter | Track fallback frequency vs HTTP recall |
| `somabrain_recall_source` | Counter (label=source) | HTTP vs inprocess distribution |

## Bypass (Development Only)
To momentarily allow legacy fallback (NOT in CI / prod):
```
export SOMABRAIN_STRICT_REAL_BYPASS=1
```
The `tests/conftest.py` fixture respects this and will *not* auto-set strict mode.

## FAQ
**Q:** Is the deterministic tiny embedder “real”?  
**A:** Yes—it produces consistent unit-norm embeddings; no placeholders or random stubs.

**Q:** Can I mix LLM predictor and mahal?  
**A:** Yes—implement dynamic selection per task type; strict mode only forbids the *stub* provider.

**Q:** Why require local payloads for in-process recall readiness?  
**A:** Prevents green health when retrieval would otherwise always return empty, masking integration gaps.

---
For the authoritative env variable list see: `../CONFIGURATION.md`.
