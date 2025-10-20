from __future__ import annotations

from typing import Optional, Dict, Any
import time as _t
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
        pred = type("PR", (), {"predicted_vec": wm_vec, "actual_vec": wm_vec, "error": 0.0})()
    pred_latency = max(0.0, _t.perf_counter() - t0)

    # Neuromodulation (personality + supervisor)
    base_nm = neuromods.get_state()
    traits = personality_store.get(getattr(cfg, "namespace", "public")) if hasattr(personality_store, "get") else None
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

