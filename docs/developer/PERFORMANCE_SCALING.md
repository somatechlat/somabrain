> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# Performance & Scaling Guidelines

Focused on actionable levers; no speculative tuning.

## 1. Core Cost Drivers
| Component | Complexity | Notes |
|-----------|------------|-------|
| HRR bind/unbind | O(D log D) (FFT) | D=8192 typical => ~0.15–0.3 ms CPU |
| Wiener unbind | O(D log D) + overhead | Additional spectral division |
| Sinkhorn small OT | O(n·m·iters) | Keep n,m ≤ 64 in request path |
| Graph heat (Chebyshev) | O(K·(A mult)) | K ~ 24, sparse mult cost dominated by edges |

## 2. Dimensionality Trade-offs
| Dim | Cosine Discrimination | Latency Impact | Memory Footprint (float32 vec) |
|-----|-----------------------|----------------|---------------------------------|
| 2048 | Low/Moderate | Fastest | 8 KB |
| 8192 | Strong (baseline) | Acceptable | 32 KB |
| 16384 | High | +40–50% FFT time | 64 KB |

Rule: increase dim only after recall quality metrics plateau (HRR_CLEANUP_SCORE, RECALL_MARGIN_TOP12).

## 3. Sharding Strategy
- Hash: `tenant_id -> shard_index` (jump consistent hashing for stability).
- Keep shard memory warm via background prefetch of recently active tenants.
- Route recall/write through lightweight shard router; avoid cross-shard scatter unless performing global analytics batch.

## 4. Caching Layers
| Layer | Purpose | Eviction |
|-------|---------|----------|
| Role Spectrum (mmap) | Avoid recomputing unitary roles | Size cap by distinct tokens |
| Embedding Cache | Frequent prompt prefixes | LRU by access timestamp |
| Recall Result Cache | Repeat queries (<2s TTL) | Time-based |

## 5. Prewarming Sequence
1. Load configuration & truth-budget.
2. Instantiate HRR layer; generate top-N roles (N≈50–100).
3. Embed system prompts & pin in embedding cache.
4. Lazy warm less frequent roles on first use (as already implemented). 

## 6. Latency Optimization Knobs
| Knob | Effect | Risk |
|------|--------|------|
| Reduce `beta` in unbind | Sharper reconstruction | Potential noise blow-up |
| Increase Wiener SNR | Closer to exact inverse | Amplifies high-frequency noise |
| Enable HRR-first rerank only for low margin | Cuts average cost | Slight quality drop for borderline cases |

## 7. Throughput Tactics
- Batch similar `/recall` embeddings via micro-batcher (<=5ms window) if QPS bursty.
- Parallelize independent memory shard reads with asyncio.gather.
- Collapse identical concurrent queries (query coalescing) using an in-flight map.

## 8. Memory Pressure Handling
| Signal | Action |
|--------|--------|
| WM_UTILIZATION > 0.9 | Evict oldest or lowest salience items |
| Anchor saturation | Increase anchors max (hrr_anchors_max) or apply aging decay |
| Redis eviction logs | Raise maxmemory or separate namespaces |

## 9. Observability Focus
- Alert if: `UNBIND_EPS_USED` p95 increases > 3x baseline over 10m.
- Track `HRR_CLEANUP_SCORE` 5m moving average.
- Derive early saturation index: anchors_used / anchors_capacity.

## 10. Horizontal Scaling Formula (Rule of Thumb)
Required pods ≈ (Target_RPS * Avg_Latency_ms / 1000) * (Safety_Factor)
Safety_Factor ~ 1.3–1.5

Example: 1200 RPS, 30ms avg → 1200*30/1000=36 core-ms concurrency → ~36 workers; on 8-core machines with 16 workers each → 3 pods + headroom ⇒ 4 pods.

## 11. Rolling Dimension Increase (Safe Path)
1. Shadow compute new-dim vectors in memory (do not serve yet).
2. Log reconstruction cosine old vs new (target delta < 0.02).
3. When stable, switch embedding + binding modules atomically during low-traffic window.

## 12. Failure Drills
| Scenario | Drill |
|----------|-------|
| Role cache corruption | Purge cache; recompute; verify invariant tests pass |
| Elevated epsilon | Run bind/unbind diagnostic with synthetic orthogonal vectors |
| Recall latency spike | Disable HRR-first toggle temporarily; isolate shard hotspots |

Keep this file terse—extend only when new mechanisms become standard.
