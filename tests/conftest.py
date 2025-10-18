from __future__ import annotations

import os

import pytest

from somabrain.config import reload_config


@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    defaults = {
        "SOMABRAIN_STRICT_REAL": "1",
        "SOMABRAIN_KAFKA_PORT": "9092",
        "SOMABRAIN_REDIS_PORT": "6379",
        "SOMABRAIN_LEARNING_LOOP_ENABLED": "1",
    }

    previous = {key: os.environ.get(key) for key in defaults}
    for key, value in defaults.items():
        os.environ.setdefault(key, value)

    reload_config()
    yield

    for key, old_value in previous.items():
        if old_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old_value
    reload_config()
