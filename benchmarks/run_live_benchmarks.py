#!/usr/bin/env python3
"""Run live benchmarks in multiple passes and generate plots.

- Runs recall latency at increasing N and fixed Q, TOPK
- Runs Recall live bench once
- Writes all artifacts to benchmarks/outputs/live_runs/<timestamp>/

Usage:
    PYTHONPATH=. python benchmarks/run_live_benchmarks.py \
        --recall-api-url http://127.0.0.1:9696 \
    --start 100 --end 1000 --passes 5 \
    --q 50 --topk 3 \
    --out-dir benchmarks/outputs/live_runs
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Tuple


@dataclass
class RecallSummary:
    N: int
    Q: int
    TOPK: int
    p50_remember_ms: float
    p95_remember_ms: float
    p50_recall_ms: float
    p95_recall_ms: float
    errors: int


@dataclass
class Provenance:
    timestamp: str
    recall_api_url: str
    # Unified recall only
    passes: List[int]
    q: int
    topk: int


def _run_recall_once(
    api_url: str, N: int, Q: int, TOPK: int, env: dict[str, str]
) -> Tuple[int, dict]:
    e = os.environ.copy()
    e.update(env)
    e["SOMA_API_URL"] = api_url
    e["BENCH_N"] = str(N)
    e["BENCH_Q"] = str(Q)
    e["BENCH_TOPK"] = str(TOPK)
    # Run recall_latency_bench and capture JSON output
    out = subprocess.check_output(
        ["python", "benchmarks/recall_latency_bench.py"], env=e
    ).decode()
    data = json.loads(out)
    return (N, data)


def _run_recall_live_once(api_url: str, out_file: Path, env: dict[str, str]) -> None:
    e = os.environ.copy()
    e.update(env)
    cmd = [
        "python",
        "benchmarks/recall_live_bench.py",
        "--api-url",
        api_url,
        "--output",
        str(out_file),
    ]
    subprocess.check_call(cmd, env=e)


def _ensure_matplotlib() -> bool:
    try:
        import matplotlib  # noqa: F401

        return True
    except Exception:
        return False


def _scrape_metrics_text(api_url: str) -> str:
    import urllib.request

    with urllib.request.urlopen(api_url.rstrip("/") + "/metrics", timeout=5) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _metric_value(
    text: str, metric: str, match_labels: dict[str, str] | None = None
) -> float:
    """Parse Prometheus text exposition and extract a counter/gauge value.

    This is a minimal parser using string checks to avoid extra deps.
    For Counters, Prometheus exports as <name>_total; call with that exact name.
    """
    match_labels = match_labels or {}
    want = metric.strip()
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        if not line.startswith(want):
            continue
        # Example: somabrain_http_requests_total{method="POST",path="/remember",status="200"} 123
        try:
            name_and_labels, value = line.split(None, 1)
        except ValueError:
            continue
        if "{" in name_and_labels and "}" in name_and_labels:
            name, raw_labels = name_and_labels.split("{", 1)
            raw_labels = raw_labels.rsplit("}", 1)[0]
            labels = {}
            for part in raw_labels.split(","):
                if "=" in part:
                    k, v = part.split("=", 1)
                    labels[k.strip()] = v.strip().strip('"')
            ok = all(labels.get(k) == v for k, v in match_labels.items())
            if not ok:
                continue
        try:
            return float(value.strip())
        except Exception:
            pass
    return 0.0


def _health_snapshot(api_url: str) -> dict:
    import json as _json
    import urllib.request

    try:
        with urllib.request.urlopen(api_url.rstrip("/") + "/health", timeout=5) as resp:
            return _json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return {"ok": False}


def _plot_curves(
    passes: List[int], vals: List[float], ylabel: str, title: str, out: Path
) -> None:
    try:
        import os

        os.environ.setdefault("MPLBACKEND", "Agg")
        import matplotlib.pyplot as plt  # type: ignore

        plt.figure(figsize=(7, 4))
        plt.plot(passes, vals, marker="o")
        plt.xlabel("N (memories)")
        plt.ylabel(ylabel)
        plt.title(title)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(out, dpi=150)
        plt.close()
    except Exception as e:
        print(f"Plotting skipped: {e}")


def _linspace_int(start: int, end: int, count: int) -> List[int]:
    if count <= 1:
        return [end]
    step = (end - start) / float(count - 1)
    out = []
    for i in range(count):
        out.append(int(round(start + i * step)))
    # Ensure the last is exactly end
    out[-1] = end
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Run multi-pass live benchmarks and plot results"
    )
    ap.add_argument(
        "--recall-api-url", default=os.getenv("SOMA_API_URL", "http://127.0.0.1:9696")
    )
    ap.add_argument("--start", type=int, default=100)
    ap.add_argument("--end", type=int, default=1000)
    ap.add_argument("--passes", type=int, default=5)
    ap.add_argument("--q", type=int, default=50)
    ap.add_argument("--topk", type=int, default=3)
    ap.add_argument(
        "--out-dir", type=Path, default=Path("benchmarks/outputs/live_runs")
    )
    ap.add_argument(
        "--n-list",
        type=str,
        default="",
        help="Comma-separated explicit N list (overrides start/end/passes)",
    )
    args = ap.parse_args()

    # Build pass list
    if args.n_list:
        passes = [int(x.strip()) for x in args.n_list.split(",") if x.strip()]
    else:
        passes = _linspace_int(args.start, args.end, args.passes)

    # Output folder with timestamp
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = args.out_dir / ts
    run_dir.mkdir(parents=True, exist_ok=True)

    env = {}

    # Run recall passes
    summaries: List[RecallSummary] = []
    # Pre-metrics snapshot (HTTP counters) and health
    try:
        m_before = _scrape_metrics_text(args.recall_api_url)
    except Exception:
        m_before = ""
    h_before = _health_snapshot(args.recall_api_url)
    for N in passes:
        print(
            f"[run] recall_latency_bench N={N} Q={args.q} TOPK={args.topk} @ {args.recall_api_url}"
        )
        try:
            _, data = _run_recall_once(args.recall_api_url, N, args.q, args.topk, env)
        except subprocess.CalledProcessError as e:
            print(f"ERROR: recall bench failed for N={N}: {e}")
            data = {
                "n_remember": 0,
                "n_recall": 0,
                "p50_remember_ms": 0,
                "p95_remember_ms": 0,
                "p50_recall_ms": 0,
                "p95_recall_ms": 0,
                "errors": 1,
            }
        # Save raw
        (run_dir / f"recall_N{N}.json").write_text(json.dumps(data, indent=2))
        summaries.append(
            RecallSummary(
                N=N,
                Q=args.q,
                TOPK=args.topk,
                p50_remember_ms=float(data.get("p50_remember_ms", 0.0)),
                p95_remember_ms=float(data.get("p95_remember_ms", 0.0)),
                p50_recall_ms=float(data.get("p50_recall_ms", 0.0)),
                p95_recall_ms=float(data.get("p95_recall_ms", 0.0)),
                errors=int(data.get("errors", 0)),
            )
        )

    # Run Recall live once
    recall_out = run_dir / "recall_live_results.json"
    print(f"[run] recall_live_bench @ {args.recall_api_url}")
    try:
        _run_recall_live_once(args.recall_api_url, recall_out, env)
    except subprocess.CalledProcessError as e:
        print(f"WARN: recall live bench failed: {e}; continuing without recall results")

    # Post-metrics snapshot and health
    try:
        m_after = _scrape_metrics_text(args.recall_api_url)
    except Exception:
        m_after = ""
    h_after = _health_snapshot(args.recall_api_url)

    # Compute HTTP counter deltas for /remember and /recall
    http_remember_before = (
        _metric_value(m_before, "somabrain_http_requests_total", {"path": "/remember"})
        if m_before
        else 0.0
    )
    http_recall_before = (
        _metric_value(m_before, "somabrain_http_requests_total", {"path": "/recall"})
        if m_before
        else 0.0
    )
    http_remember_after = (
        _metric_value(m_after, "somabrain_http_requests_total", {"path": "/remember"})
        if m_after
        else 0.0
    )
    http_recall_after = (
        _metric_value(m_after, "somabrain_http_requests_total", {"path": "/recall"})
        if m_after
        else 0.0
    )
    metrics_delta = {
        "http_remember_total_delta": max(
            0.0, http_remember_after - http_remember_before
        ),
        "http_recall_total_delta": max(0.0, http_recall_after - http_recall_before),
        "before": {"remember": http_remember_before, "recall": http_recall_before},
        "after": {"remember": http_remember_after, "recall": http_recall_after},
    }
    (run_dir / "metrics_deltas.json").write_text(json.dumps(metrics_delta, indent=2))

    # Save combined summary
    combined = {
        "recall_summaries": [asdict(s) for s in summaries],
        "health_before": h_before,
        "health_after": h_after,
    }
    (run_dir / "summary.json").write_text(json.dumps(combined, indent=2))

    # Plots
    if _ensure_matplotlib():
        Ns = [s.N for s in summaries]
        _plot_curves(
            Ns,
            [s.p50_remember_ms for s in summaries],
            "p50 remember (ms)",
            "Remember p50 vs N",
            run_dir / "remember_p50_vs_N.png",
        )
        _plot_curves(
            Ns,
            [s.p95_remember_ms for s in summaries],
            "p95 remember (ms)",
            "Remember p95 vs N",
            run_dir / "remember_p95_vs_N.png",
        )
        _plot_curves(
            Ns,
            [s.p50_recall_ms for s in summaries],
            "p50 recall (ms)",
            "Recall p50 vs N",
            run_dir / "recall_p50_vs_N.png",
        )
        _plot_curves(
            Ns,
            [s.p95_recall_ms for s in summaries],
            "p95 recall (ms)",
            "Recall p95 vs N",
            run_dir / "recall_p95_vs_N.png",
        )
    else:
        print("Note: matplotlib not installed; plots skipped. Install it to get PNGs.")

    # Provenance
    prov = Provenance(
        timestamp=ts,
        recall_api_url=args.recall_api_url,
        passes=passes,
        q=args.q,
        topk=args.topk,
    )
    (run_dir / "provenance.json").write_text(json.dumps(asdict(prov), indent=2))

    print(f"Artifacts written to {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
