from fastapi.testclient import TestClient

import somabrain.app as app_module
import somabrain.metrics as M

client = TestClient(app_module.app)


def test_reward_gate_allow_metric_increment():
    # Capture current counter value
    before = M.REWARD_ALLOW_TOTAL._value.get()
    resp = client.get("/health")
    assert resp.status_code == 200
    after = M.REWARD_ALLOW_TOTAL._value.get()
    assert after == before + 1
