"""Helpers for selecting and probing SomaBrain test targets.

This module centralises the logic for running live-stack regression tests against
multiple infrastructure targets (local compose stack, remote staging, etc.).
It exposes a small ``TargetConfig`` value object plus an iterator that yields
all targets discovered from the environment. Tests can parametrize over these
configs and skip gracefully when a target is unavailable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Iterator
from urllib.parse import urlparse

import requests

from somabrain.infrastructure import (
    get_api_base_url,
    get_memory_http_endpoint,
    get_redis_url,
    require,
)

try:  # Optional dependency in some environments.
    import redis
except Exception:  # pragma: no cover - redis not always installed.
    redis = None  # type: ignore


@dataclass(frozen=True)
class TargetConfig:
    """Test target metadata.

    Attributes
    ----------
    label:
        Friendly identifier rendered in pytest parametrised IDs (``local`` or
        ``live`` for example).
    api_base:
        Fully qualified base URL for the SomaBrain API (scheme + host + port).
    memory_base:
        Base URL for the external SomaMemory service.
    redis_url:
        Optional Redis connection URL (``redis://host:port/db``). When omitted,
        Redis connectivity checks are skipped.
    tenant:
        Optional tenant identifier injected through ``X-Tenant-ID`` when set.
    postgres_dsn:
        Optional psycopg compatible connection string used by cognition tests.
        When omitted the tests fall back to their environment-specific
        resolution logic and may skip if Postgres is unreachable.
    bypass_lock_checks:
        When ``True`` the target is always attempted even if health probes fail.
        Tests are still free to assert reachability; this flag only disables the
        eager skip that would normally occur before exercising the endpoints.
    """

    label: str
    api_base: str
    memory_base: str
    redis_url: str | None
    tenant: str | None = None
    postgres_dsn: str | None = None
    bypass_lock_checks: bool = False

    def id(self) -> str:
        return self.label

    # ---- Probing helpers -------------------------------------------------

    def _probe_api(self) -> tuple[bool, str | None]:
        url = f"{self.api_base.rstrip('/')}/health"
        try:
            resp = requests.get(url, timeout=3)
        except Exception as exc:  # pragma: no cover - network dependent
            return False, f"API unreachable at {url}: {exc}"
        if resp.status_code != 200:
            return False, f"API health returned {resp.status_code} for {url}"
        if not resp.json().get("ok", False):
            return False, f"API health check not OK for {self.label}"
        return True, None

    def _probe_memory(self) -> tuple[bool, str | None]:
        url = f"{self.memory_base.rstrip('/')}/health"
        try:
            resp = requests.get(url, timeout=3)
        except Exception as exc:  # pragma: no cover - network dependent
            return False, f"Memory unreachable at {url}: {exc}"
        if resp.status_code != 200:
            return False, f"Memory health returned {resp.status_code} for {url}"
        if not resp.json().get("ok", False):
            return False, f"Memory health check not OK for {self.label}"
        return True, None

    def _probe_redis(self) -> tuple[bool, str | None]:
        if not self.redis_url:
            return True, None
        if redis is None:  # pragma: no cover - redis client missing
            return False, "redis library unavailable to probe redis_url"
        parsed = urlparse(self.redis_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 6379
        db = int(parsed.path[1:] or 0)
        try:
            client = redis.Redis(host=host, port=port, db=db, socket_connect_timeout=1)
            client.ping()
        except Exception as exc:  # pragma: no cover - network dependent
            return False, f"Redis unreachable at {self.redis_url}: {exc}"
        return True, None

    def probe(self) -> tuple[bool, list[str]]:
        """Return reachability status plus failure reasons."""

        if self.bypass_lock_checks:
            return True, []

        checks = (self._probe_api, self._probe_memory, self._probe_redis)
        ok = True
        reasons: list[str] = []
        for fn in checks:
            success, reason = fn()
            if not success and reason:
                ok = False
                reasons.append(reason)
        return ok, reasons


def _env_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.lower() in {"1", "true", "yes", "on"}


def _default_target() -> TargetConfig:
    api_base = require(
        get_api_base_url() or os.getenv("SOMA_API_URL"),
        message="Set SOMABRAIN_API_URL (see .env) before running tests.",
    )
    memory_base = require(
        get_memory_http_endpoint()
        or os.getenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT")
        or os.getenv("MEMORY_SERVICE_URL"),
        message="Set SOMABRAIN_MEMORY_HTTP_ENDPOINT (see .env) before running tests.",
    )
    redis_url = (
        get_redis_url()
        or os.getenv("SOMABRAIN_REDIS_URL")
        or os.getenv("REDIS_URL")
    )
    return TargetConfig(
        label="local",
        api_base=api_base,
        memory_base=memory_base,
        redis_url=redis_url,
        tenant=os.getenv("SOMABRAIN_DEFAULT_TENANT"),
        postgres_dsn=os.getenv("SOMABRAIN_POSTGRES_DSN"),
        bypass_lock_checks=_env_truthy(os.getenv("SOMA_API_URL_LOCK_BYPASS")),
    )


def _live_target_from_env() -> TargetConfig | None:
    api = os.getenv("SOMABRAIN_LIVE_API_URL")
    if not api:
        return None
    memory = os.getenv("SOMABRAIN_LIVE_MEMORY_HTTP_ENDPOINT", api)
    redis_url = os.getenv("SOMABRAIN_LIVE_REDIS_URL")
    tenant = os.getenv("SOMABRAIN_LIVE_TENANT")
    postgres = os.getenv("SOMABRAIN_LIVE_POSTGRES_DSN")
    bypass = _env_truthy(os.getenv("SOMABRAIN_LIVE_FORCE"))
    return TargetConfig(
        label=os.getenv("SOMABRAIN_LIVE_LABEL", "live"),
        api_base=api,
        memory_base=memory,
        redis_url=redis_url,
        tenant=tenant,
        postgres_dsn=postgres,
        bypass_lock_checks=bypass,
    )


def iter_test_targets() -> Iterator[TargetConfig]:
    """Yield the configured test targets.

    The iterator always yields the local target first, followed by an optional
    live configuration when ``SOMABRAIN_LIVE_API_URL`` is defined.
    Additional future sources (e.g. JSON manifests) can be spliced in here.
    """

    yield _default_target()
    live = _live_target_from_env()
    if live is not None:
        yield live


def list_test_targets() -> list[TargetConfig]:
    """Collect the iterator into a list for fixture parametrisation."""

    return list(iter_test_targets())


def target_ids(targets: Iterable[TargetConfig]) -> list[str]:
    return [t.id() for t in targets]
