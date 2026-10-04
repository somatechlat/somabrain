"""Sleep system for SomaBrain.

This module provides sleep state management and consolidation cycles.
"""

import dataclasses
from enum import Enum
from typing import Any, Dict  # noqa: F401

from django.conf import settings as settings


class SleepState(Enum):
    """Sleep state enumeration."""

    ACTIVE = "active"
    LIGHT = "light"
    DEEP = "deep"
    FREEZE = "freeze"


@dataclasses.dataclass
class SleepParameters:
    """Sleep parameters configuration."""

    K: int = settings.SLEEP_K0
    t: float = settings.SLEEP_T0
    tau: float = settings.SLEEP_TAU0
    eta: float = settings.SLEEP_ETA0
    lambda_: float = settings.SLEEP_LAMBDA0
    B: float = settings.SLEEP_B0
    # Bounds for validation
    K_min: int = settings.SLEEP_K_MIN
    t_min: float = settings.SLEEP_T_MIN
    alpha_K: float = settings.SLEEP_ALPHA_K
    alpha_t: float = settings.SLEEP_ALPHA_T
    alpha_tau: float = settings.SLEEP_ALPHA_TAU
    alpha_eta: float = settings.SLEEP_ALPHA_ETA
    beta_B: float = settings.SLEEP_BETA_B


class SleepStateManager:
    """Manages sleep state transitions and parameters."""

    def __init__(self):
        """Initialize the instance."""

        self.parameters = SleepParameters()

    def compute_parameters(
        self, state: SleepState, tenant_id: str = "default"
    ) -> dict[str, float]:
        """Compute parameters for a given sleep state (hot-configurable via brain_settings)."""
        from somabrain import brain_settings

        # Load dynamic knobs from DB
        k0 = brain_settings.get("sleep_k0", tenant_id)
        t0 = brain_settings.get("sleep_t0", tenant_id)
        tau0 = brain_settings.get("sleep_tau0", tenant_id)
        eta0 = brain_settings.get("sleep_eta0", tenant_id)
        lambda_0 = brain_settings.get("sleep_lambda0", tenant_id)
        b0 = brain_settings.get("sleep_b0", tenant_id)

        # Bounds and scalars
        k_min = brain_settings.get("sleep_k_min", tenant_id)
        t_min = brain_settings.get("sleep_t_min", tenant_id)
        alpha_k = brain_settings.get("sleep_alpha_k", tenant_id)
        alpha_t = brain_settings.get("sleep_alpha_t", tenant_id)
        alpha_tau = brain_settings.get("sleep_alpha_tau", tenant_id)
        alpha_eta = brain_settings.get("sleep_alpha_eta", tenant_id)
        beta_b = brain_settings.get("sleep_beta_b", tenant_id)

        state_scalar = {
            SleepState.ACTIVE: 0.0,
            SleepState.LIGHT: 0.5,
            SleepState.DEEP: 1.0,
            SleepState.FREEZE: 10.0,
        }[state]

        s = state_scalar
        K = max(k_min, int((1 - alpha_k * s) * k0))
        t = max(t_min, (1 - alpha_t * s) * t0)
        tau = max(1e-6, (1 - alpha_tau * s) * tau0)

        if s >= 1:
            eta = 0.0
        else:
            eta = max(0.0, (1 - alpha_eta * s) * eta0)

        B = b0 + beta_b * s

        if state == SleepState.FREEZE:
            curr_lambda = 0.0
        elif state == SleepState.DEEP:
            curr_lambda = max(0.0, lambda_0 * 0.5)
        elif state == SleepState.LIGHT:
            curr_lambda = max(0.0, lambda_0 * 0.8)
        else:
            curr_lambda = lambda_0

        return {
            "K": K,
            "t": t,
            "tau": tau,
            "eta": eta,
            "lambda": curr_lambda,
            "B": B,
        }

    def can_transition(self, from_state: SleepState, to_state: SleepState) -> bool:
        """Check if state transition is valid."""
        # The allowed state transition graph is:
        #   ACTIVE → LIGHT → DEEP → FREEZE → LIGHT → ACTIVE
        # The wake edge (LIGHT → ACTIVE) is required: a tenant that leaves
        # ACTIVE must be able to return, otherwise a sleep cycle is permanent.
        valid_transitions = {
            SleepState.ACTIVE: [SleepState.LIGHT],
            SleepState.LIGHT: [SleepState.DEEP, SleepState.ACTIVE],
            SleepState.DEEP: [SleepState.FREEZE],
            SleepState.FREEZE: [SleepState.LIGHT],
        }

        return to_state in valid_transitions.get(from_state, [])

    def transition(
        self, tenant_id: str, trigger: str = "manual"
    ) -> SleepState:
        """Apply a trigger and return the resulting sleep state.

        The state itself lives in ``TenantSleepState``; this method computes
        the target from the trigger and the current state, validates the edge,
        and returns the new ``SleepState``. Persistence is the caller's job
        (the HTTP layer owns the DB transaction).

        Args:
            tenant_id: Tenant whose state is being transitioned.
            trigger: Named trigger (``manual``, ``idle``, ``scheduled``,
                ``wake``, ``freeze``).

        Returns:
            The target ``SleepState``.

        Raises:
            ValueError: On an unknown trigger or an illegal edge.
        """
        from somabrain.sleep.models import TenantSleepState

        trigger_map = {
            "manual": SleepState.LIGHT,
            "idle": SleepState.LIGHT,
            "scheduled": SleepState.DEEP,
            "deep": SleepState.DEEP,
            "freeze": SleepState.FREEZE,
            "wake": SleepState.ACTIVE,
            "active": SleepState.ACTIVE,
        }
        if trigger not in trigger_map:
            raise ValueError(f"Unknown sleep trigger: {trigger}")
        target = trigger_map[trigger]

        try:
            row = TenantSleepState.objects.get(tenant_id=tenant_id)
            current = SleepState(row.current_state.lower())
        except TenantSleepState.DoesNotExist:
            current = SleepState.ACTIVE
        except (ValueError, KeyError):
            current = SleepState.ACTIVE

        if not self.can_transition(current, target):
            raise ValueError(
                f"Invalid transition from {current.value} to {target.value}"
            )
        return target
