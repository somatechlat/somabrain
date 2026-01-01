# Retrieval Observability Runbook (Strict Real Mode)

This runbook documents the mandatory metrics, alert rules, and triage steps for the retrieval pipeline under strict production realism. No fallbacks, no silent degradation: empty results and latency surfaces must reflect actual system performance.

## Scope
Covers the unified retrieval pipeline (vector, graph, recent/WM, lexical components) and rank fusion / reranking stages. Applies to all namespaces/tenants.

## Core Metrics (Prometheus)

| Purpose | Metric | Type | Labels | Notes |
|---------|--------|------|--------|-------|
| Requests | `somabrain_retrieval_requests` | Counter | namespace,retrievers | Total retrieval pipeline invocations; retrievers label encodes active set (e.g. `vector+graph`). |
| Latency | `somabrain_retrieval_latency_seconds` | Histogram | (none) | End-to-end pipeline latency (embedding → fusion → output). |
| Candidate Count | `somabrain_retrieval_candidates_total` | Histogram | (none) | Post-dedupe + rerank final candidate size. |
| Empty Responses | `somabrain_retrieval_empty_total` | Counter | namespace,retrievers | Incremented when zero candidates returned (strict empty; no backfill). |
| Per-Retriever Hit | `somabrain_retriever_hits_total` | Counter | namespace,retriever | Non-empty candidate list per retriever adapter. |
| Fusion Applied | `somabrain_retrieval_fusion_applied_total` | Counter | method | Number of rank fusion executions (e.g. `weighted_rrf`). |
| Fusion Sources | `somabrain_retrieval_fusion_sources` | Histogram | (none) | Distribution of number of source lists fused. |

### Secondary / Stage Metrics
| Purpose | Metric | Type | Labels | Notes |
| WM Stage Latency | `somabrain_recall_wm_latency_seconds` | Histogram | cohort | Latency for working-memory stage pre-merge. |
| LTM Stage Latency | `somabrain_recall_ltm_latency_seconds` | Histogram | cohort | Latency for long-term memory stage. |
| ANN Latency | `somabrain_ann_latency_seconds` | Histogram | namespace | ANN index lookup timing. |
| Recall Requests | `somabrain_recall_requests_total` | Counter | namespace | Higher-level recall endpoint usage. |

## Alerts (`alerts.yml`)

| Alert | Condition | Window | Severity | Rationale |
|-------|-----------|--------|----------|-----------|
| RetrievalEmptyRateHigh | empty / requests > 0.30 | 5m (for 5m) | warning | Elevated empty responses; index coverage or retriever outage. |
| RetrievalLatencyP95High | p95 latency > 0.40s | 10m (for 10m) | warning | User-facing latency risk; ANN/fusion pressure or backend slowness. |
| (Indirect) PlanningLatencyP99High | planning p99 > 40ms | 10m | warning | Upstream planning pressure may cascade into retrieval demand. |

## Expected Baselines
- Empty Rate: < 10% for healthy populated memory corpus (early cold start may be higher; alert catches sustained >30%).
- p95 Latency: < 250ms typical; threshold set at 400ms leaves investigation margin.
- Fusion Sources: Usually 2–4; spikes may indicate experimental retriever activation.

## Triage Flow

1. Alert Triggered → Identify which (Empty Rate or Latency).
2. Scope: Check label namespace(s) impacted via Prometheus query.
3. Isolation Steps:
   - For Empty Rate: Query per-retriever hits
     ```promql
     sum by (retriever) (rate(somabrain_retriever_hits_total[5m]))
     ```
     If a single retriever returns zero while others have hits → retriever-specific outage (vector index rebuild, graph service connectivity, etc.).
   - For Latency: Break down ANN vs WM vs LTM stage histograms:
     ```promql
     histogram_quantile(0.95, sum(rate(somabrain_ann_latency_seconds_bucket[5m])) by (le))
     histogram_quantile(0.95, sum(rate(somabrain_recall_wm_latency_seconds_bucket[5m])) by (le))
     histogram_quantile(0.95, sum(rate(somabrain_recall_ltm_latency_seconds_bucket[5m])) by (le))
     ```
     Pinpoint dominant stage.
4. Infrastructure Readiness:
   - Run `scripts/ci_readiness.py` manually if doubtful about Kafka/Redis/Postgres/OPA.
5. ANN Issues:
   - Check rebuild counters:
     ```promql
     increase(somabrain_ann_rebuild_total[15m])
     ```
     Frequent rebuilds can stall queries.
6. Empty + Low Fusion Sources:
   - Fusion sources histogram low (1) indicates only one retriever active → verify configuration enabling vector/graph adapters.
7. Persist Session Effects:
   - Inspect `somabrain_retrieval_persist_total` counters for recent persistence status spikes (session gating).

## Common Root Causes & Signals
| Symptom | Likely Cause | Corroborating Metric |
|---------|--------------|----------------------|
| Empty rate spike & zero hits for vector | ANN index unavailable/rebuilding | `increase(somabrain_ann_rebuild_total[10m]) > 0` |
| Empty rate spike & graph hits only | Embedding provider outage | Vector retriever latency high / zero hits |
| Latency spike WM stage | Redis contention | Elevated `somabrain_recall_wm_latency_seconds` p95 only |
| Latency spike ANN only | Index memory pressure / rebuild | `somabrain_ann_latency_seconds` p95 elevated |
| Latency + Empty both elevated | Kafka publish lag causing upstream ingestion stall | External kafka lag exporter (out-of-repo) |

## Manual Queries Cheat Sheet
```promql
# Empty ratio overall (fast check)
(sum(rate(somabrain_retrieval_empty_total[5m])) / clamp_min(sum(rate(somabrain_retrieval_requests[5m])),1))

# Per namespace empty ratio
(sum by (namespace) (rate(somabrain_retrieval_empty_total[5m])) / clamp_min(sum by (namespace) (rate(somabrain_retrieval_requests[5m])),1))

# p95 retrieval latency
histogram_quantile(0.95, sum(rate(somabrain_retrieval_latency_seconds_bucket[5m])) by (le))

# Per-retriever hit rate
sum by (retriever) (rate(somabrain_retriever_hits_total[5m]))
```

## Operational Actions
| Action | Description |
|--------|-------------|
| Warm Index | Trigger controlled ANN rebuild off-peak; monitor rebuild duration histograms. |
| Increase Capacity | Scale memory/embedding workers if WM or embedding latency the bottleneck. |
| Session Persistence Audit | Review persistence outcomes in `somabrain_retrieval_persist_total`; frequent failures may impact hit composition. |
| Retriever Config Check | Confirm adapter enablement (environment flags enabling vector, graph). |
| Backpressure | If planning latency also elevated, upstream planning queue saturation may require rate control. |

## No-Fallback Enforcement
If a retriever fails internally it must yield zero candidates; pipeline still records empty metrics. DO NOT introduce synthetic or cached backfill. Empty responses are an SLO signal.

## Readiness Gating
Integration tests auto-run `scripts/ci_readiness.py`; replicate manually before deploying:
```bash
python scripts/ci_readiness.py
```
Exit code != 0 blocks deployment.

## Escalation Thresholds
| Condition | Escalate To | Notes |
|-----------|-------------|-------|
| Empty Rate >50% for 10m | On-call Engineering | Potential systemic retrieval outage. |
| Latency p95 >800ms for 5m | On-call Engineering | User SLA breach imminent. |
| ANN rebuilds >10 in 30m | Index Maintainer | Misconfiguration or thrashing. |

## Future Extensions (Out-of-Repo)
- External dashboard pack (not stored here per policy).
- Alert refinement (soft warn at 20% empty, critical at 50%).
- Cross-retriever contribution ratio (vector vs graph vs recent). 

## Verification
To verify metrics export:
1. Hit `/metrics` endpoint of the API or cognition service.
2. Confirm presence of `somabrain_retrieval_empty_total` and `somabrain_retriever_hits_total`.
3. Fire a synthetic retrieval request and watch counters increment.

## References
- Internal metrics implementation: `somabrain/metrics.py`
- Alert rules: `alerts.yml`
- Readiness script: `scripts/ci_readiness.py`

Strict realism mandates authentic failure exposure; treat empty results as truth, not a UX defect to mask.
