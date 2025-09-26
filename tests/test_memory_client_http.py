import sys


def test_http_client_endpoints_and_headers(monkeypatch):
    sys.path.insert(0, ".")
    from somabrain.config import Config, MemoryHTTPConfig
    from somabrain.memory_client import MemoryClient

    # Capture requests and created clients
    calls = []
    clients = []

    class FakeResp:
        def __init__(self, status_code=200, json_data=None):
            self.status_code = status_code
            self._json = json_data or []

        def json(self):
            return self._json

    class FakeClient:
        def __init__(self, *_, **kwargs):
            self.headers = kwargs.get("headers", {})
            clients.append(self)

        def get(self, path):
            calls.append(("GET", path, {}, None))
            return FakeResp(200)

        def post(self, path, json=None, headers=None):
            calls.append(("POST", path, headers or {}, json or {}))
            # Simulate 404 for /remember first, to trigger fallback to /store
            if path == "/remember":
                return FakeResp(404)
            if path == "/recall":
                return FakeResp(200, json_data=[{"ok": True}])
            return FakeResp(200)

    import types as _types

    fake_httpx = _types.ModuleType("httpx")
    setattr(fake_httpx, "Client", FakeClient)
    setattr(fake_httpx, "AsyncClient", FakeClient)
    sys.modules["httpx"] = fake_httpx

    cfg = Config()
    cfg.namespace = "ns:tenantA"
    cfg.http = MemoryHTTPConfig(endpoint="http://example", token="tkn")

    mc = MemoryClient(cfg)
    # Remember should try /remember then fallback to /store
    mc.remember("k1", {"task": "t"})
    # Recall should include universe and X-Request-ID
    hits = mc.recall("q", top_k=1)
    assert isinstance(hits, list)

    # Validate calls order and headers presence
    methods_paths = [(m, p) for (m, p, _, __) in calls]
    assert ("POST", "/remember") in methods_paths
    assert ("POST", "/store") in methods_paths
    assert ("POST", "/recall") in methods_paths

    # Check per-request recall headers include X-Request-ID
    # Find the recall call headers
    recall_headers = None
    for m, p, h, _ in calls:
        if m == "POST" and p == "/recall":
            recall_headers = h
            break
    assert recall_headers is not None
    assert "X-Request-ID" in recall_headers
    # Default headers set on the client include namespace and tenant
    assert clients and isinstance(clients[0], FakeClient)
    default_headers = clients[0].headers
    assert "X-Soma-Namespace" in default_headers
    assert "X-Soma-Tenant" in default_headers
    assert "Authorization" in default_headers
