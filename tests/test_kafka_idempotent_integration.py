import os
from importlib import import_module

import pytest


def is_kafka_available():
    return bool(os.environ.get("SOMA_KAFKA_URL"))


@pytest.mark.skipif(not is_kafka_available(), reason="SOMA_KAFKA_URL not set")
def test_kafka_idempotent_smoke():
    # Import the smoke runner from scripts and execute; assert it returns 0
    mod = import_module("scripts.kafka_idempotence_smoke")
    ret = mod.smoke_run()
    assert ret == 0
