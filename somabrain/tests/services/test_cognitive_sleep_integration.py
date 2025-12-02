import pytest
import numpy as np
import time
from somabrain.services.cognitive_loop_service import eval_step, _SLEEP_STATE_CACHE
from somabrain.sleep import SleepState


class SimplePredictor:
    def __init__(self, error: float = 0.1):
        self._error = error
        self.called = False

    def predict_and_compare(self, wm_vec, wm_vec_target):
        self.called = True

        class R:
            error = self._error
            predicted_vec = wm_vec
            actual_vec = wm_vec_target

        return R()


class SimpleNeuromods:
    def __init__(self, state=None):
        self._state = state or {"dopamine": 0.5}

    def get_state(self):
        return dict(self._state)


class SimplePersonalityStore:
    def __init__(self):
        self._traits = {}

    def get(self, tenant_id):
        return self._traits.get(tenant_id)

    def modulate_neuromods(self, neuromods, traits):
        return neuromods


class SimpleAmygdala:
    def __init__(self, score_val: float = 0.8, gates_val=(True, True)):
        self._score = score_val
        self._gates = gates_val

    def score(self, *_):
        return self._score

    def gates(self, *_):
        return self._gates


@pytest.fixture
def components():
    predictor = SimplePredictor()
    neuromods = SimpleNeuromods()
    personality_store = SimplePersonalityStore()
    amygdala = SimpleAmygdala()
    return predictor, neuromods, personality_store, amygdala


@pytest.fixture
def clean_cache():
    _SLEEP_STATE_CACHE.clear()
    yield
    _SLEEP_STATE_CACHE.clear()


def test_eval_step_active_mode(components, clean_cache):
    predictor, neuromods, personality_store, amygdala = components
    _SLEEP_STATE_CACHE["tenant1"] = (SleepState.ACTIVE, time.time())

    result = eval_step(
        novelty=0.5,
        wm_vec=np.zeros(10),
        cfg=None,
        predictor=predictor,
        neuromods=neuromods,
        personality_store=personality_store,
        supervisor=None,
        amygdala=amygdala,
        tenant_id="tenant1",
    )

    assert result["sleep_state"] == "active"
    assert result["eta"] > 0.0  # Learning enabled
    assert result["gate_store"] is True  # Storage enabled
    assert result["pred_error"] == 0.1


def test_eval_step_deep_mode(components, clean_cache):
    predictor, neuromods, personality_store, amygdala = components
    _SLEEP_STATE_CACHE["tenant1"] = (SleepState.DEEP, time.time())

    result = eval_step(
        novelty=0.5,
        wm_vec=np.zeros(10),
        cfg=None,
        predictor=predictor,
        neuromods=neuromods,
        personality_store=personality_store,
        supervisor=None,
        amygdala=amygdala,
        tenant_id="tenant1",
    )

    assert result["sleep_state"] == "deep"
    assert result["eta"] == 0.0  # Learning suppressed
    assert result["gate_store"] is False  # Storage forced off
    assert result["pred_error"] == 0.1  # Prediction still runs


def test_eval_step_freeze_mode(components, clean_cache):
    predictor, neuromods, personality_store, amygdala = components
    _SLEEP_STATE_CACHE["tenant1"] = (SleepState.FREEZE, time.time())

    result = eval_step(
        novelty=0.5,
        wm_vec=np.zeros(10),
        cfg=None,
        predictor=predictor,
        neuromods=neuromods,
        personality_store=personality_store,
        supervisor=None,
        amygdala=amygdala,
        tenant_id="tenant1",
    )

    assert result["sleep_state"] == "freeze"
    assert result["eta"] == 0.0
    assert result["pred_error"] == 0.0  # Predictor should be bypassed
    assert predictor.called is False


def test_eval_step_light_mode(components, clean_cache):
    predictor, neuromods, personality_store, amygdala = components
    _SLEEP_STATE_CACHE["tenant1"] = (SleepState.LIGHT, time.time())

    result = eval_step(
        novelty=0.5,
        wm_vec=np.zeros(10),
        cfg=None,
        predictor=predictor,
        neuromods=neuromods,
        personality_store=personality_store,
        supervisor=None,
        amygdala=amygdala,
        tenant_id="tenant1",
    )

    assert result["sleep_state"] == "light"
    assert result["eta"] > 0.0  # Reduced but positive
    assert result["gate_store"] is True
