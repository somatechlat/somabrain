#!/usr/bin/env python3
"""Render a Markdown report for a live benchmark run folder.

Usage:
  python benchmarks/render_run_report.py --run-dir benchmarks/outputs/live_runs/<timestamp>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, List


def _read_json(p: Path) -> Any:
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception as exc: raise
        return None


def render(run_dir: Path) -> int:
    summ = _read_json(run_dir / "summary.json") or {}
    deltas = _read_json(run_dir / "metrics_deltas.json") or {}
    recall = _read_json(run_dir / "recall_live_results.json") or {}

    md: List[str] = []
    md.append(f"# Live Benchmark Report — {run_dir.name}")

    # Health snapshots
    hb = summ.get("health_before") or {}
    ha = summ.get("health_after") or {}
    if hb or ha:
        md.append("\n## Health snapshots")
        md.append("- Before: " + (json.dumps(hb) if hb else "n/a"))
        md.append("- After:  " + (json.dumps(ha) if ha else "n/a"))

    # Metrics deltas
    if deltas:
        md.append("\n## HTTP metrics deltas (no-mock proof)")
        md.append("- /remember delta: " + str(deltas.get("http_remember_total_delta")))
        md.append("- /recall delta:   " + str(deltas.get("http_recall_total_delta")))

    # Recall summaries table
    recs = summ.get("recall_summaries") or []
    if recs:
        md.append("\n## Recall latency vs N")
        md.append(
            "N | p50 remember (ms) | p95 remember (ms) | p50 recall (ms) | p95 recall (ms) | errors"
        )
        md.append("--:|--:|--:|--:|--:|--:")
        for r in recs:
            md.append(
                f"{r['N']} | {r['p50_remember_ms']:.2f} | {r['p95_remember_ms']:.2f} | {r['p50_recall_ms']:.2f} | {r['p95_recall_ms']:.2f} | {r['errors']}"
            )
        # Plot links
        for img in [
            "remember_p50_vs_N.png",
            "remember_p95_vs_N.png",
            "recall_p50_vs_N.png",
            "recall_p95_vs_N.png",
        ]:
            p = run_dir / img
            if p.exists():
                md.append(f"\n![{img}]({img})")

    # Recall live results
    if recall:
        md.append("\n## Recall live benchmark")
        md.append("- api_url: " + str(recall.get("api_url")))
        wl = recall.get("write_latency_s") or {}
        if wl:
            md.append(f"- write avg: {wl.get('avg')}, p95: {wl.get('p95')}")
        for key in ("vector", "mix", "graph"):
            sec = recall.get(key)
            if sec:
                md.append(
                    f"- {key}: latency_s={sec.get('latency_s')}, hit_rate={sec.get('hit_rate')}"
                )

    out = run_dir / "report.md"
    out.write_text("\n".join(md))
    print(f"Wrote {out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", type=Path, required=True)
    args = ap.parse_args()
    return render(args.run_dir)


if __name__ == "__main__":
    raise SystemExit(main())
