"""APM-1: memory interactions drive AdaptationEngine weight updates.

Single entry point for remember/recall/promote/forget paths. Never raises into
the caller (learning must not break I/O) but never pretends success either —
returns bool and logs failures.
"""

from __future__ import annotations

import logging
import math

from somabrain.math.contracts import MEMORY_EVENT_SIGNAL_CLAMP, MEMORY_EVENT_SIGNALS

logger = logging.getLogger(__name__)

_ENGINE_CACHE: dict[str, object] = {}


def _get_engine(tenant_id: str):
    """Per-tenant engine; each engine owns its own weight objects when possible."""
    tid = tenant_id or "default"
    eng = _ENGINE_CACHE.get(tid)
    if eng is not None:
        return eng
    from somabrain.learning.adaptation.engine import AdaptationEngine
    from somabrain.learning.adaptation.types import RetrievalWeights
    from somabrain.learning.config import UtilityWeights
    from somabrain.math.contracts import ADAPT_DEFAULT_LR, ADAPT_DEFAULT_MAX_HISTORY

    lr = ADAPT_DEFAULT_LR
    max_history = ADAPT_DEFAULT_MAX_HISTORY
    try:
        from somabrain.brain_settings.models import BrainSetting

        lr = float(BrainSetting.get("adapt_lr", tid))
        max_history = int(BrainSetting.get("adapt_max_history", tid))
    except Exception:
        try:
            from django.conf import settings as dj_settings

            lr = float(getattr(dj_settings, "SOMABRAIN_ADAPT_LR", lr))
            max_history = int(getattr(dj_settings, "SOMABRAIN_ADAPT_MAX_HISTORY", max_history))
        except Exception:
            pass

    # Isolated per-tenant objects (do not share a factory singleton).
    eng = AdaptationEngine(
        retrieval=RetrievalWeights(1.0, 0.3, 0.5, 0.7),
        utility=UtilityWeights(),
        learning_rate=lr,
        max_history=max_history,
        tenant_id=tid,
        enable_dynamic_lr=False,
    )
    _ENGINE_CACHE[tid] = eng
    return eng


def signal_for_event(kind: str, utility: float | None = None) -> float | None:
    """Return clamped signed signal for a memory event, or None if invalid."""
    if utility is not None:
        s = float(utility)
    else:
        if kind not in MEMORY_EVENT_SIGNALS or kind == "feedback":
            return None
        s = float(MEMORY_EVENT_SIGNALS[kind])
    if not math.isfinite(s):
        return None
    lo, hi = MEMORY_EVENT_SIGNAL_CLAMP
    return min(max(s, lo), hi)


def apply_memory_event(
    kind: str,
    tenant_id: str | None = None,
    utility: float | None = None,
) -> bool:
    """Adapt per-tenant weights from a memory interaction. Fail-soft, honest bool."""
    try:
        s = signal_for_event(kind, utility=utility)
        if s is None:
            return False
        if kind == "recall_miss" and s > 0:
            s = -s
        eng = _get_engine(tenant_id)
        return bool(eng.apply_feedback(s, reward=s))
    except Exception:
        logger.exception("MEMORY_EVENT_LEARNING_FAILED kind=%s", kind)
        return False


def remember_learned(tenant_id: str | None, *, kind: str, utility: float | None = None) -> None:
    """Fire-and-forget hook for memory I/O paths."""
    apply_memory_event(kind, tenant_id=tenant_id, utility=utility)
