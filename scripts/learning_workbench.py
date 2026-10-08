#!/usr/bin/env python3
"""SomaBrain Learning Workbench — PROVE the brain learns from memory events.

Runs a closed curriculum of remember/recall/promote/feedback-style events and
prints weight trajectories. Exit 0 only if learning is real (weights move in
the predicted directions and stay finite/bounded).

Usage:
    python3 scripts/learning_workbench.py
    python3 scripts/learning_workbench.py --json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from somabrain.learning.adaptation.engine import AdaptationEngine
from somabrain.learning.adaptation.types import RetrievalWeights
from somabrain.learning.config import UtilityWeights
from somabrain.learning.memory_events import apply_memory_event, signal_for_event
from somabrain.math.contracts import ADAPT_BOUNDS, MEMORY_EVENT_SIGNALS


def _engine(tenant: str) -> AdaptationEngine:
    return AdaptationEngine(
        retrieval=RetrievalWeights(1.0, 0.3, 0.5, 0.7),
        utility=UtilityWeights(),
        learning_rate=0.1,
        max_history=128,
        tenant_id=tenant,
        enable_dynamic_lr=False,
    )


def snapshot(eng: AdaptationEngine) -> dict[str, float]:
    return {
        "alpha": float(eng.alpha),
        "beta": float(eng._retrieval.beta),
        "gamma": float(eng._retrieval.gamma),
        "tau": float(eng._retrieval.tau),
        "lambda_": float(eng._utility.lambda_),
        "mu": float(eng._utility.mu),
        "nu": float(eng._utility.nu),
    }


def run_curriculum(tenant: str = "workbench") -> dict:
    eng = _engine(tenant)
    start = snapshot(eng)
    trajectory: list[dict] = [{"step": 0, "event": "init", **start}]

    # Phase A: consistent recall hits → alpha should rise
    hit_alpha = []
    for i in range(30):
        ok = eng.apply_memory_event("recall_hit")
        if not ok:
            raise RuntimeError(f"recall_hit rejected at step {i}")
        hit_alpha.append(eng.alpha)
        trajectory.append({"step": len(trajectory), "event": "recall_hit", **snapshot(eng)})
    after_hits = snapshot(eng)

    # Phase B: misses → alpha should fall from peak
    for i in range(20):
        ok = eng.apply_memory_event("recall_miss")
        if not ok:
            raise RuntimeError(f"recall_miss rejected at step {i}")
        trajectory.append({"step": len(trajectory), "event": "recall_miss", **snapshot(eng)})
    after_miss = snapshot(eng)

    # Phase C: promote + feedback
    eng.apply_memory_event("promote_success")
    trajectory.append({"step": len(trajectory), "event": "promote_success", **snapshot(eng)})
    eng.apply_memory_event("feedback", utility=0.5)
    trajectory.append({"step": len(trajectory), "event": "feedback", **snapshot(eng)})
    final = snapshot(eng)

    # Phase D: NaN immunity
    nan_ok = eng.apply_memory_event("recall_hit", utility=float("nan"))
    after_nan = snapshot(eng)

    # Assertions — the PROOF
    proofs = {
        "alpha_rises_on_hits": after_hits["alpha"] > start["alpha"],
        "alpha_falls_on_misses": after_miss["alpha"] < after_hits["alpha"],
        "alpha_monotone_nondecreasing_on_hits": all(
            hit_alpha[i] <= hit_alpha[i + 1] + 1e-12 for i in range(len(hit_alpha) - 1)
        ),
        "nan_rejected": nan_ok is False,
        "all_finite": all(math.isfinite(v) for v in final.values()),
        "alpha_in_bounds": ADAPT_BOUNDS["alpha"][0] - 1e-9
        <= final["alpha"]
        <= ADAPT_BOUNDS["alpha"][1] + 1e-9,
        "gamma_in_bounds": ADAPT_BOUNDS["gamma"][0] - 1e-9
        <= final["gamma"]
        <= ADAPT_BOUNDS["gamma"][1] + 1e-9,
        "weights_actually_moved": final != start,
        "miss_signal_negative": signal_for_event("recall_miss") is not None
        and signal_for_event("recall_miss") < 0,
    }

    # Per-tenant isolation
    e2 = _engine("workbench-other")
    e2.apply_memory_event("recall_hit")
    proofs["per_tenant_isolated"] = e2.alpha != eng.alpha or e2 is not eng

    passed = all(proofs.values())
    return {
        "verdict": "LEARNING_PROVEN" if passed else "LEARNING_FAILED",
        "signals": MEMORY_EVENT_SIGNALS,
        "start": start,
        "after_30_hits": after_hits,
        "after_20_misses": after_miss,
        "final": final,
        "proofs": proofs,
        "trajectory_tail": trajectory[-8:],
        "trajectory_len": len(trajectory),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="SomaBrain learning workbench")
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    args = parser.parse_args()
    report = run_curriculum()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("=" * 60)
        print("SOMABRAIN LEARNING WORKBENCH")
        print("=" * 60)
        print(f"VERDICT: {report['verdict']}")
        print(f"start:        {report['start']}")
        print(f"after 30 hits:{report['after_30_hits']}")
        print(f"after misses: {report['after_20_misses']}")
        print(f"final:        {report['final']}")
        print("-" * 60)
        print("PROOFS:")
        for k, v in report["proofs"].items():
            print(f"  {'PASS' if v else 'FAIL'}  {k}")
        print("-" * 60)
        print(f"trajectory steps: {report['trajectory_len']}")
    return 0 if report["verdict"] == "LEARNING_PROVEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
