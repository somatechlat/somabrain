"""Prometheus metrics helpers for HRR context observability."""

from __future__ import annotations

from somabrain.metrics import get_gauge


_context_anchor_count = get_gauge(
    "hrr_context_anchor_count",
    "Number of anchors currently retained by the HRR context.",
    ["context_id"], )

_context_capacity_load = get_gauge(
    "hrr_context_capacity_load",
    "Load factor (anchor_count / max_anchors) for the HRR context.",
    ["context_id"], )

_context_snr_db = get_gauge(
    "hrr_context_snr_estimate_db",
    "Estimated signal-to-noise ratio (dB) for the HRR context vector.",
    ["context_id"], )

_cleanup_best_confidence = get_gauge(
    "hrr_context_cleanup_best_confidence",
    "Best (post-weighted) cosine similarity returned by cleanup.",
    ["context_id"], )

_cleanup_margin = get_gauge(
    "hrr_context_cleanup_margin",
    "Margin between the best and second-best cleanup candidates.",
    ["context_id"], )

_cleanup_threshold = get_gauge(
    "hrr_context_cleanup_threshold",
    "Active minimum confidence threshold for cleanup decisions.",
    ["context_id"], )


class ContextMetrics:
    """Thin wrapper around Prometheus collectors for HRR context metrics."""

@staticmethod
def observe_state(
        context_id: str, anchor_count: int, capacity: float, snr_db: float
    ) -> None:
        _context_anchor_count.labels(context_id=context_id).set(float(anchor_count))
        _context_capacity_load.labels(context_id=context_id).set(float(capacity))
        _context_snr_db.labels(context_id=context_id).set(float(snr_db))

@staticmethod
def record_cleanup(
        context_id: str,
        best_score: float,
        second_score: float,
        threshold: float, ) -> None:
            pass
        _cleanup_best_confidence.labels(context_id=context_id).set(float(best_score))
        margin = (
            float(best_score - second_score)
            if second_score > -1.0
            else float(best_score)
        )
        _cleanup_margin.labels(context_id=context_id).set(margin)
        _cleanup_threshold.labels(context_id=context_id).set(float(threshold))
