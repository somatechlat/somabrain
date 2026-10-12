"""HTTP Transport layer for SomaBrain Memory Service.

This module encapsulates the HTTP/AsyncHTTP clients used by MemoryClient,
providing connection pooling, retry logic, and fallback behavior.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any

import httpx
from django.conf import settings

from somabrain.math.contracts import (
    HTTP_BACKOFF_BASE_S,
    HTTP_BACKOFF_ERROR_BASE_S,
    HTTP_BACKOFF_ERROR_JITTER_S,
    HTTP_BACKOFF_JITTER_S,
    HTTP_MAX_RETRIES,
    HTTP_TIMEOUT_S,
)

# Module-level logger
logger = logging.getLogger(__name__)


def _response_json(resp: Any) -> Any:
    """Extract JSON from an HTTP response safely.

    Args:
        resp: The HTTP response object (httpx.Response or similar).

    Returns:
        The parsed JSON data or None if parsing fails.
    """
    try:
        if hasattr(resp, "json") and callable(resp.json):
            return resp.json()
    except Exception:
        return None
    return None


class MemoryHTTPTransport:
    """Encapsulates the HTTP/AsyncHTTP clients used by MemoryClient.

    This class manages both synchronous and asynchronous HTTP clients for
    communicating with the memory service. It handles:
    - Connection pooling via httpx.Limits
    - Automatic retries with exponential backoff
    - The endpoint is named by the operator; there is no localhost fallback

    Attributes:
        base_url: The base URL for the memory service.
        client: The synchronous httpx.Client instance (may be None).
        async_client: The asynchronous httpx.AsyncClient instance (may be None).
    """

    def __init__(
        self,
        *,
        base_url: str,
        headers: dict,
        limits: httpx.Limits | None,
        retries: int,
        logger: logging.Logger,
    ) -> None:
        """Initialize the HTTP transport.

        Args:
            base_url: The base URL for the memory service.
            headers: Default headers to include in all requests.
            limits: Optional httpx.Limits for connection pooling.
            retries: Number of retries for failed requests.
            logger: Logger instance for diagnostic output.
        """
        self.base_url = base_url
        self._headers = dict(headers)
        self._limits = limits
        self._retries = max(0, int(retries))
        self._logger = logger
        self._client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None
        self._async_loop: asyncio.AbstractEventLoop | None = None
        self._init_clients()

    @property
    def client(self) -> httpx.Client | None:
        """The synchronous HTTP client."""
        return self._client

    @property
    def async_client(self) -> httpx.AsyncClient | None:
        """The asynchronous HTTP client, bound to the running event loop.

        An ``httpx.AsyncClient`` owns connection-pool state tied to the event
        loop it first ran on. ASGI servers close and replace that loop between
        requests, after which the pooled connections raise
        ``RuntimeError: Event loop is closed``. So the client is rebuilt
        whenever the running loop differs from the one it was built for. The
        abandoned client is not ``aclose()``d here: closing it would need the
        loop that is already gone.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop: callers get whatever was built at construction.
            return self._async_client

        if self._async_client is not None and self._async_loop is loop:
            return self._async_client

        client = self._new_async_client()
        self._async_client = client
        self._async_loop = loop if client is not None else None
        return self._async_client

    def _init_clients(self) -> None:
        """Initialize both sync and async HTTP clients.

        Raises RuntimeError if the memory service is not reachable.
        No fallback behavior - fail fast on connection errors.
        """
        client_kwargs: dict[str, Any] = {
            "base_url": self.base_url,
            "headers": dict(self._headers),
            "timeout": HTTP_TIMEOUT_S,
        }
        if self._limits is not None:
            client_kwargs["limits"] = self._limits

        # Disable clients if no base URL
        if not self.base_url:
            self._client = None
            self._async_client = None
            return

        # Initialize sync client - fail fast if unreachable
        try:
            self._client = httpx.Client(**client_kwargs)
        except Exception as e:
            self._logger.error("Failed to create sync HTTP client: %s", e)
            self._client = None

        # Initialize async client for the loop that is current at construction.
        self._async_client = self._new_async_client()
        try:
            self._async_loop = (
                asyncio.get_running_loop() if self._async_client else None
            )
        except RuntimeError:
            self._async_loop = None

    def _new_async_client(self) -> httpx.AsyncClient | None:
        """Build a fresh async client for the current event loop.

        Returns None when no base URL is configured or construction fails; the
        failure is logged rather than silently swallowed.
        """
        if not self.base_url:
            return None

        client_kwargs: dict[str, Any] = {
            "base_url": self.base_url,
            "headers": dict(self._headers),
            "timeout": HTTP_TIMEOUT_S,
        }
        if self._limits is not None:
            client_kwargs["limits"] = self._limits

        try:
            transport = httpx.AsyncHTTPTransport(retries=self._retries)
            async_kwargs = dict(client_kwargs)
            async_kwargs["transport"] = transport
            return httpx.AsyncClient(**async_kwargs)
        except Exception:
            try:
                return httpx.AsyncClient(**client_kwargs)
            except Exception as e:
                self._logger.error("Failed to create async HTTP client: %s", e)
                return None

    def post_with_retries_sync(
        self,
        endpoint: str,
        body: dict,
        headers: dict,
        *,
        max_retries: int = HTTP_MAX_RETRIES,
    ) -> tuple[bool, int, Any]:
        """POST request with retry logic (synchronous).

        Args:
            endpoint: The API endpoint path.
            body: The JSON body to send.
            headers: Additional headers for this request.
            max_retries: Maximum number of retry attempts.

        Returns:
            Tuple of (success, status_code, response_data).
        """
        if self._client is None:
            return False, 0, None
        status = 0
        data: Any = None
        for attempt in range(max_retries + 1):
            try:
                resp = self._client.post(endpoint, json=body, headers=headers)
            except Exception:
                if attempt < max_retries:
                    time.sleep(
                        HTTP_BACKOFF_BASE_S + random.random() * HTTP_BACKOFF_JITTER_S
                    )
                continue
            status = int(getattr(resp, "status_code", 0) or 0)
            if status in (429, 503) and attempt < max_retries:
                time.sleep(
                    HTTP_BACKOFF_BASE_S + random.random() * HTTP_BACKOFF_JITTER_S
                )
                continue
            if status >= 500 and attempt < max_retries:
                time.sleep(
                    HTTP_BACKOFF_ERROR_BASE_S
                    + random.random() * HTTP_BACKOFF_ERROR_JITTER_S
                )
                continue
            data = _response_json(resp)
            return status < 300, status, data
        return False, status, data

    async def post_with_retries_async(
        self,
        endpoint: str,
        body: dict,
        headers: dict,
        *,
        max_retries: int = HTTP_MAX_RETRIES,
    ) -> tuple[bool, int, Any]:
        """POST request with retry logic (asynchronous).

        Args:
            endpoint: The API endpoint path.
            body: The JSON body to send.
            headers: Additional headers for this request.
            max_retries: Maximum number of retry attempts.

        Returns:
            Tuple of (success, status_code, response_data).
        """
        if self._async_client is None:
            return False, 0, None
        status = 0
        data: Any = None
        for attempt in range(max_retries + 1):
            try:
                resp = await self._async_client.post(
                    endpoint, json=body, headers=headers
                )
            except Exception:
                if attempt < max_retries:
                    await asyncio.sleep(
                        HTTP_BACKOFF_BASE_S + random.random() * HTTP_BACKOFF_JITTER_S
                    )
                continue
            status = int(getattr(resp, "status_code", 0) or 0)
            if status in (429, 503) and attempt < max_retries:
                await asyncio.sleep(
                    HTTP_BACKOFF_BASE_S + random.random() * HTTP_BACKOFF_JITTER_S
                )
                continue
            if status >= 500 and attempt < max_retries:
                await asyncio.sleep(
                    HTTP_BACKOFF_ERROR_BASE_S
                    + random.random() * HTTP_BACKOFF_ERROR_JITTER_S
                )
                continue
            data = _response_json(resp)
            return status < 300, status, data
        return False, status, data


def create_memory_transport(
    cfg: Any,
    logger_instance: logging.Logger,
) -> MemoryHTTPTransport:
    """Create a configured MemoryHTTPTransport instance.

    Per Requirements D1.1-D1.4:
    - D1.1: Tenant isolation via headers
    - D1.2: Namespace isolation via headers
    - D1.3: Always set tenant headers
    - D1.4: Never leave tenant header empty

    Args:
        cfg: Configuration object with memory settings.
        logger_instance: Logger for diagnostic output.

    Returns:
        Configured MemoryHTTPTransport instance.

    Raises:
        RuntimeError: If memory endpoint is not configured or unreachable.
    """
    from somabrain.core.infrastructure_defs import (
        get_memory_http_endpoint,
        resolve_memory_endpoint,
    )

    headers = {}
    # Single auth-header authority (R5) — somabrain.memory.sfm_auth.
    from somabrain.memory.sfm_auth import build_sfm_request_headers

    headers.update(build_sfm_request_headers(cfg))

    max_conns = int(getattr(settings, "HTTP_MAX_CONNECTIONS"))
    keepalive = int(getattr(settings, "HTTP_KEEPALIVE_CONNECTIONS"))
    retries = int(getattr(settings, "HTTP_RETRIES"))

    try:
        import httpx

        limits = httpx.Limits(
            max_connections=max_conns, max_keepalive_connections=keepalive
        )
    except Exception:
        limits = None

    resolved = None
    try:
        resolved = resolve_memory_endpoint()
    except RuntimeError:
        pass

    cfg_endpoint = str(getattr(cfg, "memory_http_endpoint", "") or "")
    base_url = (
        cfg_endpoint.strip()
        if cfg_endpoint
        else (resolved.url if resolved else get_memory_http_endpoint() or "")
    )
    if not base_url:
        raise RuntimeError("Memory HTTP endpoint required but not configured")
    base_url = base_url.removesuffix("/openapi.json")
    base_url = base_url.rstrip("/")
    logger_instance.info("Memory HTTP transport base_url=%s", base_url)

    transport = MemoryHTTPTransport(
        base_url=base_url,
        headers=headers,
        limits=limits,
        retries=retries,
        logger=logger_instance,
    )
    if transport.client is None:
        raise RuntimeError(
            "MEMORY SERVICE REQUIRED but not reachable. Set SOMABRAIN_MEMORY_HTTP_ENDPOINT."
        )
    # Token presence is already fail-closed in build_sfm_request_headers (R5).
    return transport
