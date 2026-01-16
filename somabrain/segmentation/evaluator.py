"""Segmentation Evaluator Harness

Computes acceptance KPIs for segmentation boundaries:
 - Boundary F1 (change vs emitted)
 - False boundary rate (spurious emissions)
 - Mean dwell latency (ticks between true changes)

Provides synthetic generation helpers for local CI tests and exposes
Prometheus metrics for dashboards.

VIBE Compliance:
    - Uses DI container for metrics cache instead of module-level global state
    - Lazy initialization via DI container
    - Thread-safe via DI container
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SegmentationMetricsCache:
    """Cache for segmentation metrics.

    VIBE Compliance:
        - Managed via DI container instead of module-level globals
        - Lazy initialization of metrics
    """

    f1_gauge: Any = None
    false_rate_gauge: Any = None
    latency_histogram: Any = None
    initialized: bool = False


def _get_metrics_cache() -> SegmentationMetricsCache:
    """Get metrics cache from DI container."""
    from somabrain.core.container import container

    if not container.has("segmentation_metrics_cache"):
        container.register("segmentation_metrics_cache", SegmentationMetricsCache)
    return container.get("segmentation_metrics_cache")


def _ensure_metrics() -> SegmentationMetricsCache:
    """Ensure metrics are initialized.

    VIBE Compliance:
        - Uses DI container for cache instead of global state
        - Lazy initialization
    """
    cache = _get_metrics_cache()
    if cache.initialized:
        return cache

    try:
        from somabrain import metrics
    except Exception:
        cache.initialized = True
        return cache

    if cache.f1_gauge is None:
        try:
            cache.f1_gauge = metrics.get_gauge(
                "somabrain_segmentation_boundary_f1",
                "Segmentation boundary F1 score",
                labelnames=["tenant"],
            )
        except Exception as exc:
            logger.debug("Failed to create f1_gauge metric: %s", exc)

    if cache.false_rate_gauge is None:
        try:
            cache.false_rate_gauge = metrics.get_gauge(
                "somabrain_segmentation_false_boundary_rate",
                "Rate of false emitted boundaries (FP / emitted)",
                labelnames=["tenant"],
            )
        except Exception as exc:
            logger.debug("Failed to create false_rate_gauge metric: %s", exc)

    if cache.latency_histogram is None:
        try:
            cache.latency_histogram = metrics.get_histogram(
                "somabrain_segmentation_latency_ticks",
                "Average dwell latency between true changes (ticks)",
                buckets=(1, 2, 3, 4, 5, 8, 13, 21, 34, 55),
            )
        except Exception as exc:
            logger.debug("Failed to create latency_histogram metric: %s", exc)

    cache.initialized = True
    return cache


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
    max(0, len(true) - tp)
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
    """Update segmentation metrics.

    VIBE Compliance:
        - Uses DI container for metrics cache
        - Proper error logging instead of silent pass
    """
    cache = _ensure_metrics()
    t = (tenant or "public").strip() or "public"
    try:
        if cache.f1_gauge is not None:
            cache.f1_gauge.labels(tenant=t).set(f1)
        if cache.false_rate_gauge is not None:
            cache.false_rate_gauge.labels(tenant=t).set(false_rate)
        if cache.latency_histogram is not None:
            cache.latency_histogram.observe(max(0.0, mean_latency))
    except Exception as exc:
        logger.debug("Failed to update segmentation metrics: %s", exc)


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
