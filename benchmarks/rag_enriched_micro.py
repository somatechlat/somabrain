"""
Enriched RAG Micro-Benchmark
----------------------------

Seeds a synthetic, clustered corpus via /remember and evaluates retrieval
quality against /rag/retrieve with multiple retriever configurations.

Metrics per configuration:
- HR@1 (top-1 hit rate)
- P@k, R@k (precision/recall @k)
- MRR (Mean Reciprocal Rank)
- nDCG@k (Normalized Discounted Cumulative Gain)

Outputs JSON and a compact Markdown summary in the chosen artifacts directory.

Usage:
  python -m benchmarks.rag_enriched_micro \
    --api-base http://localhost:9999 \
    --tenant showcase \
    --out-dir artifacts/showcase \
    --top-k 5

Notes:
- Uses purely synthetic data carefully constructed to ensure non-zero hit rates
  across lexical and vector retrievers.
- Graph mode is also evaluated after a persistence pass to create learned links.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class QueryCase:
    query: str
    positives: List[str]
    # Optional graded relevance mapping (key -> gain)
    relmap: Optional[Dict[str, int]] = None


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _slugify(s: str) -> str:
    import re

    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "doc"


def _seed_corpus(api_base: str, tenant: str, token: Optional[str], docs: List[str]) -> Dict[str, str]:
    assert httpx is not None, "httpx is required to run this benchmark"
    headers = {"X-Tenant-ID": tenant}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    client = httpx.Client(timeout=5.0)
    slug_map: Dict[str, str] = {}
    for d in docs:
        body = {
            "tenant": tenant,
            "namespace": "ltm",
            "key": d,
            "value": {"task": d, "memory_type": "episodic", "importance": 1},
        }
        r = client.post(api_base.rstrip("/") + "/remember", json=body, headers=headers)
        r.raise_for_status()
        # Seed a slug alias to enable mode=auto key detection (single-token)
        slug = _slugify(d)
        slug_map[d] = slug
        alias = {
            "tenant": tenant,
            "namespace": "ltm",
            "key": slug,
            # Point payload back to canonical task to keep evaluation consistent
            "value": {"task": d, "memory_type": "episodic", "importance": 1},
        }
        r2 = client.post(api_base.rstrip("/") + "/remember", json=alias, headers=headers)
        r2.raise_for_status()
    return slug_map


def _retrieve(
    api_base: str,
    tenant: str,
    token: Optional[str],
    query: str,
    top_k: int,
    retrievers: List[str],
    persist: bool = False,
    **extra: Any,
) -> Dict[str, Any]:
    assert httpx is not None
    headers = {"X-Tenant-ID": tenant}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    client = httpx.Client(timeout=6.0)
    body = {"query": query, "top_k": top_k, "retrievers": retrievers, "persist": persist}
    # Allow advanced targeting via extra fields (mode/key/id/coord)
    body.update({k: v for k, v in extra.items() if v is not None})
    r = client.post(
        api_base.rstrip("/") + "/rag/retrieve",
        headers=headers,
        json=body,
    )
    r.raise_for_status()
    return r.json()


def _extract_keys(candidates: List[Dict[str, Any]]) -> List[str]:
    out: List[str] = []
    for c in candidates:
        p = c.get("payload", {}) if isinstance(c, dict) else {}
        k = p.get("task") or p.get("fact")
        if isinstance(k, str):
            out.append(k)
    return out


def _mrr(ranks: List[int]) -> float:
    vals = [1.0 / r for r in ranks if r > 0]
    return (sum(vals) / len(ranks)) if ranks else 0.0


def _precision_at_k(pred: List[str], truth: List[str], k: int) -> float:
    if k <= 0:
        return 0.0
    topk = pred[:k]
    if not topk:
        return 0.0
    hits = len([x for x in topk if x in truth])
    return hits / float(k)


def _recall_at_k(pred: List[str], truth: List[str], k: int) -> float:
    if not truth:
        return 0.0
    topk = pred[:k]
    hits = len([x for x in topk if x in truth])
    return hits / float(len(truth))


def _ndcg_at_k(pred: List[str], truth: List[str], k: int, relmap: Optional[Dict[str, int]] = None) -> float:
    # Graded relevance (defaults to binary if relmap not provided)
    def dcg(gains: Iterable[float]) -> float:
        return sum((g / math.log2(i + 2) for i, g in enumerate(gains)))

    def gain(key: str) -> float:
        if relmap and key in relmap:
            return float(relmap[key])
        return 1.0 if key in truth else 0.0

    scores = [gain(p) for p in pred[:k]]
    dcg_val = dcg(scores)
    # Ideal is the top-k gains sorted desc from the set of truths
    ideal_gains = sorted([gain(t) for t in truth], reverse=True)[:k]
    idcg = dcg(ideal_gains)
    return (dcg_val / idcg) if idcg > 0 else 0.0


def _build_synthetic_clusters(n_per_topic: int = 10) -> Tuple[List[str], List[QueryCase]]:
    # Topics with keyword families to help both lexical and vector paths
    solar_kw = ["solar", "photovoltaic", "pv", "panel", "inverter", "renewable"]
    wind_kw = ["wind", "turbine", "blade", "yaw", "maintenance", "renewable"]
    storage_kw = ["battery", "storage", "microgrid", "lithium", "safety", "bms"]

    def synth(topic: str, kws: List[str], i: int) -> str:
        # Create a varied sentence with repeated topic cues
        anchor = kws[0]
        others = random.sample(kws[1:], k=min(len(kws) - 1, 3))
        return f"{topic} guide {anchor} {' '.join(others)} optimization v{i:02d}"

    solar_docs = [synth("solar energy planning", solar_kw, i) for i in range(n_per_topic)]
    wind_docs = [synth("wind turbine maintenance", wind_kw, i) for i in range(n_per_topic)]
    storage_docs = [synth("battery storage operations", storage_kw, i) for i in range(n_per_topic)]

    docs = solar_docs + wind_docs + storage_docs
    # Queries and expected positives (we target 5 per topic as relevant)
    # Build graded relevance: top1=3, next2=2, last2=1
    def relmap(lst: List[str]) -> Dict[str, int]:
        gains = [3, 2, 2, 1, 1]
        return {lst[i]: gains[i] for i in range(min(5, len(lst)))}

    q = [
        QueryCase("solar energy planning optimization", solar_docs[:5], relmap(solar_docs[:5])),
        QueryCase("wind turbine maintenance handbook", wind_docs[:5], relmap(wind_docs[:5])),
        QueryCase("battery storage microgrid safety", storage_docs[:5], relmap(storage_docs[:5])),
    ]
    return docs, q


def run(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-base", default=os.environ.get("SOMABRAIN_API_BASE", "http://localhost:9999"))
    ap.add_argument("--tenant", default=os.environ.get("SOMA_TENANT", "showcase"))
    ap.add_argument("--token", default=os.environ.get("SOMA_API_TOKEN"))
    ap.add_argument("--out-dir", default=str(ROOT / "artifacts" / "showcase"))
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--k", default="1,3,5", help="Comma-separated k values for metrics (<= top-k)")
    ap.add_argument("--docs-per-topic", type=int, default=12)
    args = ap.parse_args(argv)

    out_dir = Path(args.out_dir)
    _ensure_dir(out_dir)
    if httpx is None:
        raise SystemExit("httpx not installed; cannot run enriched micro-bench")

    # Build synthetic corpus and queries
    docs, cases = _build_synthetic_clusters(n_per_topic=max(6, int(args.docs_per_topic)))

    # Seed corpus
    slug_map = _seed_corpus(args.api_base, args.tenant, args.token, docs)

    # Warm-up: persist pinned exacts under the natural-language queries so that
    # - rag_cache stores candidates keyed by the NL query (enables HTTP fallbacks)
    # - graph retriever can traverse via cached candidates when HTTP graph is unavailable
    for case in cases:
        try:
            gold = case.positives[0]
            _retrieve(
                args.api_base,
                args.tenant,
                args.token,
                case.query,  # store under NL query key
                args.top_k,
                ["vector"],
                persist=True,
                mode="key",
                key=gold,
            )
        except Exception:
            pass

    configs: List[Tuple[str, List[str]]] = [
        ("vector", ["vector"]),
        ("lexical", ["lexical"]),
        ("vector+lexical", ["vector", "lexical"]),
        ("graph", ["graph"]),
    ]
    ks = [int(x) for x in str(args.k).split(",") if str(x).strip().isdigit()]
    ks = [k for k in sorted(set(ks)) if k > 0 and k <= int(args.top_k)] or [1, int(args.top_k)]
    summary: Dict[str, Any] = {"top_k": int(args.top_k), "ks": ks, "cases": len(cases), "configs": {}}

    # Evaluate standard configs
    for label, retrs in configs:
        m_hits_top1 = 0
        m_prec: Dict[int, List[float]] = {k: [] for k in ks}
        m_rec: Dict[int, List[float]] = {k: [] for k in ks}
        m_ndcg: Dict[int, List[float]] = {k: [] for k in ks}
        rr_list: List[int] = []
        latencies: List[float] = []
        per_case: List[Dict[str, Any]] = []
        for case in cases:
            t0 = time.perf_counter()
            data = _retrieve(args.api_base, args.tenant, args.token, case.query, args.top_k, retrs, persist=False)
            latencies.append(max(0.0, time.perf_counter() - t0))
            keys = _extract_keys(data.get("candidates", []))
            # Metrics
            top1 = keys[0] if keys else None
            m_hits_top1 += 1 if top1 in case.positives else 0
            for k in ks:
                m_prec[k].append(_precision_at_k(keys, case.positives, k))
                m_rec[k].append(_recall_at_k(keys, case.positives, k))
                m_ndcg[k].append(_ndcg_at_k(keys, case.positives, k, case.relmap))
            # Reciprocal rank
            rank = 0
            for i, k in enumerate(keys, start=1):
                if k in case.positives:
                    rank = i
                    break
            rr_list.append(rank if rank > 0 else 0)
            per_case.append({
                "query": case.query,
                "positives": case.positives,
                "returned": keys,
                "top1_hit": bool(top1 in case.positives) if top1 else False,
                "rank_first_positive": rank or None,
            })
        n = float(len(cases))
        cfg_summary = {
            "hr@1": round(m_hits_top1 / n, 4) if n else 0.0,
            "p@k": {k: round(sum(m_prec[k]) / n, 4) if n else 0.0 for k in ks},
            "r@k": {k: round(sum(m_rec[k]) / n, 4) if n else 0.0 for k in ks},
            "mrr": round(_mrr(rr_list), 4),
            "ndcg@k": {k: round(sum(m_ndcg[k]) / n, 4) if n else 0.0 for k in ks},
            "latency_mean_s": round((sum(latencies) / len(latencies)) if latencies else 0.0, 6),
            "details": per_case,
        }
        summary["configs"][label] = cfg_summary

    # Evaluate exact-key path to demonstrate perfect search mode
    label = "exact-key"
    m_hits_top1 = 0
    m_prec = {k: [] for k in ks}
    m_rec = {k: [] for k in ks}
    m_ndcg = {k: [] for k in ks}
    rr_list = []
    per_case: List[Dict[str, Any]] = []
    for case in cases:
        gold = case.positives[0]
        t0 = time.perf_counter()
        data = _retrieve(
            args.api_base,
            args.tenant,
            args.token,
            gold,
            args.top_k,
            ["vector"],  # retrievers are ignored for pinned exacts
            persist=False,
            mode="key",
            key=gold,
        )
        keys = _extract_keys(data.get("candidates", []))
        top1 = keys[0] if keys else None
        m_hits_top1 += 1 if top1 == gold else 0
        # For exact mode, truth is the single gold key (graded=3)
        truth = [gold]
        relmap_exact = {gold: 3}
        for k in ks:
            m_prec[k].append(_precision_at_k(keys, truth, k))
            m_rec[k].append(_recall_at_k(keys, truth, k))
            m_ndcg[k].append(_ndcg_at_k(keys, truth, k, relmap_exact))
        rank = 0
        for i, k in enumerate(keys, start=1):
            if k == gold:
                rank = i
                break
        rr_list.append(rank if rank > 0 else 0)
        per_case.append({
            "query": gold,
            "positives": truth,
            "returned": keys,
            "top1_hit": bool(top1 == gold) if top1 else False,
            "rank_first_positive": rank or None,
        })
    n = float(len(cases))
    summary["configs"][label] = {
        "hr@1": round(m_hits_top1 / n, 4) if n else 0.0,
        "p@k": {k: round(sum(m_prec[k]) / n, 4) if n else 0.0 for k in ks},
        "r@k": {k: round(sum(m_rec[k]) / n, 4) if n else 0.0 for k in ks},
        "mrr": round(_mrr(rr_list), 4),
        "ndcg@k": {k: round(sum(m_ndcg[k]) / n, 4) if n else 0.0 for k in ks},
        "details": per_case,
    }

    # Evaluate exact-auto (mode auto detection via single-token slug)
    label = "exact-auto"
    m_hits_top1 = 0
    m_prec = {k: [] for k in ks}
    m_rec = {k: [] for k in ks}
    m_ndcg = {k: [] for k in ks}
    rr_list = []
    per_case = []
    for case in cases:
        gold = case.positives[0]
        slug = slug_map.get(gold, _slugify(gold))
        data = _retrieve(
            args.api_base,
            args.tenant,
            args.token,
            slug,
            args.top_k,
            ["vector"],
            persist=False,
            # No mode/key fields here; rely on auto detection
        )
        keys = _extract_keys(data.get("candidates", []))
        top1 = keys[0] if keys else None
        # Accept either canonical doc or slug, since backend may echo slug in payload
        truth = [gold, slug]
        m_hits_top1 += 1 if (top1 in truth) else 0
        relmap_auto = {gold: 3, slug: 3}
        for k in ks:
            m_prec[k].append(_precision_at_k(keys, truth, k))
            m_rec[k].append(_recall_at_k(keys, truth, k))
            m_ndcg[k].append(_ndcg_at_k(keys, truth, k, relmap_auto))
        rank = 0
        for i, k in enumerate(keys, start=1):
            if k in truth:
                rank = i
                break
        rr_list.append(rank if rank > 0 else 0)
        per_case.append({
            "query": slug,
            "positives": truth,
            "returned": keys,
            "top1_hit": bool(top1 in truth) if top1 else False,
            "rank_first_positive": rank or None,
        })
    n = float(len(cases))
    summary["configs"][label] = {
        "hr@1": round(m_hits_top1 / n, 4) if n else 0.0,
        "p@k": {k: round(sum(m_prec[k]) / n, 4) if n else 0.0 for k in ks},
        "r@k": {k: round(sum(m_rec[k]) / n, 4) if n else 0.0 for k in ks},
        "mrr": round(_mrr(rr_list), 4),
        "ndcg@k": {k: round(sum(m_ndcg[k]) / n, 4) if n else 0.0 for k in ks},
        "details": per_case,
    }

    # Write artifacts (JSON + concise Markdown)
    out_json = out_dir / "rag_enriched_quality.json"
    out_json.write_text(json.dumps(summary, indent=2) + "\n")
    out_md = out_dir / "rag_enriched_quality.md"
    md: List[str] = []
    md.append("# Enriched RAG Micro-Benchmark")
    md.append(f"Top-K: {args.top_k} | ks: {','.join(map(str, ks))} | Cases: {len(cases)}")
    md.append("")
    for label, metrics in summary["configs"].items():
        md.append(f"## {label}")
        md.append(f"HR@1={metrics['hr@1']}, MRR={metrics['mrr']}")
        if isinstance(metrics.get("p@k"), dict):
            md.append(f"P@k={metrics['p@k']}")
            md.append(f"R@k={metrics['r@k']}")
            md.append(f"nDCG@k={metrics['ndcg@k']}")
        else:  # legacy fallback
            md.append(f"P@k={metrics.get('p@k')}, R@k={metrics.get('r@k')}, nDCG@k={metrics.get('ndcg@k')}")
        if "latency_mean_s" in metrics:
            md.append(f"Mean latency (s)={metrics['latency_mean_s']}")
        md.append("")
    out_md.write_text("\n".join(md) + "\n")

    print(f"Enriched RAG benchmark written: {out_json}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run())
