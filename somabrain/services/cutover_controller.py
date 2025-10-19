"""Blue/green cutover controller for SomaBrain namespaces."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from somabrain.services.config_service import ConfigService


@dataclass
class ShadowMetrics:
    """Shadow-read telemetry captured against the candidate namespace."""

    top1_accuracy: float
    margin: float
    latency_p95_ms: float
    collected_at: float


@dataclass
class CutoverPlan:
    """Represents a pending blue/green cutover."""

    tenant: str
    from_namespace: str
    to_namespace: str
    created_at: float
    status: str = "draft"
    approved_at: Optional[float] = None
    ready: bool = False
    last_shadow_metrics: Optional[ShadowMetrics] = None
    notes: list[str] = field(default_factory=list)


class CutoverError(RuntimeError):
    """Raised when a cutover operation is invalid."""


class CutoverController:
    """Manage blue/green namespace cutovers with readiness checks."""

    def __init__(
        self,
        config_service: ConfigService,
        *,
        clock: Optional[Callable[[], float]] = None,
        readiness_margin: float = 0.0,
        latency_budget_factor: float = 1.05,
    ) -> None:
        self._config = config_service
        self._clock = clock or time.time
        self._plans: Dict[str, CutoverPlan] = {}
        self._readiness_margin = readiness_margin
        self._latency_budget_factor = latency_budget_factor
        self._lock = asyncio.Lock()

    async def open_plan(
        self, tenant: str, from_namespace: str, to_namespace: str
    ) -> CutoverPlan:
        if from_namespace == to_namespace:
            raise CutoverError("from and to namespaces must differ")
        async with self._lock:
            if tenant in self._plans and self._plans[tenant].status in {
                "draft",
                "approved",
            }:
                raise CutoverError(f"cutover already open for tenant {tenant}")
            plan = CutoverPlan(
                tenant=tenant,
                from_namespace=from_namespace,
                to_namespace=to_namespace,
                created_at=self._clock(),
            )
            self._plans[tenant] = plan
            return plan

    async def record_shadow_metrics(
        self,
        tenant: str,
        to_namespace: str,
        *,
        top1_accuracy: float,
        margin: float,
        latency_p95_ms: float,
    ) -> CutoverPlan:
        async with self._lock:
            plan = self._require_plan(tenant)
            if plan.to_namespace != to_namespace:
                raise CutoverError("metrics do not match active plan namespace")
            metrics = ShadowMetrics(
                top1_accuracy=top1_accuracy,
                margin=margin,
                latency_p95_ms=latency_p95_ms,
                collected_at=self._clock(),
            )
            plan.last_shadow_metrics = metrics
            plan.ready = self._evaluate_readiness(plan, metrics)
            if plan.ready:
                plan.notes.append("shadow metrics meet readiness criteria")
            return plan

    async def approve(self, tenant: str) -> CutoverPlan:
        async with self._lock:
            plan = self._require_plan(tenant)
            if not plan.ready:
                raise CutoverError("plan not ready for approval")
            plan.status = "approved"
            plan.approved_at = self._clock()
            plan.notes.append("plan approved")
            return plan

    async def execute(self, tenant: str) -> CutoverPlan:
        async with self._lock:
            plan = self._require_plan(tenant)
            if plan.status != "approved":
                raise CutoverError("plan must be approved before execution")
            plan.status = "executed"
            plan.notes.append("cutover executed")
            self._plans[tenant] = plan
            return plan

    async def cancel(self, tenant: str, reason: str = "") -> None:
        async with self._lock:
            plan = self._require_plan(tenant)
            plan.status = "cancelled"
            if reason:
                plan.notes.append(f"cancelled: {reason}")
            self._plans.pop(tenant, None)

    def _require_plan(self, tenant: str) -> CutoverPlan:
        try:
            return self._plans[tenant]
        except KeyError as exc:
            raise CutoverError(f"no plan for tenant {tenant}") from exc

    def _evaluate_readiness(self, plan: CutoverPlan, metrics: ShadowMetrics) -> bool:
        effective = self._config.effective_config(plan.tenant, plan.to_namespace)
        targets = effective.get("targets", {})
        target_top1 = float(targets.get("top1", 0.9)) - self._readiness_margin
        target_margin = float(targets.get("margin", 0.12)) - self._readiness_margin

        baseline = self._config.effective_config(plan.tenant, plan.from_namespace)
        latency_budget = (
            float(baseline.get("latency_p95_ms", 100.0)) * self._latency_budget_factor
        )

        return (
            metrics.top1_accuracy >= target_top1
            and metrics.margin >= target_margin
            and metrics.latency_p95_ms <= latency_budget
        )


__all__ = [
    "CutoverController",
    "CutoverError",
    "CutoverPlan",
    "ShadowMetrics",
]
