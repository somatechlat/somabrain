"""
Python client for the SomaBrain API with strict health‑aware behaviour.

This client is intended for use by upstream agents (e.g. SomaAgent01) that
must:

* Always talk to real SomaBrain endpoints (no mocks or local fallbacks).
* Never silently turn connectivity errors into "no results".
* Optionally avoid calling SomaBrain at all when it is known to be
  unavailable or not ready.

Example:

    from clients.python.somabrain_client import SomaBrainClient, SomaBrainUnavailableError

    from common.config.settings import settings as _settings
    api = SomaBrainClient(base_url=_settings.api_url, tenant="public")

    # Health-aware recall: only calls SomaBrain when health says "up".
    try:
        api.ensure_ready()  # Optional explicit check
        memories = api.recall("hello", top_k=3)
    except SomaBrainUnavailableError as exc:
        # Agent can handle degraded mode explicitly instead of faking "no memory".
        print("SomaBrain unavailable:", exc.status, exc.reason)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx


@dataclass
class SomaBrainHealth:
    """Snapshot of SomaBrain health from /health.

    Attributes:
        status: "up", "degraded", "down", or "unknown".
        last_checked: UNIX timestamp of the last health probe.
        reason: Short textual reason summarising why status is not "up".
        raw: Raw JSON body from /health when available.
    """

    status: str = "unknown"
    last_checked: float = 0.0
    reason: str = ""
    raw: Optional[Dict[str, Any]] = None


class SomaBrainUnavailableError(RuntimeError):
    """Raised when SomaBrain is not in an "up" state for strict callers."""

    def __init__(self, status: str, reason: str, health: Optional[SomaBrainHealth]):
        msg = f"SomaBrain status={status!r}: {reason}"
        super().__init__(msg)
        self.status = status
        self.reason = reason
        self.health = health


class SomaBrainClient:
    """Strict HTTP client for SomaBrain.

    All methods talk to the real SomaBrain HTTP API. The client exposes a
    health snapshot from `/health` and a helper `ensure_ready()` that
    callers can use to guard memory-dependent logic.
    """

    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        tenant: Optional[str] = None,
        *,
        health_ttl_s: float = 5.0,
        timeout_s: float = 10.0,
    ):
        self.base = base_url.rstrip("/")
        self.headers: Dict[str, str] = {"Content-Type": "application/json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        if tenant:
            self.headers["X-Tenant-ID"] = str(tenant)
        self._http = httpx.Client(
            base_url=self.base, headers=self.headers, timeout=timeout_s
        )
        self._health = SomaBrainHealth(status="unknown")
        self._health_ttl_s = max(0.0, float(health_ttl_s))

    # ------------------------------------------------------------------
    # Health handling
    # ------------------------------------------------------------------

    def _classify_health(self, body: Dict[str, Any]) -> SomaBrainHealth:
        """Classify /health response into up/degraded/down from agent POV."""

        ok = bool(body.get("ok", False))
        ready = bool(body.get("ready", False))
        memory_ok = bool(body.get("memory_ok", False))
        kafka_ok = bool(body.get("kafka_ok", False))
        postgres_ok = bool(body.get("postgres_ok", False))
        opa_ok = bool(body.get("opa_ok", True))  # may be optional

        status = "up"
        reasons: List[str] = []

        if not ok or not ready:
            status = "degraded"
            reasons.append("ok/ready=false")
        if not memory_ok:
            status = "degraded"
            reasons.append("memory_ok=false")
        if not kafka_ok:
            status = "degraded"
            reasons.append("kafka_ok=false")
        if not postgres_ok:
            status = "degraded"
            reasons.append("postgres_ok=false")
        if not opa_ok:
            status = "degraded"
            reasons.append("opa_ok=false")

        reason = ",".join(reasons) if reasons else ""
        return SomaBrainHealth(
            status=status,
            last_checked=time.time(),
            reason=reason,
            raw=body,
        )

    def refresh_health(self, *, force: bool = False) -> SomaBrainHealth:
        """Refresh the cached health snapshot from `/health`.

        When `force` is False, uses the cached value if it is recent
        (within `health_ttl_s` seconds).
        """
        now = time.time()
        if (
            not force
            and self._health.last_checked > 0
            and now - self._health.last_checked <= self._health_ttl_s
        ):
            return self._health

        try:
            r = self._http.get("/health")
        except Exception as exc:
            self._health = SomaBrainHealth(
                status="down",
                last_checked=now,
                reason=f"http_error:{exc!r}",
                raw=None,
            )
            return self._health

        if r.status_code != 200:
            self._health = SomaBrainHealth(
                status="down",
                last_checked=now,
                reason=f"http_status:{r.status_code}",
                raw=None,
            )
            return self._health

        try:
            body = r.json()
            self._health = self._classify_health(body)
        except Exception as exc:
            self._health = SomaBrainHealth(
                status="down",
                last_checked=now,
                reason=f"health_parse_error:{exc!r}",
                raw=None,
            )
        return self._health

    @property
    def health(self) -> SomaBrainHealth:
        """Return the current cached health snapshot (may be stale)."""
        return self._health

    def ensure_ready(self) -> None:
        """Raise SomaBrainUnavailableError if SomaBrain is not "up".

        Upstream agents should call this before performing critical
        SomaBrain-dependent work, or use it inside their own helpers.
        """
        h = self.refresh_health()
        if h.status != "up":
            raise SomaBrainUnavailableError(h.status, h.reason or "not ready", h)

    # ------------------------------------------------------------------
    # Core API methods
    # ------------------------------------------------------------------

    def remember(
        self, payload: Dict[str, Any], coord: Optional[str] = None
    ) -> Dict[str, Any]:
        """Store a memory payload in SomaBrain.

        This method always sends the request to SomaBrain; callers that
        want strict degraded-mode behaviour should call `ensure_ready()`
        beforehand.
        """
        body = {"coord": coord, "payload": payload}
        r = self._http.post("/remember", json=body)
        r.raise_for_status()
        return r.json()

    def recall(
        self, query: str, top_k: int = 3, universe: Optional[str] = None
    ) -> Dict[str, Any]:
        """Recall memories relevant to `query` from SomaBrain.

        This method always calls SomaBrain. Agents that must never hit
        SomaBrain while it is unavailable should guard it with
        `ensure_ready()` or `refresh_health()` and their own policy.
        """
        body: Dict[str, Any] = {"query": query, "top_k": int(top_k)}
        if universe:
            body["universe"] = universe
        r = self._http.post("/recall", json=body)
        r.raise_for_status()
        return r.json()

    def link(
        self,
        *,
        from_key: Optional[str] = None,
        to_key: Optional[str] = None,
        from_coord: Optional[str] = None,
        to_coord: Optional[str] = None,
        type: Optional[str] = None,
        weight: float = 1.0,
        universe: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a semantic link between memories in SomaBrain."""
        body: Dict[str, Any] = {
            "from_key": from_key,
            "to_key": to_key,
            "from_coord": from_coord,
            "to_coord": to_coord,
            "type": type,
            "weight": weight,
            "universe": universe,
        }
        r = self._http.post("/link", json=body)
        r.raise_for_status()
        return r.json()

    def plan_suggest(
        self,
        task_key: str,
        *,
        max_steps: Optional[int] = None,
        rel_types: Optional[List[str]] = None,
        universe: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Suggest a plan over semantic links starting from `task_key`."""
        body: Dict[str, Any] = {"task_key": task_key}
        if max_steps is not None:
            body["max_steps"] = int(max_steps)
        if rel_types is not None:
            body["rel_types"] = rel_types
        if universe:
            body["universe"] = universe
        r = self._http.post("/plan/suggest", json=body)
        r.raise_for_status()
        return r.json()
