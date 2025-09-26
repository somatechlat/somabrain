from fastapi.testclient import TestClient

import somabrain.app as app_module

client = TestClient(app_module.app)


def test_demo_endpoint_allows_positive_utility():
    # High confidence (>1) yields positive utility (log > 0)
    headers = {"X-Model-Confidence": "2.0", "X-Tenant-ID": "demo"}
    resp = client.get("/demo", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"detail": "demo endpoint accessed"}


def test_demo_endpoint_denies_negative_utility():
    # Low confidence yields negative utility -> 403
    headers = {"X-Model-Confidence": "0.01", "X-Tenant-ID": "demo"}
    resp = client.get("/demo", headers=headers)
    assert resp.status_code == 403
