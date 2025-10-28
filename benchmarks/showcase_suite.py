"""
Showcase Benchmark Suite
------------------------

Runs a fast, end-to-end smoke of the live API and collects artifacts:
- Latency/throughput on a lightweight endpoint
- Optional RAG-quality micro-bench against the API
- Metrics scrape from /metrics (Prometheus exposition)
- JSON summary and optional PNG plots (if matplotlib is available)
- Markdown report aggregating results and linking artifacts

Usage (examples):
  python -m benchmarks.showcase_suite --api-base http://localhost:9999 \
      --out-dir artifacts/showcase --requests 100 --concurrency 20

  python -m benchmarks.showcase_suite --dry-run --out-dir artifacts/showcase

Notes:
- Plotting is optional; if matplotlib is not installed, plots are skipped.
- All network interactions have short timeouts and fail-soft; errors are captured in the report.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import httpx
except Exception:  # pragma: no cover - handled by tests via dry-run
    httpx = None  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_ROOT = ROOT / "artifacts" / "showcase"


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _percentile(values: List[float], q: float) -> float:
    if not values:
        return float("nan")
    # simple nearest-rank percentile
    idx = max(0, min(len(values) - 1, int(math.ceil(q * len(values)) - 1)))
    return sorted(values)[idx]


async def _latency_smoke(
    api_base: str,
    count: int,
    concurrency: int,
    timeout_s: float = 2.0,
    endpoint: str = "/health",
) -> Dict[str, Any]:
    """Hit a lightweight endpoint concurrently and measure latencies.

    Returns a dict with summary stats and samples.
    """
    if httpx is None:
        raise RuntimeError("httpx is not available; install httpx or use --dry-run")

    sem = asyncio.Semaphore(concurrency)
    latencies: List[float] = []
    failures: List[str] = []

    async def one(idx: int) -> None:
        url = api_base.rstrip("/") + endpoint
        async with sem:
            t0 = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=timeout_s) as client:
                    r = await client.get(url)
                    r.raise_for_status()
            except Exception as e:  # noqa: BLE001
                failures.append(f"{idx}:{type(e).__name__}:{e}")
            finally:
                latencies.append(time.perf_counter() - t0)

    await asyncio.gather(*(one(i) for i in range(count)))

    mean = statistics.fmean(latencies) if latencies else float("nan")
    p50 = _percentile(latencies, 0.50)
    p90 = _percentile(latencies, 0.90)
    p99 = _percentile(latencies, 0.99)

    return {
        "endpoint": endpoint,
        "requests": count,
        "concurrency": concurrency,
        "mean_s": mean,
        "p50_s": p50,
        "p90_s": p90,
        "p99_s": p99,
        "failures": failures,
        "samples_s": latencies[: min(1000, len(latencies))],  # cap to keep JSON small
    }


def _rag_quality_http(api_base: str, tenant: str = "showcase", token: Optional[str] = None) -> Dict[str, Any]:
    """Minimal RAG quality smoke against the live API.

    Seeds a tiny corpus via /remember and measures hit-rate on unified /recall variants.
    """
    if httpx is None:
        raise RuntimeError("httpx is not available; install httpx or disable --rag")

    headers = {"X-Tenant-ID": tenant}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    client = httpx.Client(timeout=5.0)

    def _remember(task: str, *, tenant_id: str) -> None:
        # Memory API contract requires tenant/namespace/key/value
        body = {
            "tenant": tenant_id,
            "namespace": "ltm",
            "key": task,
            "value": {"task": task, "memory_type": "episodic", "importance": 1},
        }
        r = client.post(
            api_base.rstrip("/") + "/remember",
            json=body,
            headers=headers,
        )
        r.raise_for_status()

    def _hit_rate(candidates: List[dict], truths: List[str]) -> float:
        got = set()
        for c in candidates:
            p = c.get("payload", {})
            t = p.get("task") or p.get("fact")
            if t:
                got.add(str(t))
        truths = [str(x) for x in truths]
        if not truths:
            return 0.0
        return len([t for t in truths if t in got]) / float(len(truths))

    # Seed small corpus
    docs = [
        "solar energy optimization with panels",
        "wind turbine maintenance guide",
        "battery storage for solar microgrids",
        "photovoltaic inverter diagnostics",
        "intro to renewable energy planning",
    ]
    for d in docs:
        _remember(d, tenant_id=tenant)

    query = "solar energy planning"
    top_k = 5

    def _retrieve(retrievers: List[str], persist: bool) -> tuple[float, Dict[str, Any]]:
        t0 = time.perf_counter()
        r = client.post(
            api_base.rstrip("/") + "/recall",
            headers=headers,
            json={"query": query, "top_k": top_k, "retrievers": retrievers, "persist": persist},
        )
        dt = time.perf_counter() - t0
        r.raise_for_status()
        return dt, r.json()

    dt0, data0 = _retrieve(["vector"], False)
    hr0 = _hit_rate(data0.get("results", []), [docs[0], docs[2]])

    dt1, data1 = _retrieve(["vector", "wm"], True)
    hr1 = _hit_rate(data1.get("results", []), [docs[0], docs[2]])

    dt2, data2 = _retrieve(["graph"], False)
    hr2 = _hit_rate(data2.get("results", []), [docs[0], docs[2]])

    return {
        "baseline_vector_latency_s": round(dt0, 6),
        "baseline_vector_hit_rate": hr0,
        "persist_mix_latency_s": round(dt1, 6),
        "persist_mix_hit_rate": hr1,
        "post_persist_graph_latency_s": round(dt2, 6),
        "post_persist_graph_hit_rate": hr2,
    }


def _scrape_metrics_text(metrics_url: str, timeout_s: float = 2.0) -> Dict[str, float]:
    """Scrape Prometheus text exposition from a /metrics endpoint.

    Returns a minimal dict of somabrain_* metric values (no labels aggregated).
    """
    out: Dict[str, float] = {}
    if httpx is None:
        return out
    try:
        r = httpx.get(metrics_url, timeout=timeout_s)
        r.raise_for_status()
        for line in r.text.splitlines():
            # skip HELP/TYPE/comments
            if not line or line.startswith("#"):
                continue
            # only capture simple counters without labels, or gauge-obvious lines
            if line.startswith("somabrain_") or line.startswith("http_server_requests_"):
                # strip labels: metric{...} value
                try:
                    metric_part, val_part = line.split(" ", 1)
                    name = metric_part.split("{", 1)[0]
                    val = float(val_part.strip())
                    out[name] = val
                except Exception:  # noqa: BLE001
                    continue
    except Exception:
        # fail-soft
        return out
    return out


def _maybe_plot_latency(latencies: List[float], out_png: Path) -> Optional[str]:
    try:
        import matplotlib.pyplot as plt  # type: ignore

        plt.figure(figsize=(6, 3))
        plt.plot([x * 1000.0 for x in latencies], marker=".", linestyle="none", alpha=0.6)
        plt.title("Latency samples (ms)")
        plt.xlabel("request index")
        plt.ylabel("latency (ms)")
        plt.tight_layout()
        plt.savefig(out_png)
        plt.close()
        return out_png.name
    except Exception:
        return None


def _maybe_plot_latency_hist(latencies: List[float], out_png: Path) -> Optional[str]:
    try:
        import matplotlib.pyplot as plt  # type: ignore

        plt.figure(figsize=(6, 3))
        ms = [x * 1000.0 for x in latencies]
        plt.hist(ms, bins=20, color="#2196F3", alpha=0.8)
        plt.title("Latency histogram (ms)")
        plt.xlabel("latency (ms)")
        plt.ylabel("count")
        plt.tight_layout()
        plt.savefig(out_png)
        plt.close()
        return out_png.name
    except Exception:
        return None


def _fetch_diagnostics(api_base: str, timeout_s: float = 2.0) -> Dict[str, Any]:
    if httpx is None:
        return {}
    try:
        r = httpx.get(api_base.rstrip("/") + "/diagnostics", timeout=timeout_s)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True))


def _write_report_md(out_dir: Path, latency: Dict[str, Any], rag: Optional[Dict[str, Any]], metrics: Dict[str, float], latency_plot: Optional[str], latency_hist: Optional[str], diagnostics: Dict[str, Any], math_panels: List[str]) -> None:
    md = ["# Somabrain Showcase Report", ""]
    if diagnostics:
        md.append("## Wiring proof (/diagnostics)")
        # Extract a few salient fields if present
        mode = diagnostics.get("mode")
        req_backends = diagnostics.get("external_backends_required")
        mem_ep = diagnostics.get("memory_endpoint") or diagnostics.get("memory", {}).get("endpoint")
        embedder = diagnostics.get("embedder")
        predictor = diagnostics.get("predictor_provider") or diagnostics.get("predictor")
        md.append(f"Mode: {mode}")
        if req_backends is not None:
            md.append(f"External backends required: {req_backends}")
        if mem_ep:
            md.append(f"Memory endpoint: {mem_ep}")
        if predictor:
            md.append(f"Predictor: {predictor}")
        if embedder:
            md.append(f"Embedder: {embedder}")
        md.append("Evidence of no mocks: external_backends_required should be true; memory endpoint should not be 127.0.0.1 inside containers; OPA decisions present in metrics.")

    md.append("## Latency smoke")
    md.append(f"Requests: {latency.get('requests')} | Concurrency: {latency.get('concurrency')} | Endpoint: {latency.get('endpoint')}")
    md.append(
        f"Mean: {latency.get('mean_s'):.4f}s | p50: {latency.get('p50_s'):.4f}s | p90: {latency.get('p90_s'):.4f}s | p99: {latency.get('p99_s'):.4f}s"
    )
    fails = latency.get("failures") or []
    if fails:
        md.append(f"Failures: {len(fails)} (first: {fails[0]})")
    if latency_plot:
        md.append("")
        md.append(f"![Latency]({latency_plot})")
    if latency_hist:
        md.append("")
        md.append(f"![Latency Histogram]({latency_hist})")

    if rag is not None:
        md.append("")
        md.append("## RAG quality (micro)")
        if isinstance(rag, dict) and "error" in rag:
            md.append(f"RAG micro-bench failed: {rag['error']}")
        else:
            md.append(
                f"Baseline vector: {rag['baseline_vector_hit_rate']:.2f} HR in {rag['baseline_vector_latency_s']:.3f}s"
            )
            md.append(
                f"Persist mix: {rag['persist_mix_hit_rate']:.2f} HR in {rag['persist_mix_latency_s']:.3f}s"
            )
            md.append(
                f"Post-persist graph: {rag['post_persist_graph_hit_rate']:.2f} HR in {rag['post_persist_graph_latency_s']:.3f}s"
            )

    if metrics:
        md.append("")
        md.append("## Metrics snapshot (/metrics)")
        top = list(sorted(metrics.items()))[:20]
        for k, v in top:
            md.append(f"- {k}: {v}")

    if math_panels:
        md.append("")
        md.append("## Math panels")
        for p in math_panels:
            md.append(f"![{Path(p).stem}]({p})")

    (out_dir / "showcase_report.md").write_text("\n".join(md) + "\n")


def run(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-base", default=os.environ.get("SOMABRAIN_API_BASE", "http://localhost:9999"))
    ap.add_argument("--out-dir", default=str(ARTIFACTS_ROOT))
    ap.add_argument("--requests", type=int, default=100)
    ap.add_argument("--concurrency", type=int, default=20)
    ap.add_argument("--timeout", type=float, default=2.0)
    ap.add_argument("--no-rag", action="store_true", help="Skip RAG micro-bench")
    ap.add_argument("--tenant", default=os.environ.get("SOMA_TENANT", "showcase"))
    ap.add_argument("--token", default=os.environ.get("SOMA_API_TOKEN"))
    ap.add_argument("--dry-run", action="store_true", help="Do not call network; emit synthetic data")
    args = ap.parse_args(argv)

    out_dir = Path(args.out_dir)
    _ensure_dir(out_dir)

    # Latency smoke
    if args.dry_run:
        latencies = [0.010 + 0.002 * math.sin(i / 5.0) for i in range(args.requests)]
        latency = {
            "endpoint": "/health",
            "requests": args.requests,
            "concurrency": args.concurrency,
            "mean_s": statistics.fmean(latencies),
            "p50_s": _percentile(latencies, 0.50),
            "p90_s": _percentile(latencies, 0.90),
            "p99_s": _percentile(latencies, 0.99),
            "failures": [],
            "samples_s": latencies[:1000],
        }
    else:
        latency = asyncio.run(
            _latency_smoke(
                api_base=args.api_base,
                count=args.requests,
                concurrency=args.concurrency,
                timeout_s=args.timeout,
            )
        )
    _write_json(out_dir / "latency.json", latency)

    # Optional plot
    samples = list(latency.get("samples_s", []))
    latency_plot = _maybe_plot_latency(samples, out_dir / "latency.png")
    latency_hist = _maybe_plot_latency_hist(samples, out_dir / "latency_hist.png")

    # RAG micro quality
    rag: Optional[Dict[str, Any]] = None
    if not args.no_rag:
        if args.dry_run:
            rag = {
                "baseline_vector_latency_s": 0.012,
                "baseline_vector_hit_rate": 0.50,
                "persist_mix_latency_s": 0.020,
                "persist_mix_hit_rate": 0.75,
                "post_persist_graph_latency_s": 0.008,
                "post_persist_graph_hit_rate": 0.50,
            }
        else:
            try:
                rag = _rag_quality_http(args.api_base, tenant=args.tenant, token=args.token)
                _write_json(out_dir / "rag_quality.json", rag)
            except Exception as e:  # noqa: BLE001
                rag = {"error": f"{type(e).__name__}: {e}"}
                _write_json(out_dir / "rag_quality.error.json", rag)

    # Diagnostics and Metrics snapshot from live API
    diagnostics: Dict[str, Any] = {}
    if not args.dry_run:
        diagnostics = _fetch_diagnostics(args.api_base)
        if diagnostics:
            _write_json(out_dir / "diagnostics.json", diagnostics)

    # Metrics snapshot from /metrics
    metrics: Dict[str, float] = {}
    if not args.dry_run:
        metrics = _scrape_metrics_text(args.api_base.rstrip("/") + "/metrics")
        if metrics:
            _write_json(out_dir / "metrics_snapshot.json", metrics)

    # Auto-include math panels from benchmarks directory
    math_panels: List[str] = []
    try:
        bench_dir = ROOT / "benchmarks"
        for name in [
            "cognition_cosine.png",
            "cognition_unbind_p99.png",
            "colored_noise_D512.png",
            "colored_noise_D1024.png",
            "nulling_D512.png",
            "nulling_D1024.png",
        ]:
            p = bench_dir / name
            if p.exists():
                # Link relative to report directory using relative path from out_dir
                rel = os.path.relpath(p, out_dir)
                math_panels.append(rel)
    except Exception:
        pass

    # Markdown report
    _write_report_md(out_dir, latency, rag, metrics, latency_plot, latency_hist, diagnostics, math_panels)

    print(f"Showcase artifacts written to: {out_dir}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run())
