"""Shared Django settings bootstrap for no_django unit tests.

Configures ``django.conf`` once with the production defaults these suites
need. First caller wins; later callers see the already-configured settings.
"""

from __future__ import annotations

import runpy
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def production_neuro_defaults() -> dict[str, float]:
    ns = runpy.run_path(str(REPO_ROOT / "somabrain" / "settings" / "neuro.py"))
    return {k: v for k, v in ns.items() if k.startswith("SOMABRAIN_NEURO_")}


def _required_settings() -> dict[str, object]:
    from somabrain.math.contracts import (
        ADAPT_BOUNDS,
        ADAPT_GAINS,
        RECENCY_FLOOR,
        RECENCY_SCALE,
        RECENCY_SHARPNESS,
        TAU_FLOOR,
    )

    cfg: dict[str, object] = dict(production_neuro_defaults())
    cfg.update(
        {
            "SECRET_KEY": "test-only-secret-key",
            "ROOT_URLCONF": "somabrain.config.urls",
            "SOMA_API_TOKEN": "test-sfm-token",
            "SOMABRAIN_MEMORY_HTTP_TOKEN": "test-only-token",
            "REQUIRE_EXTERNAL_BACKENDS": False,
            "ENABLE_LEARNING_STATE_PERSISTENCE": False,
            "REDIS_DB": 0,
            "ENTROPY_CAP": 0.0,
            "SOMABRAIN_LEARNING_RATE_DYNAMIC": False,
            "SOMABRAIN_DEFAULT_TENANT": "default",
            "SOMABRAIN_NAMESPACE": "somabrain",
            "SOMABRAIN_TAU_FLOOR": TAU_FLOOR,
            # Adaptation contract mirrors
            "SOMABRAIN_ADAPTATION_GAIN_ALPHA": ADAPT_GAINS["alpha"],
            "SOMABRAIN_ADAPTATION_GAIN_GAMMA": ADAPT_GAINS["gamma"],
            "SOMABRAIN_ADAPTATION_GAIN_LAMBDA": ADAPT_GAINS["lambda_"],
            "SOMABRAIN_ADAPTATION_GAIN_MU": ADAPT_GAINS["mu"],
            "SOMABRAIN_ADAPTATION_GAIN_NU": ADAPT_GAINS["nu"],
            "SOMABRAIN_ADAPTATION_ALPHA_MIN": ADAPT_BOUNDS["alpha"][0],
            "SOMABRAIN_ADAPTATION_ALPHA_MAX": ADAPT_BOUNDS["alpha"][1],
            "SOMABRAIN_ADAPTATION_GAMMA_MIN": ADAPT_BOUNDS["gamma"][0],
            "SOMABRAIN_ADAPTATION_GAMMA_MAX": ADAPT_BOUNDS["gamma"][1],
            "SOMABRAIN_ADAPTATION_LAMBDA_MIN": ADAPT_BOUNDS["lambda_"][0],
            "SOMABRAIN_ADAPTATION_LAMBDA_MAX": ADAPT_BOUNDS["lambda_"][1],
            "SOMABRAIN_ADAPTATION_MU_MIN": ADAPT_BOUNDS["mu"][0],
            "SOMABRAIN_ADAPTATION_MU_MAX": ADAPT_BOUNDS["mu"][1],
            "SOMABRAIN_ADAPTATION_NU_MIN": ADAPT_BOUNDS["nu"][0],
            "SOMABRAIN_ADAPTATION_NU_MAX": ADAPT_BOUNDS["nu"][1],
            "SOMABRAIN_UTILITY_LAMBDA": 1.0,
            "SOMABRAIN_UTILITY_MU": 0.1,
            "SOMABRAIN_UTILITY_NU": 0.05,
            # Recency / context builder
            "SOMABRAIN_RETRIEVAL_ALPHA": 1.0,
            "SOMABRAIN_RETRIEVAL_BETA": 0.2,
            "SOMABRAIN_RETRIEVAL_GAMMA": 0.1,
            "SOMABRAIN_RETRIEVAL_TAU": 0.7,
            "SOMABRAIN_WM_RECENCY_TIME_SCALE": RECENCY_SCALE,
            "SOMABRAIN_RECENCY_SHARPNESS": RECENCY_SHARPNESS,
            "SOMABRAIN_RECENCY_FLOOR": RECENCY_FLOOR,
            "SOMABRAIN_DENSITY_TARGET": 0.2,
            "SOMABRAIN_DENSITY_FLOOR": 0.6,
            "SOMABRAIN_DENSITY_WEIGHT": 0.35,
            "SOMABRAIN_TAU_MAX": 1.2,
            "SOMABRAIN_TAU_INC_UP": 0.1,
            "SOMABRAIN_TAU_INC_DOWN": 0.05,
            "SOMABRAIN_DUP_RATIO_THRESHOLD": 0.5,
            # Circuit breaker (MemoryService import)
            "SOMABRAIN_CIRCUIT_FAILURE_THRESHOLD": 3,
            "SOMABRAIN_CIRCUIT_RESET_INTERVAL": 60.0,
            "SOMABRAIN_CIRCUIT_COOLDOWN_INTERVAL": 0.0,
            # Salience / meta-brain knobs used by neuromod + amygdala paths
            "SOMABRAIN_SALIENCE_W_NOVELTY": 0.6,
            "SOMABRAIN_SALIENCE_W_ERROR": 0.4,
            "SOMABRAIN_SALIENCE_THRESHOLD_STORE": 0.5,
            "SOMABRAIN_SALIENCE_THRESHOLD_ACT": 0.7,
            "SOMABRAIN_SALIENCE_HYSTERESIS": 0.1,
            "SOMABRAIN_USE_SOFT_SALIENCE": False,
            "SOMABRAIN_SALIENCE_SOFT_TEMPERATURE": 0.1,
            "SOMABRAIN_SALIENCE_METHOD": "dense",
            "SOMABRAIN_SALIENCE_FD_WEIGHT": 0.25,
            "SOMABRAIN_SALIENCE_FD_ENERGY_FLOOR": 0.9,
            "SOMABRAIN_USE_META_BRAIN": False,
            "SOMABRAIN_META_GAIN": 0.1,
            "SOMABRAIN_META_LIMIT": 1.0,
        }
    )
    return cfg


def configure_unit_settings() -> None:
    """Boot Django for unit tests.

    Prefer the full project settings (same path as ``tests/conftest.py``) when
    the test credential is present so app/URL tests keep working. Fall back to
    a minimal configure() only when the full chain cannot boot.
    """
    from django.conf import settings as dj_settings

    if dj_settings.configured:
        for key, value in _required_settings().items():
            if not hasattr(dj_settings, key):
                setattr(dj_settings, key, value)
        return

    import os

    if os.environ.get("SOMABRAIN_MEMORY_HTTP_TOKEN"):
        try:
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somabrain.settings")
            import django

            django.setup()
            for key, value in _required_settings().items():
                if not hasattr(dj_settings, key):
                    setattr(dj_settings, key, value)
            return
        except Exception:
            pass

    dj_settings.configure(**_required_settings())
