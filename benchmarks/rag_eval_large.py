"""
Large-Scale RAG Evaluation (Synthetic)
-------------------------------------

Generates a synthetic corpus (~N docs) across multiple topics, seeds the
in-process app memory, and evaluates several retrieval strategies:

- vector-only
- lexical-only (BM25 when available)
- hybrid (vector+lexical+wm)
- hybrid + rerank (ce)
- graph-only after persisting sessions (learning via links)

Outputs:
- JSON summary at benchmarks/rag_eval_large.json
- PNG plots under benchmarks/plots/
"""

from __future__ import annotations

import argparse
import json
import random
import string
import time
from pathlib import Path
from typing import Dict, List, Tuple

from fastapi.testclient import TestClient

from somabrain import runtime as rt
from somabrain.app import app
from somabrain.config import load_config
from somabrain.services.memory_service import MemoryService


def _noise_words(k: int) -> str:
    base = [
        "analysis",
        "system",
        "model",
        "pipeline",
        "sensor",
        "quantum",
        "neural",
        "vector",
        "graph",
        "signal",
        "control",
        "optimizer",
    ]
    return " ".join(random.choice(base) for _ in range(k))


def _mk_docs(n_docs: int, n_topics: int, seed: int = 13) -> Tuple[List[str], List[str]]:
    random.seed(seed)
    topics = [
        "solar energy",
        "wind turbine",
        "battery storage",
        "photovoltaic inverter",
        "grid optimization",
        "hydrogen fuel",
        "geothermal heat",
        "carbon capture",
        "smart metering",
        "power forecasting",
    ][:n_topics]
    docs: List[str] = []
    labels: List[str] = []
    for i in range(n_docs):
        t = topics[i % len(topics)]
        sent = f"{t} {random.choice(['guide','overview','notes','primer','report'])} {_noise_words(6)}"
        # Add small random suffix to diversify
        suffix = "".join(random.choice(string.ascii_lowercase) for _ in range(3))
        sent = f"{sent} {suffix}"
        docs.append(sent)
        labels.append(t)
    return docs, labels


def _mk_queries(
    topics: List[str], per_topic: int = 5, seed: int = 37
) -> List[Tuple[str, str]]:
    random.seed(seed)
    qs: List[Tuple[str, str]] = []
    for t in topics:
        bases = [
            f"{t} planning",
            f"intro to {t}",
            f"{t} diagnostics",
            f"{t} maintenance",
            f"{t} optimization",
        ]
        for b in bases[:per_topic]:
            qs.append((b, t))
    return qs


def _recall_at_k(candidates: List[dict], truth_topic: str) -> float:
    # A hit if any candidate payload task contains the topic string
    for c in candidates[:5]:
        p = c.get("payload", {}) if isinstance(c, dict) else {}
        t = p.get("task") or p.get("fact") or ""
        if truth_topic in str(t):
            return 1.0
    return 0.0


def run(
    n_docs: int,
    n_topics: int,
    per_topic_q: int,
    tenant: str,
    out_json: Path,
    *,
    expansion: int = 0,
    calibrate: bool = False,
):
    client = TestClient(app)
    headers = {"X-Tenant-ID": tenant}

    # 1) Generate and store docs
    docs, labels = _mk_docs(n_docs, n_topics)
    topics = sorted(set(labels))
    # Prefer direct memory service to avoid rate limiting during bulk ingest
    cfg = load_config()
    ns = f"{cfg.namespace}:{tenant}"
    memsvc = MemoryService(rt.mt_memory, ns) if rt.mt_memory is not None else None
    for d in docs:
        payload = {"task": d, "memory_type": "episodic", "importance": 1}
        ok = False
        if memsvc is not None:
            try:
                memsvc.remember(d, payload)
                ok = True
            except Exception:
                ok = False
        if not ok:
            r = client.post(
                "/remember",
                json={"payload": payload},
                headers=headers,
            )
            assert r.status_code == 200

    # 2) Build queries (truth by matching topic string)
    queries = _mk_queries(topics, per_topic=per_topic_q)

    # Optional: turn on query expansion dynamically by tweaking runtime cfg
    try:
        from somabrain import runtime as _rt

        if _rt.cfg is not None and expansion > 0:
            _rt.cfg.use_query_expansion = True
            _rt.cfg.query_expansion_variants = int(expansion)
    except Exception:
        pass

    strategies = [
        ("vector", {"retrievers": ["vector"], "rerank": None, "persist": False}),
        ("lexical", {"retrievers": ["lexical"], "rerank": None, "persist": False}),
        (
            "hybrid",
            {
                "retrievers": ["vector", "lexical", "wm"],
                "rerank": None,
                "persist": False,
            },
        ),
        (
            "hybrid+ce",
            {
                "retrievers": ["vector", "lexical", "wm"],
                "rerank": "ce",
                "persist": False,
            },
        ),
    ]

    results: Dict[str, Dict[str, float]] = {}
    per_strategy_latency: Dict[str, float] = {}
    per_strategy_hits: Dict[str, float] = {}
    for name, cfg in strategies:
        hits = 0
        lat = 0.0
        for q, truth in queries:
            t1 = time.perf_counter()
            body = {
                "query": q,
                "top_k": 5,
                "retrievers": cfg["retrievers"],
                "persist": bool(cfg.get("persist")),
            }
            if cfg.get("rerank"):
                body["rerank"] = cfg["rerank"]
            r = client.post("/rag/retrieve", headers=headers, json=body)
            assert r.status_code == 200
            lat += time.perf_counter() - t1
            cand = r.json().get("candidates", [])
            hits += _recall_at_k(cand, truth)
        total = len(queries)
        results[name] = {
            "recall@5": hits / float(total),
            "avg_latency_ms": (lat / float(total)) * 1000.0,
        }
        per_strategy_latency[name] = (lat / float(total)) * 1000.0
        per_strategy_hits[name] = hits / float(total)
        # Persist sessions once for graph experiment
        if name == "hybrid":
            for q, _ in queries:
                client.post(
                    "/rag/retrieve",
                    headers=headers,
                    json={
                        "query": q,
                        "top_k": 5,
                        "retrievers": ["vector", "lexical", "wm"],
                        "persist": True,
                    },
                )

    # Graph-only after persistence
    hits = 0
    lat = 0.0
    for q, truth in queries:
        t1 = time.perf_counter()
        r = client.post(
            "/rag/retrieve",
            headers=headers,
            json={"query": q, "top_k": 5, "retrievers": ["graph"], "persist": False},
        )
        assert r.status_code == 200
        lat += time.perf_counter() - t1
        cand = r.json().get("candidates", [])
        hits += _recall_at_k(cand, truth)
    total = len(queries)
    results["graph_after_persist"] = {
        "recall@5": hits / float(total),
        "avg_latency_ms": (lat / float(total)) * 1000.0,
    }

    # Optional simple fusion weights calibration suggestion
    suggested_weights: Dict[str, float] = {}
    if calibrate:
        # normalize recalls of vector and lexical as weights; include wm as smaller share
        rv = float(per_strategy_hits.get("vector", 0.0))
        rl = float(per_strategy_hits.get("lexical", 0.0))
        rw = 0.25  # base for wm
        total = rv + rl + rw if (rv + rl + rw) > 0 else 1.0
        suggested_weights = {
            "vector": rv / total,
            "lexical": rl / total,
            "wm": rw / total,
            "graph": 1.0,  # graph used after persist; not part of first-stage fusion
        }

    out = {
        "meta": {
            "n_docs": n_docs,
            "n_topics": n_topics,
            "per_topic_queries": per_topic_q,
            "tenant": tenant,
            "expansion": expansion,
            "calibrate": calibrate,
        },
        "results": results,
        "suggested_weights": suggested_weights,
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(out, indent=2))

    # Plots
    try:
        import matplotlib.pyplot as plt

        keys = list(results.keys())
        recalls = [results[k]["recall@5"] for k in keys]
        lats = [results[k]["avg_latency_ms"] for k in keys]

        plot_dir = Path("benchmarks/plots")
        plot_dir.mkdir(parents=True, exist_ok=True)

        plt.figure()
        plt.bar(keys, recalls)
        plt.xticks(rotation=20)
        plt.ylabel("Recall@5")
        plt.title("RAG Strategies Recall@5")
        plt.tight_layout()
        plt.savefig(plot_dir / "rag_large_recall.png", dpi=150)
        plt.close()

        plt.figure()
        plt.bar(keys, lats)
        plt.xticks(rotation=20)
        plt.ylabel("Avg Latency (ms)")
        plt.title("RAG Strategies Latency")
        plt.tight_layout()
        plt.savefig(plot_dir / "rag_large_latency.png", dpi=150)
        plt.close()
    except Exception:
        pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--docs", type=int, default=1000)
    p.add_argument("--topics", type=int, default=10)
    p.add_argument("--queries", type=int, default=5)
    p.add_argument("--tenant", type=str, default="raglarge")
    p.add_argument("--out", type=Path, default=Path("benchmarks/rag_eval_large.json"))
    p.add_argument(
        "--expansion", type=int, default=0, help="# of query expansion variants (0=off)"
    )
    p.add_argument(
        "--calibrate", action="store_true", help="Print suggested fusion weights"
    )
    args = p.parse_args()
    run(
        args.docs,
        args.topics,
        args.queries,
        args.tenant,
        args.out,
        expansion=args.expansion,
        calibrate=args.calibrate,
    )


if __name__ == "__main__":
    main()
