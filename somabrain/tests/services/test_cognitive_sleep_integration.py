import pytest
import numpy as np
from somabrain.services.cognitive_loop_service import eval_step, _SLEEP_STATE_CACHE
from somabrain.sleep import SleepState
from somabrain.neuromodulators import NeuromodState

# Use real classes or functional stubs


class FakePredictor:
    def __init__(self, error=0.1):
        self.error = error
        self.called = False

    def predict_and_compare(self, *args, **kwargs):
        self.called = True

        # Return a simple object with an error attribute
        class Result:
            pass

        r = Result()
        r.error = self.error
        return r


class FakeNeuromods:
    def get_state(self, tenant_id):
        return NeuromodState(
            dopamine=0.5,
            serotonin=0.5,
            noradrenaline=0.5,
            acetylcholine=0.5,
            timestamp=0.0,
        )


class FakePersonalityStore:
    def get(self, tenant_id):
        return None

    def modulate_neuromods(self, nm, tenant_id):
        return nm


class FakeAmygdala:
    def score(self, *args, **kwargs):
        return 0.8

    def gates(self, *args, **kwargs):
        return (True, True)


@pytest.fixture
def real_components():
    predictor = FakePredictor(error=0.1)
    neuromods = FakeNeuromods()
    personality_store = FakePersonalityStore()
    amygdala = FakeAmygdala()
    return predictor, neuromods, personality_store, amygdala


@pytest.fixture
def clean_cache():
    _SLEEP_STATE_CACHE.clear()
    yield
    _SLEEP_STATE_CACHE.clear()


# Instead of patching _get_sleep_state, we inject the cache state directly
# since _get_sleep_state reads from _SLEEP_STATE_CACHE if available (and ttl valid).
# However, _get_sleep_state logic might check circuit breaker if cache missing.
# A better approach for VIBE is to expose a way to inject state or use the real circuit breaker logic.
# But for unit testing `eval_step`, we can pre-populate the cache which `_get_sleep_state` checks.


def set_sleep_state(tenant_id, state):
    import time

    # Cache entry is (value, expiry)
    _SLEEP_STATE_CACHE[tenant_id] = (state, time.time() + 60.0)


def test_eval_step_active_mode(real_components, clean_cache):
    predictor, neuromods, personality_store, amygdala = real_components
    tenant = "tenant1"
    set_sleep_state(tenant, SleepState.ACTIVE)

    result = eval_step(
        novelty=0.5,
        wm_vec=np.zeros(10),
        cfg=None,
        predictor=predictor,
        neuromods=neuromods,
        personality_store=personality_store,
        supervisor=None,
        amygdala=amygdala,
        tenant_id=tenant,
    )

    assert result["sleep_state"] == "active"
    assert result["eta"] > 0.0  # Learning enabled
    assert result["gate_store"] is True  # Storage enabled
    assert result["pred_error"] == 0.1


def test_eval_step_deep_mode(real_components, clean_cache):
    predictor, neuromods, personality_store, amygdala = real_components
    tenant = "tenant1"
    set_sleep_state(tenant, SleepState.DEEP)

    result = eval_step(
        novelty=0.5,
        wm_vec=np.zeros(10),
        cfg=None,
        predictor=predictor,
        neuromods=neuromods,
        personality_store=personality_store,
        supervisor=None,
        amygdala=amygdala,
        tenant_id=tenant,
    )

    assert result["sleep_state"] == "deep"
    assert result["eta"] == 0.0  # Learning suppressed
    assert result["gate_store"] is False  # Storage forced off
    assert result["pred_error"] == 0.1  # Prediction still runs


def test_eval_step_freeze_mode(real_components, clean_cache):
    predictor, neuromods, personality_store, amygdala = real_components
    tenant = "tenant1"
    set_sleep_state(tenant, SleepState.FREEZE)

    result = eval_step(
        novelty=0.5,
        wm_vec=np.zeros(10),
        cfg=None,
        predictor=predictor,
        neuromods=neuromods,
        personality_store=personality_store,
        supervisor=None,
        amygdala=amygdala,
        tenant_id=tenant,
    )

    assert result["sleep_state"] == "freeze"
    assert result["eta"] == 0.0
    assert result["pred_error"] == 0.0  # Dummy result
    assert not predictor.called  # Should short-circuit


def test_eval_step_light_mode(real_components, clean_cache):
    predictor, neuromods, personality_store, amygdala = real_components
    tenant = "tenant1"
    set_sleep_state(tenant, SleepState.LIGHT)

    result = eval_step(
        novelty=0.5,
        wm_vec=np.zeros(10),
        cfg=None,
        predictor=predictor,
        neuromods=neuromods,
        personality_store=personality_store,
        supervisor=None,
        amygdala=amygdala,
        tenant_id=tenant,
    )

    assert result["sleep_state"] == "light"
    assert result["eta"] > 0.0  # Reduced but positive
    assert result["gate_store"] is True
