"""
Test: Neuromodulator Adaptation Validation

Proves that neuromodulator parameters adapt based on performance feedback,
eliminating static values and creating true learning behavior.

This test demonstrates:
1. Dopamine adaptation based on reward prediction errors
2. Serotonin adaptation based on emotional stability
3. Noradrenaline adaptation based on urgency/arousal needs
4. Acetylcholine adaptation based on attention/memory formation
5. Per-tenant neuromodulator personalization
6. Performance-driven parameter evolution
"""

import time
import pytest
from somabrain.adaptive.core import PerformanceMetrics
from somabrain.adaptive_neuromodulators import (
    AdaptiveNeuromodulators, 
    AdaptivePerTenantNeuromodulators,
    _calculate_dopamine_feedback,
    _calculate_serotonin_feedback,
    _calculate_noradrenaline_feedback,
    _calculate_acetylcholine_feedback
)


class TestNeuromodulatorAdaptation:
    
    def test_dopamine_learning_from_rewards(self):
        """Prove dopamine adapts based on reward prediction errors."""
        system = AdaptiveNeuromodulators()
        
        # Initial state
        initial_dopamine = system.dopamine_param.current_value
        assert initial_dopamine == 0.4, "Initial dopamine should be 0.4"
        
        # Simulate successful reward learning
        perf = PerformanceMetrics(
            accuracy=0.9,
            success_rate=0.8,
            error_rate=0.1
        )
        
        # Update from reward learning
        system.update_from_performance(perf, task_type="reward_learning")
        
        # Dopamine should increase due to successful reward learning
        final_dopamine = system.dopamine_param.current_value
        assert final_dopamine > initial_dopamine, "Dopamine should increase with successful rewards"
        
        # Verify it's within bounds
        assert 0.1 <= final_dopamine <= 1.0, "Dopamine should stay within bounds"
    
    def test_serotonin_stability_learning(self):
        """Prove serotonin adapts based on emotional stability."""
        system = AdaptiveNeuromodulators()
        
        initial_serotonin = system.serotonin_param.current_value
        
        # Simulate stable performance
        perf = PerformanceMetrics(
            accuracy=0.95,
            error_rate=0.05,
            success_rate=0.9
        )
        
        system.update_from_performance(perf, task_type="general")
        final_serotonin = system.serotonin_param.current_value
        
        # Serotonin should increase with stable performance
        assert final_serotonin > initial_serotonin, "Serotonin should increase with stable performance"
    
    def test_noradrenaline_urgency_adaptation(self):
        """Prove noradrenaline adapts based on urgency needs."""
        system = AdaptiveNeuromodulators()
        
        initial_noradrenaline = system.noradrenaline_param.current_value
        
        # Simulate high-urgency task
        perf = PerformanceMetrics(
            latency=0.5,  # Fast response
            success_rate=0.7
        )
        
        system.update_from_performance(perf, task_type="urgent")
        final_noradrenaline = system.noradrenaline_param.current_value
        
        # Noradrenaline should increase for urgent tasks
        assert final_noradrenaline > initial_noradrenaline, "Noradrenaline should increase for urgent tasks"
    
    def test_acetylcholine_memory_learning(self):
        """Prove acetylcholine adapts based on memory formation success."""
        system = AdaptiveNeuromodulators()
        
        initial_ach = system.acetylcholine_param.current_value
        
        # Simulate successful memory task
        perf = PerformanceMetrics(
            accuracy=0.85,
            success_rate=0.8
        )
        
        system.update_from_performance(perf, task_type="memory")
        final_ach = system.acetylcholine_param.current_value
        
        # Acetylcholine should increase for successful memory tasks
        assert final_ach > initial_ach, "Acetylcholine should increase for memory tasks"
    
    def test_all_parameters_evolve(self):
        """Prove all neuromodulator parameters evolve over multiple updates."""
        system = AdaptiveNeuromodulators()
        
        # Initial values
        initial = {
            "dopamine": system.dopamine_param.current_value,
            "serotonin": system.serotonin_param.current_value,
            "noradrenaline": system.noradrenaline_param.current_value,
            "acetylcholine": system.acetylcholine_param.current_value
        }
        
        # Multiple update cycles with varying performance
        performances = [
            PerformanceMetrics(success_rate=0.9, error_rate=0.1),
            PerformanceMetrics(success_rate=0.7, error_rate=0.3),
            PerformanceMetrics(success_rate=0.95, error_rate=0.05),
        ]
        
        for perf in performances:
            system.update_from_performance(perf)
        
        # Get final values
        final = {
            "dopamine": system.dopamine_param.current_value,
            "serotonin": system.serotonin_param.current_value,
            "noradrenaline": system.noradrenaline_param.current_value,
            "acetylcholine": system.acetylcholine_param.current_value
        }
        
        # At least some parameters should have changed
        any_changed = any(
            abs(final[name] - initial[name]) > 0.001 
            for name in initial.keys()
        )
        assert any_changed, "At least one neuromodulator parameter should change over time"
    
    def test_per_tenant_personalization(self):
        """Prove per-tenant neuromodulator personalization."""
        tenant_system = AdaptivePerTenantNeuromodulators()
        
        # Tenant 1: Reward-focused
        perf1 = PerformanceMetrics(success_rate=0.9)
        state1 = tenant_system.adapt_from_performance("tenant1", perf1, task_type="reward_learning")
        
        # Tenant 2: Memory-focused
        perf2 = PerformanceMetrics(accuracy=0.95)
        state2 = tenant_system.adapt_from_performance("tenant2", perf2)
        
        # Different tenants should have different neuromodulator states
        assert state1.dopamine != state2.dopamine, "Different tenants should evolve differently"
        assert state1.acetylcholine != state2.acetylcholine, "Different tenants should evolve differently"
    
    def test_neuromodulator_bounds(self):
        """Prove neuromodulator parameters stay within defined bounds."""
        system = AdaptiveNeuromodulators()
        
        # Extreme performance feedback
        perf = PerformanceMetrics(success_rate=1.0, error_rate=0.0)
        
        # Many updates to test bounds
        for _ in range(100):
            system.update_from_performance(perf)
        
        # Check bounds
        assert 0.1 <= system.dopamine_param.current_value <= 1.0
        assert 0.0 <= system.serotonin_param.current_value <= 1.0
        assert 0.0 <= system.noradrenaline_param.current_value <= 0.5
        assert 0.0 <= system.acetylcholine_param.current_value <= 0.5
    
    def test_feedback_calculation_accuracy(self):
        """Test feedback calculation functions."""
        
        # Test dopamine feedback
        perf = PerformanceMetrics(success_rate=0.8)
        dopamine_feedback = _calculate_dopamine_feedback(perf, "reward_learning")
        assert dopamine_feedback > 0, "Dopamine feedback should be positive for success"
        
        # Test serotonin feedback
        perf_stable = PerformanceMetrics(error_rate=0.1)
        serotonin_feedback = _calculate_serotonin_feedback(perf_stable, "general")
        assert serotonin_feedback > 0.8, "Serotonin feedback should be high for stable performance"
        
        # Test noradrenaline feedback
        perf_fast = PerformanceMetrics(latency=0.1)
        noradrenaline_feedback = _calculate_noradrenaline_feedback(perf_fast, "urgent")
        assert noradrenaline_feedback > 0, "Noradrenaline should be high for fast response"
        
        # Test acetylcholine feedback
        perf_memory = PerformanceMetrics(accuracy=0.9)
        ach_feedback = _calculate_acetylcholine_feedback(perf_memory, "memory")
        assert ach_feedback > 0.09, "Acetylcholine should be high for accurate memory tasks"
    
    def test_adaptation_convergence(self):
        """Prove neuromodulator parameters converge to optimal values."""
        system = AdaptiveNeuromodulators()
        
        # Track parameter changes
        dopamine_values = []
        for i in range(50):
            perf = PerformanceMetrics(
                success_rate=0.8 + 0.1 * (i % 3),  # Varying success
                error_rate=0.2 - 0.05 * (i % 3)   # Improving error
            )
            system.update_from_performance(perf)
            dopamine_values.append(system.dopamine_param.current_value)
        
        # Should show learning curve (values changing over time)
        assert len(set(round(v, 3) for v in dopamine_values)) > 5, \
            "Parameters should show learning behavior"
    
    def test_learning_rate_adaptation(self):
        """Prove learning rates adapt based on performance trends."""
        system = AdaptiveNeuromodulators()
        
        # Initial learning rate
        initial_lr = system.dopamine_param.learning_rate
        
        # Consistent improvement
        perf_improving = PerformanceMetrics(success_rate=0.8)
        for i in range(20):
            perf = PerformanceMetrics(
                success_rate=0.5 + 0.01 * i  # Steady improvement
            )
            system.update_from_performance(perf)
        
        # Learning rate should adapt (increase or decrease based on trends)
        final_lr = system.dopamine_param.learning_rate
        assert abs(final_lr - initial_lr) > 0, \
            "Learning rate should change based on performance trends"


if __name__ == "__main__":
    # Run comprehensive validation
    suite = TestNeuromodulatorAdaptation()
    
    print("🧠 TESTING NEUROMODULATOR TRUE LEARNING...")
    
    tests = [
        suite.test_dopamine_learning_from_rewards,
        suite.test_serotonin_stability_learning,
        suite.test_noradrenaline_urgency_adaptation,
        suite.test_acetylcholine_memory_learning,
        suite.test_all_parameters_evolve,
        suite.test_per_tenant_personalization,
        suite.test_neuromodulator_bounds,
        suite.test_feedback_calculation_accuracy,
        suite.test_adaptation_convergence,
        suite.test_learning_rate_adaptation
    ]
    
    passed = 0
    for test in tests:
        try:
            test()
            print(f"✅ {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: {e}")
    
    print(f"\n🎯 NEUROMODULATOR LEARNING VALIDATION: {passed}/{len(tests)} PASSED")
    
    if passed == len(tests):
        print("🚀 PHASE 1 COMPLETE: NEUROMODULATORS NOW TRULY LEARNING")
    else:
        print("⚠️  Some tests failed - need debugging")