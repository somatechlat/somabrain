#!/usr/bin/env python3
"""CLI to assert SomaBrain governance upgrades improve core metrics.

The script compares a baseline benchmark JSON report with a candidate report
and enforces non-regression on accuracy and latency figures. It is intentionally
simple so it can run in CI without additional dependencies.

Expected JSON shape::

    {
        "metrics": {
            "top1_accuracy": 0.92,
            "cosine_margin": 0.13,
            "recall_latency_p95": 0.085
        }
    }

Keys can appear at any nesting level; the loader searches recursively for the
following metric aliases:

- top-1 accuracy: ``top1_accuracy``, ``top1``, ``recall_top1``
- cosine margin: ``cosine_margin``, ``margin``
- recall latency: ``recall_latency_p95``, ``latency_p95``, ``recall_latency``

Usage::

    python scripts/prove_enhancement.py \
        --baseline benchmarks/results_baseline.json \
        --candidate benchmarks/results_full.json

The script exits with a non-zero status code when the candidate fails to meet or
exceed the baseline on accuracy/margin, or when latency regresses beyond the
configured tolerance.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

TOP1_KEYS = ("top1_accuracy", "top1", "recall_top1")
MARGIN_KEYS = ("cosine_margin", "margin", "margin_mean")
LATENCY_KEYS = ("recall_latency_p95", "latency_p95", "recall_latency")


def _load_json(path: Path) -> Dict[str, Any]:
    """Execute load json.

    Args:
        path: The path.
    """

    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError as exc:  # pragma: no cover - CLI guard
        raise SystemExit(f"missing benchmark file: {path}") from exc
    except json.JSONDecodeError as exc:  # pragma: no cover - CLI guard
        raise SystemExit(f"invalid JSON in {path}: {exc}") from exc


def _find_metric(blob: Any, keys: Iterable[str]) -> Optional[float]:
    """Execute find metric.

    Args:
        blob: The blob.
        keys: The keys.
    """

    if isinstance(blob, dict):
        for name in keys:
            if name in blob and isinstance(blob[name], (int, float)):
                return float(blob[name])
        for value in blob.values():
            found = _find_metric(value, keys)
            if found is not None:
                return found
    elif isinstance(blob, list):
        for item in blob:
            found = _find_metric(item, keys)
            if found is not None:
                return found
    return None


def _extract_metrics(data: Dict[str, Any]) -> Dict[str, float]:
    """Execute extract metrics.

    Args:
        data: The data.
    """

    metrics: Dict[str, float] = {}
    top1 = _find_metric(data, TOP1_KEYS)
    if top1 is not None:
        metrics["top1"] = top1
    margin = _find_metric(data, MARGIN_KEYS)
    if margin is not None:
        metrics["margin"] = margin
    latency = _find_metric(data, LATENCY_KEYS)
    if latency is not None:
        metrics["latency_p95"] = latency
    return metrics


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Execute parse args.

    Args:
        argv: The argv.
    """

    parser = argparse.ArgumentParser(description="Verify benchmark uplift")
    parser.add_argument("--baseline", required=True, type=Path, help="baseline report")
    parser.add_argument(
        "--candidate", required=True, type=Path, help="candidate report"
    )
    parser.add_argument(
        "--accuracy-tolerance",
        type=float,
        default=0.0,
        help="allowed drop in top-1 accuracy before failing (default: 0)",
    )
    parser.add_argument(
        "--margin-tolerance",
        type=float,
        default=0.0,
        help="allowed drop in cosine margin before failing (default: 0)",
    )
    parser.add_argument(
        "--latency-regression",
        type=float,
        default=0.0,
        help="allowed fractional increase in p95 recall latency (0.05 => +5%)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Execute main.

    Args:
        argv: The argv.
    """

    args = parse_args(argv or sys.argv[1:])
    baseline = _extract_metrics(_load_json(args.baseline))
    candidate = _extract_metrics(_load_json(args.candidate))

    failures: list[str] = []

    for key in ("top1", "margin"):
        base = baseline.get(key)
        cand = candidate.get(key)
        if base is None or cand is None:
            continue
        tolerance = args.accuracy_tolerance if key == "top1" else args.margin_tolerance
        if cand + tolerance < base:
            failures.append(
                f"{key} regression: candidate={cand:.4f} baseline={base:.4f} tol={tolerance:.4f}"
            )

    base_lat = baseline.get("latency_p95")
    cand_lat = candidate.get("latency_p95")
    if base_lat is not None and cand_lat is not None:
        limit = base_lat * (1.0 + max(0.0, args.latency_regression))
        if cand_lat > limit:
            failures.append(
                f"latency regression: candidate={cand_lat:.4f}s limit={limit:.4f}s (baseline {base_lat:.4f}s)"
            )

    if failures:
        for line in failures:
            print(f"FAIL: {line}")
        return 1

    summary = [
        "PASS: candidate meets governance uplift criteria",
        f"  top1:      {candidate.get('top1')} (baseline {baseline.get('top1')})",
        f"  margin:    {candidate.get('margin')} (baseline {baseline.get('margin')})",
        f"  latency_p95: {candidate.get('latency_p95')} (baseline {baseline.get('latency_p95')})",
    ]
    print("\n".join(summary))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
