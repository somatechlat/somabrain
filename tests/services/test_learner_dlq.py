import json
import os
from pathlib import Path

import pytest

from somabrain.services.learner_dlq import LearnerDLQ, DLQ_DEFAULT_PATH

pytestmark = [pytest.mark.unit, pytest.mark.skip_infra]


@pytest.fixture(autouse=True)
def _disable_infra(monkeypatch):
    monkeypatch.setenv("SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS", "0")


class DummyProducer:
    def __init__(self):
        self.records = []

    def produce(self, topic, payload):
        self.records.append((topic, payload))

    def flush(self):
        return


def test_dlq_falls_back_to_file(tmp_path, monkeypatch):
    # Force file path into tmp
    path = tmp_path / "dlq.jsonl"
    dlq = LearnerDLQ(producer=None, topic=None, path=str(path))
    dlq.record({"foo": "bar"}, "oops")
    assert path.exists()
    lines = path.read_text().strip().splitlines()
    assert lines and json.loads(lines[0])["reason"] == "oops"


def test_dlq_uses_producer_when_available(monkeypatch):
    prod = DummyProducer()
    dlq = LearnerDLQ(producer=prod, topic="dlq.topic")
    dlq.record({"foo": "bar"}, "oops")
    assert prod.records
    topic, payload = prod.records[0]
    assert topic == "dlq.topic"
    assert b"oops" in payload
pytestmark = pytest.mark.unit
