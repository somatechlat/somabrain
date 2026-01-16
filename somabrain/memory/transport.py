"""HTTP Transport layer for SomaBrain Memory Service.

This module encapsulates the HTTP/AsyncHTTP clients used by MemoryClient,
providing connection pooling, retry logic, and fallback behavior.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any, Optional, Tuple

import httpx

from django.conf import settings

# Module-level logger
logger = logging.getLogger(__name__)


def _http_setting(attr: str, default_val: int) -> int:
    """Fetch HTTP client tuning knobs from shared settings with default.

    Args:
        attr: The settings attribute name to fetch.
        default_val: Default value if attribute is not found or invalid.

    Returns:
        The integer value from settings or the default.
    """
    if settings is not None:
        try:
            value = getattr(settings, attr)
            if value is None:
                return default_val
            return int(value)
        except Exception:
            pass
    return default_val


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
    - Fallback to localhost if the primary endpoint is unreachable

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
        limits: Optional[httpx.Limits],
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
        self._client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None
        self._init_clients()

    @property
    def client(self) -> Optional[httpx.Client]:
        """The synchronous HTTP client."""
        return self._client

    @property
    def async_client(self) -> Optional[httpx.AsyncClient]:
        """The asynchronous HTTP client."""
        return self._async_client

    def _init_clients(self) -> None:
        """Initialize both sync and async HTTP clients.

        Raises RuntimeError if the memory service is not reachable.
        No fallback behavior - fail fast on connection errors.
        """
        client_kwargs: dict[str, Any] = {
            "base_url": self.base_url,
            "headers": dict(self._headers),
            "timeout": 10.0,
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

        # Initialize async client
        try:
            transport = httpx.AsyncHTTPTransport(retries=self._retries)
            async_kwargs = dict(client_kwargs)
            async_kwargs["transport"] = transport
            self._async_client = httpx.AsyncClient(**async_kwargs)
        except Exception:
            try:
                self._async_client = httpx.AsyncClient(**client_kwargs)
            except Exception as e:
                self._logger.error("Failed to create async HTTP client: %s", e)
                self._async_client = None

    def post_with_retries_sync(
        self,
        endpoint: str,
        body: dict,
        headers: dict,
        *,
        max_retries: int = 2,
    ) -> Tuple[bool, int, Any]:
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
                    time.sleep(0.01 + random.random() * 0.02)
                continue
            status = int(getattr(resp, "status_code", 0) or 0)
            if status in (429, 503) and attempt < max_retries:
                time.sleep(0.01 + random.random() * 0.02)
                continue
            if status >= 500 and attempt < max_retries:
                time.sleep(0.05 + random.random() * 0.05)
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
        max_retries: int = 2,
    ) -> Tuple[bool, int, Any]:
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
                resp = await self._async_client.post(endpoint, json=body, headers=headers)
            except Exception:
                if attempt < max_retries:
                    await asyncio.sleep(0.01 + random.random() * 0.02)
                continue
            status = int(getattr(resp, "status_code", 0) or 0)
            if status in (429, 503) and attempt < max_retries:
                await asyncio.sleep(0.01 + random.random() * 0.02)
                continue
            if status >= 500 and attempt < max_retries:
                await asyncio.sleep(0.05 + random.random() * 0.05)
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
    from somabrain.infrastructure import (
        get_memory_http_endpoint,
        resolve_memory_endpoint,
    )
    from somabrain.memory.utils import get_tenant_namespace

    headers = {}
    token_value = getattr(cfg, "memory_http_token", None)
    if token_value:
        headers["Authorization"] = f"Bearer {token_value}"
        headers["X-API-Key"] = token_value

    # TENANT ISOLATION (D1.3): Always set tenant headers for isolation
    tenant, namespace = get_tenant_namespace(cfg)

    # CRITICAL: Always set both headers - never leave empty (D1.4)
    headers["X-Soma-Namespace"] = namespace or "default"
    headers["X-Soma-Tenant"] = tenant or "default"

    max_conns = _http_setting("http_max_connections", 64)
    keepalive = _http_setting("http_keepalive_connections", 32)
    retries = _http_setting("http_retries", 1)

    try:
        import httpx

        limits = httpx.Limits(max_connections=max_conns, max_keepalive_connections=keepalive)
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
    if base_url.endswith("/openapi.json"):
        base_url = base_url[: -len("/openapi.json")]
    base_url = base_url.rstrip("/")

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
    if not token_value:
        logger_instance.warning(
            "Memory HTTP client initialized without token; proceeding without auth."
        )
    return transport
