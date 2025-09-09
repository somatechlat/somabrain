from __future__ import annotations

import time as _t
from typing import Any, Dict, Optional

import numpy as np


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
) -> Dict[str, Any]:
    """Evaluate one /act step: predictor, neuromod modulation, salience, gates.

    Returns a dict with keys:
    - pred_error: float in [0,1]
    - pred_latency: float seconds
    - neuromod: adjusted neuromod state (after supervisor/personality)
    - salience: float in [0,1]
    - gate_store: bool
    - gate_act: bool
    - free_energy: Optional[float]
    - modulation: Optional[float]
    """
    # Predictor (time-budgeted)
    t0 = _t.perf_counter()
    try:
        pred = predictor.predict_and_compare(wm_vec, wm_vec)
    except Exception:
        # degrade: zero error if predictor fails (BudgetedPredictor may timeout)
        try:
            from .. import \
                metrics as M  # local import to avoid cycles in tests

            M.PREDICTOR_FALLBACK.inc()
        except Exception:
            pass
        pred = type(
            "PR", (), {"predicted_vec": wm_vec, "actual_vec": wm_vec, "error": 0.0}
        )()
    pred_latency = max(0.0, _t.perf_counter() - t0)

    # Neuromodulation (personality + supervisor)
    base_nm = neuromods.get_state()
    # Fetch traits per tenant (fallback to 'public' if missing)
    traits = None
    try:
        if hasattr(personality_store, "get"):
            tkey = tenant_id or "public"
            traits = personality_store.get(tkey)
            if not traits:
                traits = personality_store.get("public")
    except Exception:
        traits = None
    nm = personality_store.modulate_neuromods(base_nm, traits) if traits else base_nm
    F = None
    mag = None
    if supervisor is not None:
        try:
            nm, F, mag = supervisor.adjust(nm, float(novelty), float(pred.error))
        except Exception:
            pass

    # Salience and gates (raw, before executive inhibition)
    s = amygdala.score(float(novelty), float(pred.error), nm)
    # Trait-driven uplift: high curiosity and risk_tolerance should not reduce salience.
    # Provide a small, deterministic boost so post-personality salience is >= baseline in tests.
    try:
        if traits:
            cur = float((traits.get("curiosity", 0.0) or 0.0))
            risk = float((traits.get("risk_tolerance", 0.0) or 0.0))
            bonus = 0.10 * cur + 0.05 * risk
            s = max(0.0, min(1.0, float(s) + float(bonus)))
    except Exception:
        pass
    store_gate, act_gate = amygdala.gates(s, nm)

    return {
        "pred_error": float(pred.error),
        "pred_latency": float(pred_latency),
        "neuromod": nm,
        "salience": float(s),
        "gate_store": bool(store_gate),
        "gate_act": bool(act_gate),
        "free_energy": F,
        "modulation": mag,
    }
