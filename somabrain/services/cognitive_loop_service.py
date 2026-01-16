"""Cognitive loop evaluation service.

This module provides the core cognitive evaluation step that combines:
- Sleep state management
- Prediction error computation
- Neuromodulation adjustment
- Salience scoring and gating

Architecture:
    Uses DI container for state management. The CognitiveLoopState class
    encapsulates the BeliefUpdate publisher and sleep state cache.

VIBE Compliance:
    - Uses direct imports from metrics.predictor (no lazy imports for circular avoidance)
    - PREDICTOR_ALTERNATIVE imported at module level (no circular deps)
    - All metrics calls are best-effort (silent failure on metrics errors)
"""

from __future__ import annotations

import logging
import time as _t
from typing import Any, Dict, Optional

import numpy as np

from somabrain.core.container import container
from somabrain.metrics.predictor import PREDICTOR_ALTERNATIVE
from somabrain.modes import feature_enabled
from somabrain.sleep import SleepState, SleepStateManager


logger = logging.getLogger(__name__)


class CognitiveLoopState:
    """Encapsulates cognitive loop state for DI container management."""

    def __init__(self) -> None:
        """Initialize the instance."""

        self._bu_publisher = None
        self._sleep_state_cache: Dict[str, tuple[SleepState, float]] = {}
        self._sleep_cache_ttl = 5.0

        if feature_enabled("integrator"):
            try:
                from somabrain.cog.producer import BeliefUpdatePublisher

                publisher = BeliefUpdatePublisher()
                if getattr(publisher, "enabled", False):
                    self._bu_publisher = publisher
            except Exception:
                pass

    @property
    def bu_publisher(self):
        """Get the BeliefUpdate publisher (may be None if disabled)."""
        return self._bu_publisher

    def get_sleep_state(self, tenant_id: str) -> SleepState:
        """Fetch the current sleep state for a tenant with short TTL caching."""
        now = _t.time()
        if tenant_id in self._sleep_state_cache:
            state, ts = self._sleep_state_cache[tenant_id]
            if now - ts < self._sleep_cache_ttl:
                return state

        try:
            from somabrain.models import SleepState as DbSleepState

            # Use Django ORM to fetch sleep state
            # order_by('-timestamp') to get the latest if multiple exist (though ideally unique per tenant)
            # The model has index on [tenant_id, timestamp]
            ss = DbSleepState.objects.filter(tenant_id=tenant_id).order_by("-timestamp").first()

            if ss:
                # Map string state from DB to Enum
                # Ensure we handle case sensitivity if needed, usually upper or matching enum
                try:
                    state = SleepState(ss.state)
                except ValueError:
                    # Fallback if DB has invalid state
                    state = SleepState.ACTIVE
            else:
                state = SleepState.ACTIVE
        except Exception as exc:
            logger.exception("Failed to retrieve sleep state from DB: %s", exc)
            state = SleepState.ACTIVE

        self._sleep_state_cache[tenant_id] = (state, now)
        return state

    def clear_cache(self) -> None:
        """Clear the sleep state cache."""
        self._sleep_state_cache.clear()


def _create_cognitive_loop_state() -> CognitiveLoopState:
    """Factory function for DI container registration."""
    return CognitiveLoopState()


container.register("cognitive_loop_state", _create_cognitive_loop_state)


def get_cognitive_loop_state() -> CognitiveLoopState:
    """Get the cognitive loop state from the DI container."""
    return container.get("cognitive_loop_state")


def eval_step(
    novelty: float,
    wm_vec: np.ndarray,
    cfg,
    predictor,
    neuromods,
    personality_store,
    supervisor: Optional[object],
    amygdala,
    tenant_id: str,
    previous_focus_vec: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """Evaluate one /act step: predictor, neuromod modulation, salience, gates.

    Args:
        novelty: Novelty score for current input
        wm_vec: Current working memory vector (focus)
        cfg: Configuration object
        predictor: Predictor for error computation
        neuromods: Neuromodulator state
        personality_store: Personality trait store
        supervisor: Optional supervisor for adjustment
        amygdala: Amygdala for salience scoring
        tenant_id: Tenant identifier
        previous_focus_vec: Previous focus vector for prediction comparison
            (FIX: was comparing wm_vec to itself, now compares previous to current)

    Returns:
        Dict with pred_error, salience, gates, etc.
    """
    loop_state = get_cognitive_loop_state()

    sleep_state = loop_state.get_sleep_state(tenant_id)
    sleep_mgr = SleepStateManager()
    sleep_params = sleep_mgr.compute_parameters(sleep_state)
    eta = sleep_params["eta"]

    if sleep_state == SleepState.FREEZE:
        return {
            "pred_error": 0.0,
            "pred_latency": 0.0,
            "neuromod": neuromods.get_state(),
            "salience": 0.0,
            "gate_store": False,
            "gate_act": False,
            "free_energy": 0.0,
            "modulation": 0.0,
            "sleep_state": sleep_state.value,
            "eta": 0.0,
        }

    t0 = _t.perf_counter()
    result_extras: Dict[str, Any] = {}

    # FIX: Compare previous_focus_vec to current wm_vec (NOT wm_vec to itself!)
    # Requirements: 3.1, 3.2, 3.3, 3.4
    if previous_focus_vec is None:
        # First step in session - no previous focus (Requirement 3.2)
        try:
            from somabrain.metrics.planning import PREDICT_COMPARE_MISSING_PREV

            PREDICT_COMPARE_MISSING_PREV.inc()
        except Exception:
            pass
        pred = type("PR", (), {"predicted_vec": wm_vec, "actual_vec": wm_vec, "error": 0.0})()
        result_extras["no_prev_focus"] = True
    else:
        try:
            # Compare previous focus to current focus (Requirement 3.1, 3.3)
            pred = predictor.predict_and_compare(previous_focus_vec, wm_vec)
        except Exception as exc:
            try:
                PREDICTOR_ALTERNATIVE.inc()
            except Exception as metric_exc:
                logger.debug("Failed to increment PREDICTOR_ALTERNATIVE metric: %s", metric_exc)
            pred = type("PR", (), {"predicted_vec": wm_vec, "actual_vec": wm_vec, "error": 0.0})()
            logger.exception("Predictor failed, falling back to zero-error recovery path: %s", exc)
    pred_latency = max(0.0, _t.perf_counter() - t0)

    base_nm = neuromods.get_state()
    traits = None
    try:
        if hasattr(personality_store, "get"):
            tkey = tenant_id or "public"
            traits = personality_store.get(tkey)
            if not traits:
                traits = personality_store.get("public")
    except Exception as trait_fetch_exc:
        logger.debug(
            "Failed to fetch personality traits for tenant=%s: %s",
            tenant_id,
            trait_fetch_exc,
        )
        traits = None
    nm = personality_store.modulate_neuromods(base_nm, traits) if traits else base_nm
    F = None
    mag = None
    if supervisor is not None:
        try:
            from typing import Any, cast

            if hasattr(supervisor, "adjust"):
                nm, F, mag = cast(Any, supervisor).adjust(nm, float(novelty), float(pred.error))
        except Exception as exc:
            logger.exception("Supervisor adjustment failed: %s", exc)

    s = amygdala.score(float(novelty), float(pred.error), nm, wm_vec)
    try:
        if traits:
            s = 1.0
    except Exception as trait_exc:
        logger.debug("Failed to apply trait-driven salience uplift: %s", trait_exc)
    store_gate, act_gate = amygdala.gates(s, nm)

    if eta <= 0.0:
        store_gate = False

    bu_publisher = loop_state.bu_publisher
    if bu_publisher is not None:
        try:
            conf = max(0.0, min(1.0, 1.0 - float(pred.error)))
            latency_ms = int(1000.0 * float(pred_latency))
            evidence = {
                "tenant": str(tenant_id),
                "novelty": f"{float(novelty):.4f}",
                "salience": f"{float(s):.4f}",
                "sleep_state": sleep_state.value,
            }
            model_ver = getattr(getattr(predictor, "base", predictor), "version", "v1")
            bu_publisher.publish(
                domain="state",
                delta_error=float(pred.error),
                confidence=float(conf),
                evidence=evidence,
                posterior={},
                model_ver=str(model_ver),
                latency_ms=latency_ms,
            )
        except Exception as exc:
            logger.exception("Telemetry publishing failed: %s", exc)

    result = {
        "pred_error": float(pred.error),
        "pred_latency": float(pred_latency),
        "neuromod": nm,
        "salience": float(s),
        "gate_store": bool(store_gate),
        "gate_act": bool(act_gate),
        "free_energy": F,
        "modulation": mag,
        "sleep_state": sleep_state.value,
        "eta": eta,
    }
    result.update(result_extras)
    return result
