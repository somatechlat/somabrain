> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# Production Configuration (Canonical Baseline)

Only high-impact settings that materially affect correctness, throughput, or large-scale reliability are listed.

## 1. Environment Variables (Critical Subset)
| Variable | Purpose | Recommended Default | Notes |
|----------|---------|---------------------|-------|
| SOMABRAIN_HRR_DIM | HRR vector dimension | 8192 (baseline), 16384 (rich) | Higher = better semantic separation; memory ∝ dim |
| SOMABRAIN_HRR_SEED | Deterministic global seed | 42 | Stable reproducibility |
| SOMABRAIN_MINIMAL_PUBLIC_API | Restrict public endpoints | 0 | Keep 0 for full API in production cluster |
| SOMABRAIN_RATE_RPS | Soft rate limit | 500 | Tune per pod capacity |
| SOMABRAIN_WRITE_DAILY_LIMIT | LTM write quota | 500000 | Guard runaway agents |
| SOMABRAIN_REDIS_URL | Primary Redis | redis://host:6379/0 | Use dedicated instance |
| SOMABRAIN_USE_HRR | Enable HRR layer | true | Disable only for emergency fallback |
| SOMABRAIN_USE_HRR_FIRST | HRR-first rerank | true (if dim>=4096) | Gains depend on workload |
| SOMABRAIN_WIENER_SNR_DB | Default Wiener SNR | 40 | 20=more smoothing, 60=sharper |
| SOMABRAIN_CONSOLIDATION_TIMEOUT_S | Max seconds per NREM/REM phase | 1.0 | Prevents long-running consolidation from blocking API |

## 2. Process Model
| Layer | Recommendation | Rationale |
|-------|----------------|-----------|
| ASGI Workers | gunicorn with uvicorn workers | Mature supervisory + asyncio |
| Worker Count | `2 * physical_cores` | Utilization with IO + bursts |
| Threads | 1 (async only) | Avoid GIL contention |
| Loop | uvloop | Lower latency event loop |
| Graceful Timeout | 30s | Allow inflight long recall |

Example (8 core node):
```
gunicorn somabrain.app:app \
  -k uvicorn.workers.UvicornWorker \
  --workers 16 \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout 45 \
  --graceful-timeout 30 \
  --keep-alive 30
```

## 3. Redis
| Setting | Value |
|---------|-------|
| persistent storage | AOF (everysec) |
| maxmemory policy | allkeys-lru |
| latency monitoring | ENABLED (latency doctor) |
| connection pool | min 10, max 200 |

Use separate Redis for: (a) core memory metadata, (b) ephemeral rate counters (optional).

## 4. HRR Dimensions & Memory
| Tier | Dim | Use Case |
|------|-----|----------|
| Tiny | 2048 | Edge / test rigs |
| Baseline | 8192 | Standard production |
| Rich | 16384 | Dense semantic / multi-domain agents |

Memory impact: float32 vector ≈ 4 * dim bytes. Role cache stores time + spectrum (≈ 6 * dim bytes). Estimate baseline 8192 dim role pair ≈ ~192 KB.

## 5. Startup Optimizations
1. Pre-warm unitary roles for top N frequent tokens (predict from logs) to reduce first-request latency.
2. Warm embeddings cache for system prompts / scaffolds.
3. Lazy-load optional components (constitution engine already lazy). 

## 6. Metrics & Observability
| Metric | Actionable Threshold |
|--------|----------------------|
| UNBIND_EPS_USED | Unexpected spikes => inspect spectral energy distribution |
| HRR_CLEANUP_SCORE | Sustained <0.4 => anchor saturation or dimensionality too low |
| RECALL_MARGIN_TOP12 | Falling trend => noise, consider rerank weight tuning |
| WM_UTILIZATION | >0.85 sustained => trigger eviction or scale out |

Prometheus scrape interval: 5s (fast) or 15s (cost-conscious). 

## 7. Latency Budget Targets (p50 / p95)
| Operation | p50 | p95 | Notes |
|-----------|-----|-----|-------|
| /remember | <20ms | <60ms | Mostly embedding + admission |
| /recall (top_k=8) | <35ms | <90ms | HRR rerank adds ~5–10ms at 8k dim |
| HRR bind/unbind | <0.2ms | <0.6ms | Pure NumPy FFT on 8k dim |
| Sinkhorn (small OT) | <3ms | <8ms | Avoid large n^2 in sync path |

## 13. Dev-Prod Parity Tips

- In local Docker, run the API with a single worker (SOMABRAIN_WORKERS=1) to keep in‑process WM read‑your‑writes
  for smoke/tests. In production, scale workers as needed.
- To run tests against the live Docker API on 9696, export:
  ```bash
  export SOMA_API_URL_LOCK_BYPASS=1
  export SOMA_API_URL=http://127.0.0.1:9696
  pytest -q
  ```
- Keep SOMABRAIN_CONSOLIDATION_TIMEOUT_S small (1–2s) to avoid request timeouts during `/sleep/run` under load.
## 8. Scaling Strategy (Horizontal)
1. Stateless API pods behind load balancer.
2. Shard working memory by tenant hash (consistent hashing ring) to keep locality.
3. Offload rarely accessed LTM segments to secondary persistence (e.g., object store) with lazy hydrate.
4. Use role spectrum disk cache (mmap) shared per node to amortize generation.
5. Gradually increase HRR dim in dark launch (duplicate bind/unbind internally, compare cosine before switch).

## 9. Failure / Degradation Modes
| Symptom | Mitigation |
|---------|------------|
| High unbind epsilon | Increase dim or review role collisions |
| Low recall margin | Enable HRR-first or increase anchors max |
| Redis latency spikes | Add replica / move rate limiting to in-memory token bucket |
| Memory saturation | Evict least-recalled anchors / compress payload metadata |

## 10. Security & Auth
Minimal public API mode should remain OFF internally; use gateway/WAF for external restriction. Auth gating for /remember and /recall via token or JWT when multi-tenant external exposure required.

## 11. Rolling Upgrade Playbook
1. Deploy new pods with `SOMABRAIN_HRR_DIM` duplicated (no change) for fast rollback.
2. In shadow mode, compute new-dim bindings side-by-side and log cosine deltas.
3. Promote dim increase only if average cosine delta < 0.02 and latency < defined SLO budget.

## 12. Checklist Before Production
- [ ] All property tests green in CI
- [ ] Role cache warm pre-launch (top 50 roles)
- [ ] Metrics dashboard: unbind eps, recall margin, utilization, Anchor size
- [ ] Load test: sustain target RPS + 20% headroom
- [ ] Alerting: p95 recall latency, Redis latency, unbind eps spike

*Keep this document lean; expand only when a setting proves critical in postmortems.*
