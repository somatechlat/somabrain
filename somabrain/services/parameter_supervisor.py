"""Metrics-driven parameter supervisor for SomaBrain."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional, Tuple

from somabrain.metrics import mark_controller_change

from .config_service import ConfigService


@dataclass
class MetricsSnapshot:
    """Observability data consumed by the parameter supervisor."""

    tenant: str
    namespace: str
    top1_accuracy: float
    margin: float
    latency_p95_ms: float


@dataclass
class SupervisorPolicy:
    """Simple policy knobs for config adjustments."""

    eta_step: float = 0.01
    eta_bounds: Tuple[float, float] = (0.01, 0.3)
    tau_step: float = -0.02
    tau_bounds: Tuple[float, float] = (0.4, 0.8)
    ef_step: int = 16
    ef_bounds: Tuple[int, int] = (64, 512)
    min_interval_seconds: float = 60.0


class ParameterSupervisor:
    """Adjusts configuration parameters based on observed metrics."""

    def __init__(
        self,
        config_service: ConfigService,
        policy: SupervisorPolicy | None = None,
        *,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._config = config_service
        self._policy = policy or SupervisorPolicy()
        self._clock = clock or time.monotonic
        self._last_adjustment: Dict[Tuple[str, str], float] = {}

    async def evaluate(self, snapshot: MetricsSnapshot) -> Optional[Dict[str, object]]:
        tenant = snapshot.tenant
        namespace = snapshot.namespace
        key = (tenant, namespace)
        now = self._clock()
        last = self._last_adjustment.get(key, float("-inf"))
        if now - last < self._policy.min_interval_seconds:
            return None

        effective = self._config.effective_config(tenant, namespace)
        targets = effective.get("targets", {})
        target_top1 = float(targets.get("top1", 0.9))
        target_margin = float(targets.get("margin", 0.12))

        patch: Dict[str, object] = {}

        if snapshot.top1_accuracy < target_top1:
            eta = float(
                effective.get("eta", effective.get("trace", {}).get("eta", 0.05))
            )
            new_eta = self._clamp(eta + self._policy.eta_step, *self._policy.eta_bounds)
            if not math.isclose(new_eta, eta):
                patch["eta"] = new_eta

        if snapshot.margin < target_margin:
            gate = effective.get("gate", {})
            tau = float(gate.get("tau", 0.65))
            new_tau = self._clamp(tau + self._policy.tau_step, *self._policy.tau_bounds)
            if not math.isclose(new_tau, tau):
                patch.setdefault("gate", {})
                patch["gate"]["tau"] = new_tau
            cleanup = effective.get("cleanup", {})
            hnsw = cleanup.get("hnsw", {})
            ef = int(hnsw.get("efSearch", 128))
            new_ef = int(
                self._clamp(ef + self._policy.ef_step, *self._policy.ef_bounds)
            )
            if new_ef != ef:
                patch.setdefault("cleanup", {}).setdefault("hnsw", {})
                patch["cleanup"]["hnsw"]["efSearch"] = new_ef

        if not patch:
            return None

        await self._config.patch_namespace(tenant, namespace, patch, actor="supervisor")
        for param in self._flatten_patch_keys(patch):
            mark_controller_change(param)
        self._last_adjustment[key] = now
        return patch

    @staticmethod
    def _clamp(value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, value))

    @staticmethod
    def _flatten_patch_keys(data: Dict[str, object], prefix: str = "") -> Iterable[str]:
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, dict):
                yield from ParameterSupervisor._flatten_patch_keys(value, path)
            else:
                yield path


__all__ = ["MetricsSnapshot", "SupervisorPolicy", "ParameterSupervisor"]
