"""Cognitive loop evaluation service.

This module provides the core cognitive evaluation step that combines:
- Sleep state management
- Prediction error computation
- Neuromodulation adjustment (including personality trait bias, T83)
- VAD emotion update and couplings into salience / gate temperature (T82)
- Salience scoring and amygdala gating
- Prefrontal precision-weighted WM admission (T81)
- Basal-ganglia Boltzmann action selection (T80)

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
import types
from typing import Any

import numpy as np

from somabrain.core.container import container
from somabrain.metrics.predictor import PREDICTOR_ALTERNATIVE
from somabrain.runtime.modes import feature_enabled
from somabrain.sleep import SleepState, SleepStateManager

logger = logging.getLogger(__name__)


class CognitiveLoopState:
    """Encapsulates cognitive loop state for DI container management."""

    def __init__(self) -> None:
        """Initialize the instance."""

        self._bu_publisher = None
        self._sleep_state_cache: dict[str, tuple[SleepState, float]] = {}
        self._sleep_cache_ttl = 5.0

        if feature_enabled("integrator"):
            try:
                from somabrain.cog.producer import BeliefUpdatePublisher

                publisher = BeliefUpdatePublisher()
                if getattr(publisher, "enabled", False):
                    self._bu_publisher = publisher
            except Exception as e:
                logger.warning(f"Failed to initialize BeliefUpdatePublisher: {e}")

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
            from somabrain.admin.core.models import SleepState as DbSleepState

            # Use Django ORM to fetch sleep state
            # order_by('-timestamp') to get the latest if multiple exist (though ideally unique per tenant)
            # The model has index on [tenant_id, timestamp]
            ss = (
                DbSleepState.objects.filter(tenant_id=tenant_id)
                .order_by("-timestamp")
                .first()
            )

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
    supervisor: object | None,
    amygdala,
    tenant_id: str,
    previous_focus_vec: np.ndarray | None = None,
) -> dict[str, Any]:
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
            "neuromod": neuromods.get_state(tenant_id),
            "salience": 0.0,
            "gate_store": False,
            "gate_act": False,
            "free_energy": 0.0,
            "modulation": 0.0,
            "sleep_state": sleep_state.value,
            "eta": 0.0,
            "wm_admit": False,
            "policy": None,
        }

    t0 = _t.perf_counter()
    result_extras: dict[str, Any] = {}

    # FIX: Compare previous_focus_vec to current wm_vec (NOT wm_vec to itself!)
    # Requirements: 3.1, 3.2, 3.3, 3.4
    if previous_focus_vec is None:
        # First step in session - no previous focus (Requirement 3.2)
        try:
            from somabrain.metrics.planning import PREDICT_COMPARE_MISSING_PREV

            PREDICT_COMPARE_MISSING_PREV.inc()
        except Exception:
            pass
        pred = types.SimpleNamespace(predicted_vec=wm_vec, actual_vec=wm_vec, error=0.0)
        result_extras["no_prev_focus"] = True
    else:
        try:
            # Compare previous focus to current focus (Requirement 3.1, 3.3)
            pred = predictor.predict_and_compare(previous_focus_vec, wm_vec)
        except Exception as exc:
            try:
                PREDICTOR_ALTERNATIVE.inc()
            except Exception as metric_exc:
                logger.debug(
                    "Failed to increment PREDICTOR_ALTERNATIVE metric: %s", metric_exc
                )
            raise RuntimeError(f"Predictor failed: {exc}") from exc
    pred_latency = max(0.0, _t.perf_counter() - t0)

    base_nm = neuromods.get_state(tenant_id)
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
    # Personality trait → neuromod blend (T83). Unmapped traits are identity
    # metadata and have no behavioural effect.
    nm = base_nm
    if traits is not None and hasattr(personality_store, "modulate_neuromods"):
        try:
            nm = personality_store.modulate_neuromods(base_nm, traits)
        except Exception as trait_mod_exc:
            logger.debug(
                "Personality neuromod modulation failed for tenant=%s: %s",
                tenant_id,
                trait_mod_exc,
            )
            nm = base_nm
    F = None
    mag = None
    if supervisor is not None:
        try:
            from typing import Any, cast

            if hasattr(supervisor, "adjust"):
                nm, F, mag = cast(Any, supervisor).adjust(
                    nm, float(novelty), float(pred.error)
                )
        except Exception as exc:
            logger.exception("Supervisor adjustment failed: %s", exc)

    # VAD emotion (T82): update from this step's signals, then derive the
    # salience / temperature / threshold couplings.
    affect_boost = 0.0
    temperature_scale = 1.0
    threshold_offset = 0.0
    emotion_state = None
    try:
        from somabrain.admin.cognitive.emotion import (
            affect_salience_boost,
            affect_temperature_scale,
            affect_threshold_offset,
            stimulus_from_signals,
        )
        from somabrain.bootstrap.singletons import get_emotion_model

        emotion = get_emotion_model()
        emotion.update(stimulus_from_signals(float(novelty), float(pred.error)))
        if float(getattr(emotion, "decay_rate", 0.0) or 0.0) > 0.0:
            emotion.decay()
        emotion_state = emotion.as_dict()
        affect_boost = affect_salience_boost(emotion.state)
        temperature_scale = affect_temperature_scale(emotion.state)
        threshold_offset = affect_threshold_offset(emotion.state)
    except Exception as emo_exc:
        logger.debug("Emotion coupling unavailable: %s", emo_exc)

    s = amygdala.score(
        float(novelty), float(pred.error), nm, wm_vec, affect_boost=affect_boost
    )
    store_gate, act_gate = amygdala.gates(
        s,
        nm,
        temperature_scale=temperature_scale,
        threshold_offset=threshold_offset,
    )

    if eta <= 0.0:
        store_gate = False

    # Prefrontal precision-weighted WM admission (T81).
    wm_admit = True
    try:
        from somabrain.bootstrap.singletons import get_prefrontal

        prefrontal = get_prefrontal()
        wm_admit = bool(prefrontal.gate_wm(float(s), float(pred.error)))
    except Exception as pf_exc:
        logger.debug("Prefrontal WM gate unavailable: %s", pf_exc)

    # Basal-ganglia Boltzmann action selection (T80). Values come from
    # salience and the amygdala gates; the selection is the final store/act
    # decision and populates the step ``policy`` payload.
    policy_payload: dict[str, Any] | None = None
    try:
        from somabrain.bootstrap.singletons import get_basal_ganglia

        bg = get_basal_ganglia()
        gate_closed = 0.0
        action_values = {
            "skip": max(0.0, 1.0 - float(s)),
            "store": float(s) if store_gate else gate_closed,
            "act": float(s) if act_gate else gate_closed,
            "both": float(s) if (store_gate and act_gate) else gate_closed,
        }
        decision, selection = bg.decide(action_values)
        store_gate = bool(decision.store)
        act_gate = bool(decision.act)
        if eta <= 0.0:
            store_gate = False
        policy_payload = selection.as_dict()
    except Exception as bg_exc:
        logger.debug("Basal ganglia selection unavailable: %s", bg_exc)

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
        "wm_admit": bool(wm_admit),
        "policy": policy_payload,
    }
    if emotion_state is not None:
        result["emotion"] = emotion_state
    result.update(result_extras)
    return result
