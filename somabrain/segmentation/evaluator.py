"""Segmentation Evaluator Harness

Computes acceptance KPIs for segmentation boundaries:
 - Boundary F1 (change vs emitted)
 - False boundary rate (spurious emissions)
 - Mean dwell latency (ticks between true changes)

Provides synthetic generation helpers for local CI tests and exposes
Prometheus metrics for dashboards.
"""

from __future__ import annotations

from typing import List, Tuple, Dict, Iterable
import random

try:
    from somabrain import metrics  # type: ignore
except Exception:  # pragma: no cover
    metrics = None  # type: ignore


# Metrics (lazy init on first update)
_mx_f1 = None
_mx_false_rate = None
_mx_latency = None


def _ensure_metrics() -> None:
    global _mx_f1, _mx_false_rate, _mx_latency
    if metrics is None:
        return
    if _mx_f1 is None:
        try:
            _mx_f1 = metrics.get_gauge(
                "somabrain_segmentation_boundary_f1",
                "Segmentation boundary F1 score",
                labelnames=["tenant"],
            )
        except Exception:
            _mx_f1 = None
    if _mx_false_rate is None:
        try:
            _mx_false_rate = metrics.get_gauge(
                "somabrain_segmentation_false_boundary_rate",
                "Rate of false emitted boundaries (FP / emitted)",
                labelnames=["tenant"],
            )
        except Exception:
            _mx_false_rate = None
    if _mx_latency is None:
        try:
            _mx_latency = metrics.get_histogram(
                "somabrain_segmentation_latency_ticks",
                "Average dwell latency between true changes (ticks)",
                buckets=(1, 2, 3, 4, 5, 8, 13, 21, 34, 55),
            )
        except Exception:
            _mx_latency = None


def generate_synthetic_sequence(
    length: int = 200,
    change_prob: float = 0.05,
    domains: Iterable[str] | None = None,
    seed: int | None = None,
) -> List[str]:
    """Generate synthetic leader domain sequence with random changes.

    Args:
        length: number of ticks
        change_prob: probability of domain change at each tick
        domains: iterable of domain labels (default state/agent/action)
        seed: optional RNG seed
    Returns:
        List of domain labels per tick.
    """
    rnd = random.Random(seed)
    doms = list(domains or ("state", "agent", "action"))
    seq: List[str] = []
    cur = rnd.choice(doms)
    for _ in range(length):
        if rnd.random() < change_prob:
            cur = rnd.choice([d for d in doms if d != cur])
        seq.append(cur)
    return seq


def true_boundaries(sequence: List[str]) -> List[int]:
    """Return tick indices where domain changes in the sequence."""
    out: List[int] = []
    prev = None
    for i, d in enumerate(sequence):
        if prev is None:
            prev = d
            continue
        if d != prev:
            out.append(i)
            prev = d
    return out


def evaluate_boundaries(
    emitted: List[int],
    true: List[int],
    tolerance: int = 0,
) -> Tuple[float, float, float]:
    """Compute F1, false boundary rate, mean dwell latency.

    A predicted boundary is a TP if there exists a true boundary within
    +/- tolerance ticks. Others are FP. FN are true boundaries with no
    emitted match.

    False boundary rate = FP / max(1, len(emitted)).
    Mean dwell latency = average difference between successive true boundaries.
    """
    if not true:
        return 0.0, 0.0, 0.0
    matched_true = set()
    tp = 0
    for e in emitted:
        # find nearest true within tolerance
        for t in true:
            if t in matched_true:
                continue
            if abs(e - t) <= tolerance:
                tp += 1
                matched_true.add(t)
                break
    fp = max(0, len(emitted) - tp)
    fn = max(0, len(true) - tp)
    precision = tp / len(emitted) if emitted else 0.0
    recall = tp / len(true) if true else 0.0
    f1 = (
        (2 * precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    false_rate = fp / len(emitted) if emitted else 0.0
    # Mean dwell latency across true boundaries (intervals between changes)
    if len(true) > 1:
        intervals = [b - a for a, b in zip(true[:-1], true[1:])]
        mean_latency = sum(intervals) / len(intervals)
    else:
        mean_latency = 0.0
    return f1, false_rate, mean_latency


def update_metrics(
    tenant: str, f1: float, false_rate: float, mean_latency: float
) -> None:
    _ensure_metrics()
    t = (tenant or "public").strip() or "public"
    try:
        if _mx_f1 is not None:
            _mx_f1.labels(tenant=t).set(f1)
        if _mx_false_rate is not None:
            _mx_false_rate.labels(tenant=t).set(false_rate)
        if _mx_latency is not None:
            _mx_latency.observe(max(0.0, mean_latency))
    except Exception:
raise NotImplementedError("Placeholder removed per VIBE rules")


def evaluate_sequence(
    sequence: List[str], emitted_boundaries: List[int], tenant: str = "public"
) -> Dict[str, float]:
    """High-level convenience wrapper: derives true boundaries, evaluates, updates metrics.

    Returns dict of metrics for caller assertions/tests.
    """
    tb = true_boundaries(sequence)
    f1, false_rate, mean_latency = evaluate_boundaries(emitted_boundaries, tb)
    update_metrics(tenant, f1, false_rate, mean_latency)
    return {
        "f1": f1,
        "false_rate": false_rate,
        "mean_latency": mean_latency,
        "true_count": len(tb),
        "emitted_count": len(emitted_boundaries),
    }
