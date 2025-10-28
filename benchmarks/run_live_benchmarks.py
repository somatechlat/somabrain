#!/usr/bin/env python3
"""Run live benchmarks in multiple passes and generate plots.

- Runs recall latency at increasing N and fixed Q, TOPK
- Runs RAG live bench once
- Writes all artifacts to benchmarks/outputs/live_runs/<timestamp>/

Usage:
  PYTHONPATH=. python benchmarks/run_live_benchmarks.py \
    --recall-api-url http://127.0.0.1:9999 \
    --rag-api-url http://127.0.0.1:9999 \
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
    rag_api_url: str
    passes: List[int]
    q: int
    topk: int


def _run_recall_once(api_url: str, N: int, Q: int, TOPK: int, env: dict[str, str]) -> Tuple[int, dict]:
    e = os.environ.copy()
    e.update(env)
    e["SOMA_API_URL"] = api_url
    e["BENCH_N"] = str(N)
    e["BENCH_Q"] = str(Q)
    e["BENCH_TOPK"] = str(TOPK)
    # Run recall_latency_bench and capture JSON output
    out = subprocess.check_output([
        "python", "benchmarks/recall_latency_bench.py"
    ], env=e).decode()
    data = json.loads(out)
    return (N, data)


def _run_rag_live_once(api_url: str, out_file: Path, env: dict[str, str]) -> None:
    e = os.environ.copy()
    e.update(env)
    cmd = [
        "python",
        "benchmarks/rag_live_bench.py",
        "--api-url", api_url,
        "--output", str(out_file),
    ]
    subprocess.check_call(cmd, env=e)


def _ensure_matplotlib() -> bool:
    try:
        import matplotlib  # noqa: F401
        return True
    except Exception:
        return False


def _plot_curves(passes: List[int], vals: List[float], ylabel: str, title: str, out: Path) -> None:
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
    ap = argparse.ArgumentParser(description="Run multi-pass live benchmarks and plot results")
    ap.add_argument("--recall-api-url", default=os.getenv("SOMA_API_URL", "http://127.0.0.1:9999"))
    ap.add_argument("--rag-api-url", default=os.getenv("SOMABRAIN_API_URL", "http://127.0.0.1:9696"))
    ap.add_argument("--start", type=int, default=100)
    ap.add_argument("--end", type=int, default=1000)
    ap.add_argument("--passes", type=int, default=5)
    ap.add_argument("--q", type=int, default=50)
    ap.add_argument("--topk", type=int, default=3)
    ap.add_argument("--out-dir", type=Path, default=Path("benchmarks/outputs/live_runs"))
    ap.add_argument("--n-list", type=str, default="", help="Comma-separated explicit N list (overrides start/end/passes)")
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
    for N in passes:
        print(f"[run] recall_latency_bench N={N} Q={args.q} TOPK={args.topk} @ {args.recall_api_url}")
        try:
            _, data = _run_recall_once(args.recall_api_url, N, args.q, args.topk, env)
        except subprocess.CalledProcessError as e:
            print(f"ERROR: recall bench failed for N={N}: {e}")
            data = {"n_remember": 0, "n_recall": 0, "p50_remember_ms": 0, "p95_remember_ms": 0, "p50_recall_ms": 0, "p95_recall_ms": 0, "errors": 1}
        # Save raw
        (run_dir / f"recall_N{N}.json").write_text(json.dumps(data, indent=2))
        summaries.append(RecallSummary(
            N=N,
            Q=args.q,
            TOPK=args.topk,
            p50_remember_ms=float(data.get("p50_remember_ms", 0.0)),
            p95_remember_ms=float(data.get("p95_remember_ms", 0.0)),
            p50_recall_ms=float(data.get("p50_recall_ms", 0.0)),
            p95_recall_ms=float(data.get("p95_recall_ms", 0.0)),
            errors=int(data.get("errors", 0)),
        ))

    # Run RAG live once (use recall API URL if rag is not reachable separately)
    rag_out = run_dir / "rag_live_results.json"
    rag_api = args.rag_api_url or args.recall_api_url
    print(f"[run] rag_live_bench @ {rag_api}")
    try:
        _run_rag_live_once(rag_api, rag_out, env)
    except subprocess.CalledProcessError as e:
        print(f"WARN: rag live bench failed: {e}; continuing without RAG results")

    # Save combined summary
    combined = {
        "recall_summaries": [asdict(s) for s in summaries],
    }
    (run_dir / "summary.json").write_text(json.dumps(combined, indent=2))

    # Plots
    if _ensure_matplotlib():
        Ns = [s.N for s in summaries]
        _plot_curves(Ns, [s.p50_remember_ms for s in summaries], "p50 remember (ms)", "Remember p50 vs N", run_dir / "remember_p50_vs_N.png")
        _plot_curves(Ns, [s.p95_remember_ms for s in summaries], "p95 remember (ms)", "Remember p95 vs N", run_dir / "remember_p95_vs_N.png")
        _plot_curves(Ns, [s.p50_recall_ms for s in summaries], "p50 recall (ms)", "Recall p50 vs N", run_dir / "recall_p50_vs_N.png")
        _plot_curves(Ns, [s.p95_recall_ms for s in summaries], "p95 recall (ms)", "Recall p95 vs N", run_dir / "recall_p95_vs_N.png")
    else:
        print("Note: matplotlib not installed; plots skipped. Install it to get PNGs.")

    # Provenance
    prov = Provenance(
        timestamp=ts,
        recall_api_url=args.recall_api_url,
        rag_api_url=rag_api,
        passes=passes,
        q=args.q,
        topk=args.topk,
    )
    (run_dir / "provenance.json").write_text(json.dumps(asdict(prov), indent=2))

    print(f"Artifacts written to {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
