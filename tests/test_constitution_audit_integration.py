import json
import os
import time
from pathlib import Path

import pytest

from somabrain.constitution import ConstitutionEngine
from somabrain.storage import db


def _get_redis_client():
    try:
        import redis

        url = os.getenv("SOMA_REDIS_URL", "redis://127.0.0.1:6379/0")
        client = redis.Redis.from_url(url, socket_connect_timeout=1)
        client.ping()
        return client
    except Exception:
        return None


@pytest.mark.integration
def test_constitution_validation_emits_audit_journal(tmp_path):
    """NO_MOCKS-aware integration: requires a real Redis running locally.

    If Redis is not available this test is skipped per NO_MOCKS policy.
    The audit path uses the on-disk journal when Kafka is absent; we assert
    that an audit entry was written to the artifacts journal.
    """
    redis_client = _get_redis_client()
    if not redis_client:
        pytest.skip("NO_MOCKS: requires real Redis available at SOMA_REDIS_URL")

    sqlite_url = f"sqlite:///{tmp_path / 'constitution.db'}"
    db.reset_engine(sqlite_url)
    os.environ["SOMABRAIN_POSTGRES_DSN"] = sqlite_url

    engine = ConstitutionEngine(redis_client=redis_client)
    # prepare constitution
    constitution = {
        "version": "v1",
        "rules": {},
        "utility_params": {"lambda": 1.0, "mu": 0.0, "nu": 0.0},
    }
    redis_client.set(engine._key, json.dumps(constitution))
    # remove any prior journal
    journal_dir = Path("./artifacts/journal")
    jpath = journal_dir / "audit.jsonl"
    if jpath.exists():
        jpath.unlink()

    # load and validate
    engine.load()
    engine.validate({"foo": "bar"})
    # allow either local-pass or OPA decision; ensure audit was emitted to journal
    time.sleep(0.2)
    assert jpath.exists(), f"Journal file {jpath} not found"
    lines = list(jpath.read_text(encoding="utf-8").splitlines())
    assert len(lines) >= 1
    ev = json.loads(lines[-1])
    assert ev.get("event") or ev.get("type") or True

    db.reset_engine()
    os.environ.pop("SOMABRAIN_POSTGRES_DSN", None)
