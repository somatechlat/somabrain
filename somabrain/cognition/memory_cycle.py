"""Cognition on every memory cycle (remember / recall / promote).

COGNITION ALWAYS ON law: hippocampus · amygdala · PFC · BG · neuromodulators ·
learner run on every memory cycle, not only ``/cognitive/act``.

This module is the ONE shared caller of ``cognitive_loop_service.eval_step``
for memory paths. ``/act`` keeps its own path; this one is extracted so the
memory cycle never constructs its own cog stack (uses bootstrap singletons).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("somabrain.cognition.memory_cycle")


def _safe_eval(novelty: float, wm_vec: Any, tenant_id: str, label: str) -> dict[str, Any]:
    """Run the shared cog step; never raise into the memory hot path."""
    try:
        from django.conf import settings

        from somabrain.bootstrap.singletons import (
            get_amygdala,
            get_neuromodulators,
            get_personality_store,
            get_predictor,
            get_supervisor,
        )
        from somabrain.services.cognitive_loop_service import eval_step

        predictor = get_predictor()
        neuromods = get_neuromodulators()
        personality_store = get_personality_store()
        amygdala = get_amygdala()
        supervisor = get_supervisor()
        if wm_vec is None:
            import numpy as np

            from somabrain.embed_dim import resolve_embed_dim

            wm_vec = np.zeros(resolve_embed_dim(), dtype=np.float32)
        result = eval_step(
            novelty=float(novelty or 0.0),
            wm_vec=wm_vec,
            cfg=settings,
            predictor=predictor,
            neuromods=neuromods,
            personality_store=personality_store,
            supervisor=supervisor,
            amygdala=amygdala,
            tenant_id=tenant_id,
        )
        return dict(result) if isinstance(result, dict) else {}
    except Exception as exc:
        logger.warning("memory-cycle cognition (%s) failed: %s", label, exc)
        return {"cognition_error": str(exc), "label": label}


def remember_cognition(
    *,
    text: str,
    tenant_id: str,
    wm_vec: Any = None,
    salience: float = 0.0,
) -> dict[str, Any]:
    """Cognition hook after durable-accept on remember."""
    result = _safe_eval(salience, wm_vec, tenant_id, "remember")
    try:
        from somabrain.learning.memory_events import remember_learned

        remember_learned(tenant_id, kind="remember", utility=float(salience or 0.0))
    except Exception as exc:
        logger.debug("remember learning hook failed: %s", exc)
    return result


def recall_cognition(
    *,
    query: str,
    hits: list[Any],
    tenant_id: str,
    wm_vec: Any = None,
) -> dict[str, Any]:
    """Cognition hook after hits are gathered on recall."""
    best = 0.0
    for hit in hits or []:
        score = getattr(hit, "score", None)
        if score is None and isinstance(hit, dict):
            score = hit.get("score")
        try:
            best = max(best, float(score or 0.0))
        except Exception:
            continue
    result = _safe_eval(best, wm_vec, tenant_id, "recall")
    try:
        from somabrain.learning.memory_events import remember_learned

        kind = "recall_hit" if hits else "recall_miss"
        remember_learned(tenant_id, kind=kind, utility=best if hits else None)
    except Exception as exc:
        logger.debug("recall learning hook failed: %s", exc)
    return result


def promote_cognition(
    *,
    candidate: Any,
    tenant_id: str,
    wm_vec: Any = None,
    salience: float = 0.0,
) -> dict[str, Any]:
    """Cognition hook before WM→LTM promote. Returns step; caller checks gate."""
    return _safe_eval(salience, wm_vec, tenant_id, "promote")
