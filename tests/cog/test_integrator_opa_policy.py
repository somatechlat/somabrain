from __future__ import annotations

from typing import Any, Dict, Optional


import pytest

from somabrain.services.integrator_hub import IntegratorHub


class _Resp:
    def __init__(self, status: int, body: Dict[str, Any]):
        self.status_code = status
        self._body = body

    def json(self) -> Dict[str, Any]:
        return self._body


def _mk_hub(opa_url: str = "http://127.0.0.1:8181", policy: str = "soma.policy.integrator") -> IntegratorHub:
    hub = IntegratorHub()
    # override internal OPA fields for testing
    hub._opa_url = opa_url
    hub._opa_policy = policy
    hub._opa_fail_closed = False
    return hub


def test_opa_allow_no_change(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, json: Optional[Dict[str, Any]] = None, timeout: float = 1.5) -> _Resp:  # type: ignore[override]
        return _Resp(200, {"result": {"allow": True}})

    import requests  # type: ignore

    monkeypatch.setattr(requests, "post", fake_post)  # type: ignore

    hub = _mk_hub()
    allowed, new_leader, note = hub._opa_decide(
        tenant="public",
        leader="state",
        weights={"state": 0.6, "agent": 0.3, "action": 0.1},
        ev={"domain": "state"},
    )
    assert allowed is True
    assert new_leader is None


def test_opa_allow_with_leader_change(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, json: Optional[Dict[str, Any]] = None, timeout: float = 1.5) -> _Resp:  # type: ignore[override]
        return _Resp(200, {"result": {"allow": True, "leader": "action"}})

    import requests  # type: ignore

    monkeypatch.setattr(requests, "post", fake_post)  # type: ignore

    hub = _mk_hub()
    allowed, new_leader, note = hub._opa_decide(
        tenant="public",
        leader="state",
        weights={"state": 0.2, "agent": 0.1, "action": 0.7},
        ev={"domain": "state"},
    )
    assert allowed is True
    assert new_leader == "action"


def test_opa_deny_open(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, json: Optional[Dict[str, Any]] = None, timeout: float = 1.5) -> _Resp:  # type: ignore[override]
        return _Resp(200, {"result": {"allow": False}})

    import requests  # type: ignore

    monkeypatch.setattr(requests, "post", fake_post)  # type: ignore

    hub = _mk_hub()
    hub._opa_fail_closed = False
    allowed, new_leader, note = hub._opa_decide(
        tenant="blocked",
        leader="state",
        weights={"state": 0.4, "agent": 0.3, "action": 0.3},
        ev={"domain": "state"},
    )
    # Open mode: treat deny as allowed at caller level, but integrator uses this to drop only if fail-closed
    assert allowed is False
    assert new_leader is None
