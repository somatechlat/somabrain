from fastapi.testclient import TestClient

import somabrain.app as app_module
import somabrain.metrics as M

client = TestClient(app_module.app)


def test_reward_gate_deny_metric_increment():
    # Ensure utility guard will reject (negative utility) via low confidence
    headers = {"X-Model-Confidence": "0.01", "X-Tenant-ID": "demo"}
    before = M.REWARD_DENY_TOTAL._value.get()
    resp = client.get("/demo", headers=headers)
    # Expect 403 from utility guard (and reward gate)
    assert resp.status_code == 403
    after = M.REWARD_DENY_TOTAL._value.get()
    assert after == before + 1
