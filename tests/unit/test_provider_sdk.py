from common.provider_sdk import discover_providers


def test_discover_providers_yaml(tmp_path, monkeypatch):
    p = tmp_path / "providers.yaml"
    p.write_text("test:\n  api_key: 'abc'\n")
    monkeypatch.setenv("PROVIDERS_PATH", str(p))
    got = discover_providers()
    assert got.get("test", {}).get("api_key") == "abc"


def test_discover_providers_json(tmp_path, monkeypatch):
    p = tmp_path / "providers.json"
    p.write_text('{"other": {"api_key": "xyz"}}')
    monkeypatch.setenv("PROVIDERS_PATH", str(p))
    got = discover_providers()
    assert got.get("other", {}).get("api_key") == "xyz"
