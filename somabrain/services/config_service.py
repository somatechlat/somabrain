"""Dynamic configuration service for SomaBrain.

This module provides an in-memory configuration service that merges global,
tenant, and namespace layers, tracks an audit log, and exposes a lightweight
publish/subscribe stream for hot-reload consumers. It is intentionally
synchronous for ease of testing; the subscriber interface uses asyncio queues
so workers can await new configuration versions.
"""

from __future__ import annotations

import asyncio
import copy
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

# The original Config model was removed; use the unified Settings for type hints.
from django.conf import settings as Config


@dataclass(frozen=True)
class ConfigEvent:
    """Event emitted whenever the effective configuration changes."""

    version: int
    tenant: str
    namespace: str
    payload: Dict[str, Any]


@dataclass(frozen=True)
class AuditRecord:
    """Audit metadata for configuration mutations."""

    version: int
    scope: str
    tenant: str
    namespace: str
    actor: str
    timestamp: float
    patch: Dict[str, Any]
    before: Dict[str, Any]
    after: Dict[str, Any]


class ConfigMergeError(RuntimeError):
    """Raised when an invalid patch is supplied."""


class ConfigService:
    """Manage layered configuration with auditing and hot reload events."""

    def __init__(
        self,
        base_supplier: Callable[[], Config],
        *,
        clock: Callable[[], float] | None = None,
    ) -> None:
        """Initialize the instance."""

        self._base_supplier = base_supplier
        self._clock = clock or time.time
        self._global_layer: Dict[str, Any] = {}
        self._tenant_layer: Dict[str, Dict[str, Any]] = {}
        self._namespace_layer: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._version = 0
        self._audit_log: List[AuditRecord] = []
        self._subscribers: List[asyncio.Queue[ConfigEvent]] = []
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def patch_global(self, patch: Dict[str, Any], *, actor: str) -> ConfigEvent:
        """Execute patch global.

        Args:
            patch: The patch.
        """

        return await self._apply_patch("global", patch, actor, "", "")

    async def patch_tenant(
        self, tenant: str, patch: Dict[str, Any], *, actor: str
    ) -> ConfigEvent:
        """Execute patch tenant.

        Args:
            tenant: The tenant.
            patch: The patch.
        """

        if not tenant:
            raise ConfigMergeError("tenant must be provided")
        return await self._apply_patch("tenant", patch, actor, tenant, "")

    async def patch_namespace(
        self,
        tenant: str,
        namespace: str,
        patch: Dict[str, Any],
        *,
        actor: str,
    ) -> ConfigEvent:
        """Execute patch namespace.

        Args:
            tenant: The tenant.
            namespace: The namespace.
            patch: The patch.
        """

        if not tenant or not namespace:
            raise ConfigMergeError("tenant and namespace must be provided")
        return await self._apply_patch("namespace", patch, actor, tenant, namespace)

    def subscribe(self, *, max_queue: int = 128) -> asyncio.Queue[ConfigEvent]:
        """Execute subscribe."""

        queue: asyncio.Queue[ConfigEvent] = asyncio.Queue(max_queue)
        self._subscribers.append(queue)
        return queue

    def audit_log(self, limit: Optional[int] = None) -> List[AuditRecord]:
        """Execute audit log.

        Args:
            limit: The limit.
        """

        if limit is None or limit >= len(self._audit_log):
            return list(self._audit_log)
        return self._audit_log[-limit:]

    def effective_config(self, tenant: str, namespace: str) -> Dict[str, Any]:
        """Execute effective config.

        Args:
            tenant: The tenant.
            namespace: The namespace.
        """

        base_cfg = self._config_to_dict(self._base_supplier())
        merged = self._deep_merge(copy.deepcopy(base_cfg), self._global_layer)
        if tenant:
            merged = self._deep_merge(merged, self._tenant_layer.get(tenant, {}))
        if tenant and namespace:
            merged = self._deep_merge(
                merged, self._namespace_layer.get((tenant, namespace), {})
            )
        merged.setdefault("tenant", tenant)
        merged.setdefault("namespace", namespace)
        merged["version"] = self._version
        return merged

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _apply_patch(
        self,
        scope: str,
        patch: Dict[str, Any],
        actor: str,
        tenant: str,
        namespace: str,
    ) -> ConfigEvent:
        """Execute apply patch.

        Args:
            scope: The scope.
            patch: The patch.
            actor: The actor.
            tenant: The tenant.
            namespace: The namespace.
        """

        async with self._lock:
            target_dict, before = self._target_and_before(scope, tenant, namespace)
            after = self._deep_merge(copy.deepcopy(before), patch)
            self._validate(after)
            self._set_layer(scope, tenant, namespace, after)
            self._version += 1
            event = ConfigEvent(
                version=self._version,
                tenant=tenant,
                namespace=namespace,
                payload=self.effective_config(tenant, namespace),
            )
            record = AuditRecord(
                version=self._version,
                scope=scope,
                tenant=tenant,
                namespace=namespace,
                actor=actor,
                timestamp=self._clock(),
                patch=copy.deepcopy(patch),
                before=before,
                after=after,
            )
            self._audit_log.append(record)
            for queue in list(self._subscribers):
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    # drop oldest subscriber queue entry to avoid blocking
                    queue.get_nowait()
                    queue.put_nowait(event)
            return event

    def _target_and_before(
        self, scope: str, tenant: str, namespace: str
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Execute target and before.

        Args:
            scope: The scope.
            tenant: The tenant.
            namespace: The namespace.
        """

        if scope == "global":
            return self._global_layer, copy.deepcopy(self._global_layer)
        if scope == "tenant":
            layer = self._tenant_layer.setdefault(tenant, {})
            return layer, copy.deepcopy(layer)
        if scope == "namespace":
            key = (tenant, namespace)
            layer = self._namespace_layer.setdefault(key, {})
            return layer, copy.deepcopy(layer)
        raise ConfigMergeError(f"unknown scope: {scope}")

    def _set_layer(
        self, scope: str, tenant: str, namespace: str, data: Dict[str, Any]
    ) -> None:
        """Execute set layer.

        Args:
            scope: The scope.
            tenant: The tenant.
            namespace: The namespace.
            data: The data.
        """

        if scope == "global":
            self._global_layer = data
        elif scope == "tenant":
            self._tenant_layer[tenant] = data
        else:
            self._namespace_layer[(tenant, namespace)] = data

    @staticmethod
    def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
        """Execute deep merge.

        Args:
            base: The base.
            patch: The patch.
        """

        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = ConfigService._deep_merge(
                    copy.deepcopy(base.get(key, {})), value
                )
            else:
                base[key] = copy.deepcopy(value)
        return base

    @staticmethod
    def _config_to_dict(cfg: Config) -> Dict[str, Any]:
        """Execute config to dict.

        Args:
            cfg: The cfg.
        """

        try:
            return asdict(cfg)
        except Exception:
            return copy.deepcopy(cfg.__dict__)

    @staticmethod
    def _validate(data: Dict[str, Any]) -> None:
        # Minimal validation: ensure numeric values are finite when present.
        """Execute validate.

        Args:
            data: The data.
        """

        def _walk(obj: Any, path: str = "") -> None:
            """Execute walk.

            Args:
                obj: The obj.
                path: The path.
            """

            if isinstance(obj, dict):
                for k, v in obj.items():
                    _walk(v, f"{path}.{k}" if path else str(k))
            elif isinstance(obj, (int, float)):
                if isinstance(obj, float) and (obj != obj):  # NaN check
                    raise ConfigMergeError(f"non-finite value at {path}")

        _walk(data)


__all__ = [
    "ConfigEvent",
    "AuditRecord",
    "ConfigMergeError",
    "ConfigService",
]
