import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from somabrain.services.cognitive_loop_service import eval_step, _SLEEP_STATE_CACHE
from somabrain.sleep import SleepState


@pytest.fixture
def mock_components():
    predictor = MagicMock()
    predictor.predict_and_compare.return_value.error = 0.1

    neuromods = MagicMock()
    neuromods.get_state.return_value = {"dopamine": 0.5}

    personality_store = MagicMock()
    personality_store.get.return_value = None
    personality_store.modulate_neuromods.side_effect = lambda nm, t: nm

    amygdala = MagicMock()
    amygdala.score.return_value = 0.8
    amygdala.gates.return_value = (True, True)

    return predictor, neuromods, personality_store, amygdala


@pytest.fixture
def clean_cache():
    _SLEEP_STATE_CACHE.clear()
    yield
    _SLEEP_STATE_CACHE.clear()


def test_eval_step_active_mode(mock_components, clean_cache):
    predictor, neuromods, personality_store, amygdala = mock_components

    with patch(
        "somabrain.services.cognitive_loop_service._get_sleep_state"
    ) as mock_get_state:
        mock_get_state.return_value = SleepState.ACTIVE

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


def test_eval_step_deep_mode(mock_components, clean_cache):
    predictor, neuromods, personality_store, amygdala = mock_components

    with patch(
        "somabrain.services.cognitive_loop_service._get_sleep_state"
    ) as mock_get_state:
        mock_get_state.return_value = SleepState.DEEP

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


def test_eval_step_freeze_mode(mock_components, clean_cache):
    predictor, neuromods, personality_store, amygdala = mock_components

    with patch(
        "somabrain.services.cognitive_loop_service._get_sleep_state"
    ) as mock_get_state:
        mock_get_state.return_value = SleepState.FREEZE

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
        assert result["pred_error"] == 0.0  # Dummy result
        predictor.predict_and_compare.assert_not_called()  # Should short-circuit


def test_eval_step_light_mode(mock_components, clean_cache):
    predictor, neuromods, personality_store, amygdala = mock_components

    with patch(
        "somabrain.services.cognitive_loop_service._get_sleep_state"
    ) as mock_get_state:
        mock_get_state.return_value = SleepState.LIGHT

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
