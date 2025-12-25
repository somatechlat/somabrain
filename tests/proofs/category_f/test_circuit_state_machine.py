"""Circuit Breaker State Machine Tests.

**Feature: full-capacity-testing, Property 35-39**
**Validates: Requirements F1.1, F1.2, F1.3, F1.4, F1.5**

Tests that PROVE circuit breaker state machine correctness:
- CLOSED -> OPEN after 5 consecutive failures
- OPEN fails fast without backend call
- OPEN -> HALF_OPEN after reset timeout
- HALF_OPEN -> CLOSED on success
- HALF_OPEN -> OPEN on failure

Uses the real CircuitBreaker implementation from somabrain.infrastructure.
"""

from __future__ import annotations

import time

import pytest

from somabrain.infrastructure.circuit_breaker import CircuitBreaker


@pytest.mark.circuit_breaker
class TestCircuitBreakerStateMachine:
    """Prove circuit breaker state machine correctness."""

    def test_closed_to_open_on_threshold(self) -> None:
        """F1.1: Circuit opens after 5 consecutive failures.

        **Feature: full-capacity-testing, Property 35: Circuit Opens on Threshold**
        **Validates: Requirements F1.1**

        For any backend failing 5 consecutive times, circuit breaker SHALL
        transition to OPEN state.
        """
        cb = CircuitBreaker(
            global_failure_threshold=5,
            global_reset_interval=60.0,
            global_cooldown_interval=0.0,
        )
        tenant = "test_tenant_f1_1"

        # Initially closed
        assert not cb.is_open(tenant), "Circuit should start CLOSED"

        # Record 4 failures - should still be closed
        for i in range(4):
            cb.record_failure(tenant)
            assert not cb.is_open(tenant), f"Circuit opened after only {i + 1} failures"

        # 5th failure should open the circuit
        cb.record_failure(tenant)
        assert cb.is_open(tenant), "Circuit should be OPEN after 5 failures"

    def test_open_fails_fast(self) -> None:
        """F1.2: Open circuit fails fast without backend call.

        **Feature: full-capacity-testing, Property 36: Open Circuit Fails Fast**
        **Validates: Requirements F1.2**

        For any request when circuit is OPEN, the system SHALL fail-fast
        without attempting backend call.
        """
        cb = CircuitBreaker(
            global_failure_threshold=5,
            global_reset_interval=60.0,
            global_cooldown_interval=0.0,
        )
        tenant = "test_tenant_f1_2"

        # Open the circuit
        for _ in range(5):
            cb.record_failure(tenant)

        assert cb.is_open(tenant), "Circuit should be OPEN"

        # Verify is_open returns True (fail-fast check)
        # In real usage, caller checks is_open before making backend call
        assert cb.is_open(tenant), "is_open should return True for fail-fast"

        # should_attempt_reset should be False immediately after opening
        # (reset interval not elapsed)
        assert not cb.should_attempt_reset(
            tenant
        ), "should_attempt_reset should be False immediately after opening"

    def test_open_to_half_open_on_timeout(self) -> None:
        """F1.3: Circuit transitions to HALF_OPEN after reset timeout.

        **Feature: full-capacity-testing, Property 37: Reset Timeout Transitions to Half-Open**
        **Validates: Requirements F1.3**

        For any OPEN circuit after reset timeout expires, circuit SHALL
        transition to HALF_OPEN state (allowing a test request).
        """
        # Use very short reset interval for testing
        cb = CircuitBreaker(
            global_failure_threshold=5,
            global_reset_interval=1.0,  # 1 second
            global_cooldown_interval=0.0,
        )
        tenant = "test_tenant_f1_3"

        # Open the circuit
        for _ in range(5):
            cb.record_failure(tenant)

        assert cb.is_open(tenant), "Circuit should be OPEN"

        # Immediately after opening, should not attempt reset
        assert not cb.should_attempt_reset(
            tenant
        ), "should_attempt_reset should be False before timeout"

        # Wait for reset interval
        time.sleep(1.5)

        # Now should_attempt_reset should return True (HALF_OPEN state)
        assert cb.should_attempt_reset(
            tenant
        ), "should_attempt_reset should be True after reset timeout (HALF_OPEN)"

    def test_half_open_to_closed_on_success(self) -> None:
        """F1.4: HALF_OPEN transitions to CLOSED on success.

        **Feature: full-capacity-testing, Property 38: Half-Open Success Closes Circuit**
        **Validates: Requirements F1.4**

        For any HALF_OPEN circuit with successful request, circuit SHALL
        transition to CLOSED state.
        """
        cb = CircuitBreaker(
            global_failure_threshold=5,
            global_reset_interval=1.0,
            global_cooldown_interval=0.0,
        )
        tenant = "test_tenant_f1_4"

        # Open the circuit
        for _ in range(5):
            cb.record_failure(tenant)

        assert cb.is_open(tenant), "Circuit should be OPEN"

        # Wait for reset interval to enter HALF_OPEN
        time.sleep(1.5)

        # Verify we can attempt reset (HALF_OPEN)
        assert cb.should_attempt_reset(tenant), "Should be in HALF_OPEN state"

        # Record success - should close the circuit
        cb.record_success(tenant)

        assert not cb.is_open(tenant), "Circuit should be CLOSED after success"

        # Verify state is fully reset
        state = cb.get_state(tenant)
        assert state["failure_count"] == 0, "Failure count should be reset"
        assert not state["circuit_open"], "Circuit should be closed"

    def test_half_open_to_open_on_failure(self) -> None:
        """F1.5: HALF_OPEN returns to OPEN on failure.

        **Feature: full-capacity-testing, Property 39: Half-Open Failure Reopens Circuit**
        **Validates: Requirements F1.5**

        For any HALF_OPEN circuit with failed request, circuit SHALL
        return to OPEN state.
        """
        cb = CircuitBreaker(
            global_failure_threshold=5,
            global_reset_interval=1.0,
            global_cooldown_interval=0.0,
        )
        tenant = "test_tenant_f1_5"

        # Open the circuit
        for _ in range(5):
            cb.record_failure(tenant)

        assert cb.is_open(tenant), "Circuit should be OPEN"

        # Wait for reset interval to enter HALF_OPEN
        time.sleep(1.5)

        # Verify we can attempt reset (HALF_OPEN)
        assert cb.should_attempt_reset(tenant), "Should be in HALF_OPEN state"

        # Record failure - should reopen the circuit
        cb.record_failure(tenant)

        assert cb.is_open(tenant), "Circuit should be OPEN after failure in HALF_OPEN"


@pytest.mark.circuit_breaker
class TestCircuitBreakerConfiguration:
    """Tests for circuit breaker configuration."""

    def test_custom_threshold(self) -> None:
        """Custom failure threshold is respected."""
        cb = CircuitBreaker(
            global_failure_threshold=3,
            global_reset_interval=60.0,
            global_cooldown_interval=0.0,
        )
        tenant = "test_custom_threshold"

        # 2 failures - still closed
        cb.record_failure(tenant)
        cb.record_failure(tenant)
        assert not cb.is_open(tenant)

        # 3rd failure - opens
        cb.record_failure(tenant)
        assert cb.is_open(tenant)

    def test_per_tenant_configuration(self) -> None:
        """Per-tenant configuration overrides global."""
        cb = CircuitBreaker(
            global_failure_threshold=5,
            global_reset_interval=60.0,
            global_cooldown_interval=0.0,
        )
        tenant = "test_per_tenant"

        # Configure tenant with lower threshold
        cb.configure_tenant(tenant, failure_threshold=2)

        # 2 failures should open (not 5)
        cb.record_failure(tenant)
        cb.record_failure(tenant)
        assert cb.is_open(tenant), "Per-tenant threshold should be 2"

    def test_get_state_returns_snapshot(self) -> None:
        """get_state returns accurate snapshot."""
        cb = CircuitBreaker(
            global_failure_threshold=5,
            global_reset_interval=60.0,
            global_cooldown_interval=0.0,
        )
        tenant = "test_state_snapshot"

        # Record some failures
        cb.record_failure(tenant)
        cb.record_failure(tenant)

        state = cb.get_state(tenant)

        assert state["tenant"] == tenant
        assert state["failure_count"] == 2
        assert not state["circuit_open"]
        assert state["failure_threshold"] == 5
        assert state["reset_interval"] == 60.0
