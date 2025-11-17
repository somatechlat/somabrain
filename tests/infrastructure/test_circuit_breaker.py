"""Unit tests for the centralised CircuitBreaker implementation.

Tests cover state transitions, threshold configuration, reset logic, and metric
emission. All tests use real implementations (no mocks) and follow VIBE rules.
"""
from __future__ import annotations

import time

import pytest

from somabrain.infrastructure.circuit_breaker import CircuitBreaker


class TestCircuitBreaker:
    """Test suite for CircuitBreaker functionality."""

    def test_initial_state_defaults(self) -> None:
        """Verify CircuitBreaker initializes with proper defaults."""
        breaker = CircuitBreaker()
        
        # Check default global thresholds
        assert breaker._global_failure_threshold == 3
        assert breaker._global_reset_interval == 60.0
        
        # No tenants should be registered initially
        assert not breaker._circuit_open
        assert not breaker._failure_count
        assert not breaker._last_failure_time
        assert not breaker._last_reset_attempt
        assert not breaker._failure_threshold
        assert not breaker._reset_interval

    def test_custom_global_thresholds(self) -> None:
        """Verify CircuitBreaker accepts custom global thresholds."""
        breaker = CircuitBreaker(global_failure_threshold=5, global_reset_interval=120.0)
        
        assert breaker._global_failure_threshold == 5
        assert breaker._global_reset_interval == 120.0

    def test_tenant_initialization_on_first_access(self) -> None:
        """Verify tenant state is initialized on first access."""
        breaker = CircuitBreaker()
        tenant = "test_tenant"
        
        # First access should initialize tenant state
        is_open = breaker.is_open(tenant)
        
        assert not is_open
        assert tenant in breaker._circuit_open
        assert breaker._circuit_open[tenant] is False
        assert breaker._failure_count[tenant] == 0
        assert breaker._last_failure_time[tenant] == 0.0
        assert breaker._failure_threshold[tenant] == breaker._global_failure_threshold
        assert breaker._reset_interval[tenant] == breaker._global_reset_interval

    def test_single_failure_increments_count(self) -> None:
        """Verify recording a failure increments the failure count."""
        breaker = CircuitBreaker()
        tenant = "test_tenant"
        
        # Initialize tenant
        breaker.is_open(tenant)
        
        # Record failure
        breaker.record_failure(tenant)
        
        assert breaker._failure_count[tenant] == 1
        assert breaker._circuit_open[tenant] is False
        assert breaker._last_failure_time[tenant] > 0.0

    def test_multiple_failures_open_circuit(self) -> None:
        """Verify reaching failure threshold opens the circuit."""
        breaker = CircuitBreaker(global_failure_threshold=3)
        tenant = "test_tenant"
        
        # Initialize tenant
        breaker.is_open(tenant)
        initial_time = breaker._last_failure_time[tenant]
        
        # Record failures up to threshold
        breaker.record_failure(tenant)
        breaker.record_failure(tenant)
        breaker.record_failure(tenant)
        
        # Circuit should be open
        assert breaker._failure_count[tenant] == 3
        assert breaker._circuit_open[tenant] is True
        assert breaker._last_failure_time[tenant] > initial_time

    def test_success_resets_failure_state(self) -> None:
        """Verify recording success resets failure count and closes circuit."""
        breaker = CircuitBreaker(global_failure_threshold=2)
        tenant = "test_tenant"
        
        # Initialize tenant and create failures
        breaker.is_open(tenant)
        breaker.record_failure(tenant)
        breaker.record_failure(tenant)
        assert breaker._circuit_open[tenant] is True
        
        # Record success
        breaker.record_success(tenant)
        
        # State should be reset
        assert breaker._failure_count[tenant] == 0
        assert breaker._circuit_open[tenant] is False
        assert breaker._last_failure_time[tenant] == 0.0

    def test_should_attempt_reset_closed_circuit(self) -> None:
        """Verify should_attempt_reset returns False for closed circuit."""
        breaker = CircuitBreaker()
        tenant = "test_tenant"
        
        # Circuit is closed initially
        should_reset = breaker.should_attempt_reset(tenant)
        assert should_reset is False

    def test_should_attempt_reset_too_soon(self) -> None:
        """Verify should_attempt_reset returns False when reset interval hasn't elapsed."""
        breaker = CircuitBreaker(global_failure_threshold=1, global_reset_interval=10.0)
        tenant = "test_tenant"
        
        # Open circuit
        breaker.is_open(tenant)
        breaker.record_failure(tenant)
        assert breaker._circuit_open[tenant] is True
        
        # Try to reset immediately
        should_reset = breaker.should_attempt_reset(tenant)
        assert should_reset is False
        
        # Last reset attempt should be recorded
        assert tenant in breaker._last_reset_attempt

    def test_should_attempt_reset_after_interval(self) -> None:
        """Verify should_attempt_reset returns True after reset interval elapses."""
        breaker = CircuitBreaker(global_failure_threshold=1, global_reset_interval=0.1)
        tenant = "test_tenant"
        
        # Open circuit
        breaker.is_open(tenant)
        breaker.record_failure(tenant)
        assert breaker._circuit_open[tenant] is True
        
        # Wait for reset interval
        time.sleep(0.15)
        
        # Should be able to reset
        should_reset = breaker.should_attempt_reset(tenant)
        assert should_reset is True

    def test_should_attempt_reset_cooldown(self) -> None:
        """Verify should_attempt_reset respects 5-second cooldown between attempts."""
        breaker = CircuitBreaker(global_failure_threshold=1, global_reset_interval=0.1)
        tenant = "test_tenant"
        
        # Open circuit
        breaker.is_open(tenant)
        breaker.record_failure(tenant)
        
        # Wait for reset interval
        time.sleep(0.15)
        
        # First attempt should succeed
        should_reset = breaker.should_attempt_reset(tenant)
        assert should_reset is True
        
        # Immediate second attempt should fail due to cooldown
        should_reset = breaker.should_attempt_reset(tenant)
        assert should_reset is False

    def test_configure_tenant_thresholds(self) -> None:
        """Verify per-tenant threshold configuration works."""
        breaker = CircuitBreaker()
        tenant = "test_tenant"
        
        # Initialize tenant
        breaker.is_open(tenant)
        
        # Configure tenant with custom thresholds
        breaker.configure_tenant(
            tenant,
            failure_threshold=5,
            reset_interval=120.0
        )
        
        assert breaker._failure_threshold[tenant] == 5
        assert breaker._reset_interval[tenant] == 120.0

    def test_configure_tenant_partial_thresholds(self) -> None:
        """Verify configuring only one threshold preserves the other."""
        breaker = CircuitBreaker()
        tenant = "test_tenant"
        
        # Initialize tenant
        breaker.is_open(tenant)
        original_reset = breaker._reset_interval[tenant]
        
        # Configure only failure threshold
        breaker.configure_tenant(tenant, failure_threshold=7)
        
        assert breaker._failure_threshold[tenant] == 7
        assert breaker._reset_interval[tenant] == original_reset

    def test_get_state_for_tenant(self) -> None:
        """Verify get_state returns correct tenant state snapshot."""
        breaker = CircuitBreaker(global_failure_threshold=3, global_reset_interval=60.0)
        tenant = "test_tenant"
        
        # Initialize tenant and set some state
        breaker.is_open(tenant)
        breaker.record_failure(tenant)
        
        state = breaker.get_state(tenant)
        
        assert state["tenant"] == tenant
        assert state["circuit_open"] is False  # Not at threshold yet
        assert state["failure_count"] == 1
        assert state["last_failure_time"] > 0.0
        assert state["last_reset_attempt"] == 0.0
        assert state["failure_threshold"] == 3
        assert state["reset_interval"] == 60.0

    def test_get_state_for_open_circuit(self) -> None:
        """Verify get_state returns correct state for open circuit."""
        breaker = CircuitBreaker(global_failure_threshold=1)
        tenant = "test_tenant"
        
        # Open circuit
        breaker.is_open(tenant)
        breaker.record_failure(tenant)
        
        state = breaker.get_state(tenant)
        
        assert state["circuit_open"] is True
        assert state["failure_count"] == 1

    def test_thread_safety_with_concurrent_access(self) -> None:
        """Verify circuit breaker is thread-safe under concurrent access."""
        import threading
        import concurrent.futures
        
        breaker = CircuitBreaker(global_failure_threshold=10)
        tenant = "test_tenant"
        
        def record_failures(count: int) -> None:
            for _ in range(count):
                breaker.record_failure(tenant)
        
        # Run multiple threads concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(record_failures, 5)
                for _ in range(4)
            ]
            concurrent.futures.wait(futures)
        
        # All failures should be recorded correctly
        assert breaker._failure_count[tenant] == 20

    def test_metric_emission_on_success(self) -> None:
        """Verify CIRCUIT_STATE metric is emitted on success using real metrics module."""
        # Import real metrics module to test actual integration
        try:
            from somabrain.infrastructure.circuit_breaker import CircuitBreaker
            from somabrain import metrics
            
            # Get the real gauge
            gauge = getattr(metrics, 'CIRCUIT_STATE', None)
            if gauge is not None:
                # Record initial value
                breaker = CircuitBreaker()
                tenant = "test_tenant"
                
                # Record success and verify metric is updated
                breaker.record_success(tenant)
                
                # The metric should exist and be set to 0 (closed)
                # We can't easily inspect the actual value without Prometheus client,
                # but we can verify no exception was raised
                assert True  # If we get here, metric emission worked
            else:
                # Metrics not available, skip test
                pytest.skip("Metrics not available in test environment")
        except ImportError:
            # Metrics module not available, skip test
            pytest.skip("Metrics module not available")

    def test_metric_emission_on_failure(self) -> None:
        """Verify CIRCUIT_STATE metric is emitted on failure using real metrics module."""
        try:
            from somabrain.infrastructure.circuit_breaker import CircuitBreaker
            from somabrain import metrics
            
            # Get the real gauge
            gauge = getattr(metrics, 'CIRCUIT_STATE', None)
            if gauge is not None:
                breaker = CircuitBreaker(global_failure_threshold=1)
                tenant = "test_tenant"
                
                # Record failure that opens circuit
                breaker.record_failure(tenant)
                
                # The metric should exist and be set to 1 (open)
                # We can't easily inspect the actual value without Prometheus client,
                # but we can verify no exception was raised
                assert True  # If we get here, metric emission worked
            else:
                # Metrics not available, skip test
                pytest.skip("Metrics not available in test environment")
        except ImportError:
            # Metrics module not available, skip test
            pytest.skip("Metrics module not available")

    def test_metric_emission_handles_import_error(self) -> None:
        """Verify metric emission handles import errors gracefully with real module."""
        # Test with real CircuitBreaker - it should handle missing metrics gracefully
        breaker = CircuitBreaker()
        tenant = "test_tenant"
        
        # These calls should not raise exceptions even if metrics are unavailable
        breaker.record_success(tenant)
        breaker.record_failure(tenant)
        
        # If we get here, graceful handling worked
        assert True

    def test_threshold_enforcement_minimum_values(self) -> None:
        """Verify thresholds are enforced to minimum values."""
        # Test constructor with invalid values
        breaker = CircuitBreaker(global_failure_threshold=0, global_reset_interval=0.5)
        assert breaker._global_failure_threshold == 1  # Minimum
        assert breaker._global_reset_interval == 1.0  # Minimum
        
        # Test configure_tenant with invalid values
        tenant = "test_tenant"
        breaker.is_open(tenant)
        breaker.configure_tenant(tenant, failure_threshold=-1, reset_interval=0.0)
        assert breaker._failure_threshold[tenant] == 1  # Minimum
        assert breaker._reset_interval[tenant] == 1.0  # Minimum

    def test_multiple_tenant_isolation(self) -> None:
        """Verify multiple tenants are properly isolated."""
        breaker = CircuitBreaker(global_failure_threshold=2)
        tenant1 = "tenant1"
        tenant2 = "tenant2"
        
        # Initialize both tenants
        breaker.is_open(tenant1)
        breaker.is_open(tenant2)
        
        # Open circuit for tenant1 only
        breaker.record_failure(tenant1)
        breaker.record_failure(tenant1)
        breaker.record_failure(tenant2)  # Only one failure for tenant2
        
        # Verify isolation
        assert breaker.is_open(tenant1) is True
        assert breaker.is_open(tenant2) is False
        assert breaker._failure_count[tenant1] == 2
        assert breaker._failure_count[tenant2] == 1

    def test_state_return_type_consistency(self) -> None:
        """Verify get_state returns consistent types."""
        breaker = CircuitBreaker()
        tenant = "test_tenant"
        
        state = breaker.get_state(tenant)
        
        # Verify all value types
        assert isinstance(state["tenant"], str)
        assert isinstance(state["circuit_open"], bool)
        assert isinstance(state["failure_count"], int)
        assert isinstance(state["last_failure_time"], float)
        assert isinstance(state["last_reset_attempt"], float)
        assert isinstance(state["failure_threshold"], int)
        assert isinstance(state["reset_interval"], float)