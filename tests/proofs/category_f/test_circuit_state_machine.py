"""Circuit Breaker State Machine Tests.

**Feature: full-capacity-testing, Property 35-39**
**Validates: Requirements F1.1, F1.2, F1.3, F1.4, F1.5**

Tests that PROVE circuit breaker state machine correctness using the real
``somabrain.infrastructure.circuit_breaker.CircuitBreaker`` implementation.
"""

from __future__ import annotations

import time

import pytest

from somabrain.infrastructure.circuit_breaker import CircuitBreaker


@pytest.mark.circuit_breaker
class TestCircuitBreakerStateMachine:
    """Prove circuit breaker state machine correctness."""

    def test_closed_to_open_on_threshold(self) -> None:
        """F1.1: Circuit opens after 5 consecutive failures."""
        cb = CircuitBreaker(
            global_failure_threshold=5,
            global_reset_interval=60.0,
            global_cooldown_interval=0.0,
        )
        tenant = "test_tenant_f1_1"

        assert not cb.is_open(tenant), "Circuit should start CLOSED"

        for i in range(4):
            cb.record_failure(tenant)
            assert not cb.is_open(tenant), f"Circuit opened after only {i + 1} failures"

        cb.record_failure(tenant)
        assert cb.is_open(tenant), "Circuit should be OPEN after 5 failures"

    def test_open_fails_fast(self) -> None:
        """F1.2: Open circuit fails fast without backend call."""
        cb = CircuitBreaker(
            global_failure_threshold=5,
            global_reset_interval=60.0,
            global_cooldown_interval=0.0,
        )
        tenant = "test_tenant_f1_2"

        for _ in range(5):
            cb.record_failure(tenant)

        assert cb.is_open(tenant), "Circuit should be OPEN"
        assert not cb.allow_request(tenant), "allow_request should be False when OPEN"

    def test_open_to_half_open_on_timeout(self) -> None:
        """F1.3: Circuit transitions to HALF_OPEN after reset timeout."""
        cb = CircuitBreaker(
            global_failure_threshold=5,
            global_reset_interval=1.0,
            global_cooldown_interval=0.0,
        )
        tenant = "test_tenant_f1_3"

        for _ in range(5):
            cb.record_failure(tenant)

        assert cb.is_open(tenant), "Circuit should be OPEN"
        assert not cb.allow_request(tenant), "Should not allow request immediately"

        time.sleep(1.5)

        assert cb.allow_request(tenant), "Should allow request in HALF_OPEN"
        assert cb.get_stats(tenant)["state"] == "HALF-OPEN", "State should be HALF-OPEN"

    def test_half_open_to_closed_on_success(self) -> None:
        """F1.4: HALF_OPEN transitions to CLOSED on success."""
        cb = CircuitBreaker(
            global_failure_threshold=5,
            global_reset_interval=1.0,
            global_cooldown_interval=0.0,
        )
        tenant = "test_tenant_f1_4"

        for _ in range(5):
            cb.record_failure(tenant)

        assert cb.is_open(tenant), "Circuit should be OPEN"
        time.sleep(1.5)

        assert cb.allow_request(tenant), "Should be in HALF_OPEN state"
        cb.record_success(tenant)

        assert not cb.is_open(tenant), "Circuit should be CLOSED after success"
        stats = cb.get_stats(tenant)
        assert stats["failure_count"] == 0, "Failure count should be reset"
        assert stats["state"] == "CLOSED", "State should be CLOSED"

    def test_half_open_to_open_on_failure(self) -> None:
        """F1.5: HALF_OPEN returns to OPEN on failure."""
        cb = CircuitBreaker(
            global_failure_threshold=5,
            global_reset_interval=1.0,
            global_cooldown_interval=0.0,
        )
        tenant = "test_tenant_f1_5"

        for _ in range(5):
            cb.record_failure(tenant)

        assert cb.is_open(tenant), "Circuit should be OPEN"
        time.sleep(1.5)

        assert cb.allow_request(tenant), "Should be in HALF_OPEN state"
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

        cb.record_failure(tenant)
        cb.record_failure(tenant)
        assert not cb.is_open(tenant)

        cb.record_failure(tenant)
        assert cb.is_open(tenant)

    def test_per_tenant_isolation(self) -> None:
        """Each tenant has an independent circuit state."""
        cb = CircuitBreaker(
            global_failure_threshold=5,
            global_reset_interval=60.0,
            global_cooldown_interval=0.0,
        )
        tenant_a = "tenant_a"
        tenant_b = "tenant_b"

        for _ in range(5):
            cb.record_failure(tenant_a)

        assert cb.is_open(tenant_a), "Tenant A circuit should be OPEN"
        assert not cb.is_open(tenant_b), "Tenant B circuit should remain CLOSED"

    def test_get_stats_returns_snapshot(self) -> None:
        """get_stats returns an accurate snapshot."""
        cb = CircuitBreaker(
            global_failure_threshold=5,
            global_reset_interval=60.0,
            global_cooldown_interval=0.0,
        )
        tenant = "test_state_snapshot"

        cb.record_failure(tenant)
        cb.record_failure(tenant)

        stats = cb.get_stats(tenant)

        assert stats["tenant"] == tenant
        assert stats["failure_count"] == 2
        assert stats["state"] == "CLOSED"
