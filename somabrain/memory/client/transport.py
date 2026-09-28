from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

from somabrain.embed_dim import ensure_embedding_dim

from somabrain.core.infrastructure_defs import get_memory_http_endpoint
from somabrain.memory.transport import MemoryHTTPTransport

logger = logging.getLogger(__name__)


def _http_setting(attr: str, default_val: int) -> int:
    """Fetch HTTP client tuning knobs from shared settings with default."""
    if settings is not None:
        try:
            value = getattr(settings, attr, default_val)
            return int(value)
        except Exception:
            pass
    return default_val



def build_store_payload(
    *,
    coord: str,
    payload: Any,
    memory_type: str,
    embedding: list[float] | None = None,
    tenant_id: str | None = None,
) -> dict:
    """Build the POST /memories body, forwarding the seam fields.

    Regression guard: earlier versions rebuilt this body as
    {coord, payload, memory_type} only, silently stripping ``embedding`` and
    ``tenant_id`` so every stored memory fell back to hash vectors.
    """
    body: dict = {
        "coord": coord,
        "payload": payload,
        "memory_type": memory_type,
    }
    if embedding is not None:
        ensure_embedding_dim(embedding)
        body["embedding"] = list(embedding)
    if tenant_id:
        body["tenant_id"] = str(tenant_id)
    return body


def build_search_payload(
    *,
    query: str,
    top_k: int,
    embedding: list[float] | None = None,
    tenant_id: str | None = None,
) -> dict:
    """Build the POST /memories/search body, forwarding the query embedding."""
    body: dict = {
        "query": query,
        "top_k": top_k,
    }
    if embedding is not None:
        ensure_embedding_dim(embedding)
        body["embedding"] = list(embedding)
    if tenant_id:
        body["tenant_id"] = str(tenant_id)
    return body


class TransportMixin:
    """Handles HTTP transport for the Memory Client."""

    @property
    def _http_async(self) -> Any | None:
        """Async HTTP client for the *currently running* event loop.

        Read through to ``MemoryHTTPTransport.async_client`` rather than being
        cached on the instance: an ``httpx.AsyncClient`` is bound to the loop it
        first ran on, and ASGI servers replace that loop between requests. A
        cached client therefore raises ``RuntimeError: Event loop is closed`` on
        a later request.
        """
        transport = getattr(self, "_transport", None)
        if transport is None:
            return None
        return transport.async_client

    def _init_http(self) -> None:
        import httpx  # type: ignore

        # Default headers applied to all requests; per-request we add X-Request-ID
        headers = {}
        token_value = getattr(self.cfg, "memory_http_token", None) or getattr(
            self.cfg, "SOMABRAIN_MEMORY_HTTP_TOKEN", None
        )
        if token_value:
            headers["Authorization"] = f"Bearer {token_value}"
            headers.setdefault("X-API-Key", token_value)
            headers.setdefault("X-Auth-Token", token_value)

        # Propagate tenancy via standardized headers (best-effort)
        ns = str(getattr(self.cfg, "namespace", ""))
        if ns:
            headers["X-Soma-Namespace"] = ns
            try:
                tenant_guess = ns.split(":")[-1] if ":" in ns else ns
                headers["X-Soma-Tenant"] = tenant_guess
            except Exception:
                pass

        # Allow tuning via environment variables for production/dev use
        default_max = _http_setting("http_max_connections", 64)
        try:
            max_conns = int(getattr(settings, "http_max_connections", default_max))
        except Exception:
            max_conns = default_max
        default_keepalive = _http_setting("http_keepalive_connections", 32)
        try:
            keepalive = int(
                getattr(settings, "http_keepalive_connections", default_keepalive)
            )
        except Exception:
            keepalive = default_keepalive
        default_retries = _http_setting("http_retries", 1)
        try:
            retries = int(getattr(settings, "http_retries", default_retries))
        except Exception:
            retries = default_retries

        limits = None
        try:
            limits = httpx.Limits(
                max_connections=max_conns, max_keepalive_connections=keepalive
            )
        except Exception:
            limits = None

        # Allow overriding the HTTP memory endpoint via environment variable
        # Useful for tests or local development where a memory service runs on
        # a non-default port. Accept either a base URL or a full openapi.json
        # URL and normalise to the service base URL.
        candidate_base = get_memory_http_endpoint()
        env_base = getattr(settings, "memory_http_endpoint", None) or getattr(
            settings, "http_endpoint", None
        )
        if not env_base:
            env_base = candidate_base
        if env_base:
            try:
                env_base = str(env_base).strip()
                if "://" not in env_base and env_base.startswith("/"):
                    pass
                elif "://" not in env_base:
                    env_base = f"http://{env_base}"
                env_base = env_base.removesuffix("/openapi.json")
            except Exception:
                env_base = None
        base_url = str(getattr(self.cfg, "memory_http_endpoint", "") or "")
        if not base_url and env_base:
            base_url = env_base
        # Strict mode: memory endpoint is always required
        if not base_url:
            base_url = get_memory_http_endpoint() or ""
        if not base_url:
            raise RuntimeError("Memory HTTP endpoint required but not configured")
        # Final normalisation: ensure empty string remains empty
        base_url = base_url or ""

        # Diagnostic: record chosen endpoint for debugging in tests
        try:
            logger.debug("MemoryClient HTTP base_url=%r", base_url)
        except Exception:
            pass

        # Delegate client creation to the canonical MemoryHTTPTransport
        self._transport = MemoryHTTPTransport(
            base_url=base_url,
            headers=headers,
            limits=limits,
            retries=retries,
            logger=logger,
        )
        self._http = self._transport.client

        # Strict mode: memory is always required
        if self._http is None:
            raise RuntimeError(
                "MEMORY SERVICE REQUIRED but not reachable or endpoint unset. Set SOMABRAIN_MEMORY_HTTP_ENDPOINT in the environment."
            )
        # Enforce token presence by mode policy
        if self._http is not None and not token_value:
            try:
                logger.warning(
                    "Memory HTTP client initialized without token; proceeding without auth."
                )
            except Exception:
                pass

    def health(self) -> dict:
        """Best-effort backend health signal for local or http mode."""
        try:
            if self._http:
                # Try common health endpoints in order of preference.
                for path in ("/health", "/healthz", "/readyz"):
                    try:
                        r = self._http.get(path)
                        if int(getattr(r, "status_code", 0) or 0) == 200:
                            return {"http": True}
                    except Exception:
                        # Try next path
                        continue
                return {"http": False}
        except Exception:
            return {"ok": False}
        return {"ok": True}

    @staticmethod
    def _response_json(resp: Any) -> Any:
        try:
            if hasattr(resp, "json") and callable(resp.json):
                return resp.json()
        except Exception:
            return None
        return None

    def _http_post_with_retries_sync(
        self,
        endpoint: str,
        body: dict,
        headers: dict,
        *,
        max_retries: int = 2,
    ) -> tuple[bool, int, Any]:
        transport = getattr(self, "_transport", None)
        if transport is None:
            return False, 0, None
        return transport.post_with_retries_sync(
            endpoint, body, headers, max_retries=max_retries
        )

    async def _http_post_with_retries_async(
        self,
        endpoint: str,
        body: dict,
        headers: dict,
        *,
        max_retries: int = 2,
    ) -> tuple[bool, int, Any]:
        transport = getattr(self, "_transport", None)
        if transport is None:
            return False, 0, None
        return await transport.post_with_retries_async(
            endpoint, body, headers, max_retries=max_retries
        )

    def _store_http_sync(self, body: dict, headers: dict) -> tuple[bool, Any]:
        if self._http is None:
            return False, None

        coord = str(body.get("coord") or "")
        payload = body.get("payload") or {}
        memory_type = str(body.get("memory_type") or body.get("type") or "episodic")

        payload = build_store_payload(
            coord=coord,
            payload=payload,
            memory_type=memory_type,
            embedding=body.get("embedding"),
            tenant_id=body.get("tenant_id"),
        )

        success, _, data = self._http_post_with_retries_sync(
            "/memories", payload, headers
        )
        if success:
            return True, data

        return False, data

    async def _store_http_async(self, body: dict, headers: dict) -> tuple[bool, Any]:
        if self._http_async is None:
            return False, None

        coord = str(body.get("coord") or "")
        payload = body.get("payload") or {}
        memory_type = str(body.get("memory_type") or body.get("type") or "episodic")

        payload = build_store_payload(
            coord=coord,
            payload=payload,
            memory_type=memory_type,
            embedding=body.get("embedding"),
            tenant_id=body.get("tenant_id"),
        )

        success, _, data = await self._http_post_with_retries_async(
            "/memories", payload, headers
        )
        if success:
            return True, data

        return False, data

    def _store_bulk_http_sync(
        self, items: list[dict], headers: dict
    ) -> tuple[bool, int, Any]:
        if self._http is None:
            return False, 0, None
        all_ok = True
        responses: list[Any] = []
        for item in items:
            ok, resp = self._store_http_sync(item, headers)
            all_ok = all_ok and ok
            responses.append(resp)
        return all_ok, 200 if all_ok else 207, responses

    async def _store_bulk_http_async(
        self, items: list[dict], headers: dict
    ) -> tuple[bool, int, Any]:
        if self._http_async is None:
            return False, 0, None
        all_ok = True
        responses: list[Any] = []
        for item in items:
            ok, resp = await self._store_http_async(item, headers)
            all_ok = all_ok and ok
            responses.append(resp)
        return all_ok, 200 if all_ok else 207, responses
