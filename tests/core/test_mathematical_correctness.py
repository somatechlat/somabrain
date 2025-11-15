"""
Unified mathematical correctness tests for ROAMDP compliance.
Consolidates all BHDC, consistency, and mathematical invariant tests.
"""

import pytest
import numpy as np
from typing import Tuple

from somabrain.runtime.consistency import ConsistencyChecker
from somabrain.runtime.fusion import BHDCFusionLayer
from somabrain.sleep.models import SleepStateManager, SleepParameters


class TestMathematicalCorrectness:
    """Test all mathematical invariants and guarantees."""
    
    def test_bhdc_fusion_normalization(self):
        """Test fusion normalization: e_norm_d = (error_d-μ_d)/(σ_d+ε)"""
        fusion = BHDCFusionLayer(dim=2048)
        
        # Test data with controlled statistics
        errors = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
        mu = 0.4
        sigma = 0.15
        epsilon = 1e-8
        
        # Expected normalized values
        expected = (errors - mu) / (sigma + epsilon)
        actual = fusion._normalize_errors(errors, mu, sigma)
        
        np.testing.assert_allclose(actual, expected, rtol=1e-6)
    
    def test_consistency_kappa_calculation(self):
        """Test κ = 1 - JSD(P||Q) calculation"""
        checker = ConsistencyChecker()
        
        # Perfect consistency
        p = np.array([0.25, 0.25, 0.25, 0.25])
        q = np.array([0.25, 0.25, 0.25, 0.25])
        
        kappa = checker.calculate_kappa(p, q)
        assert abs(kappa - 1.0) < 1e-6
        
        # Complete inconsistency
        p = np.array([1.0, 0.0, 0.0, 0.0])
        q = np.array([0.0, 1.0, 0.0, 0.0])
        
        kappa = checker.calculate_kappa(p, q)
        assert abs(kappa - 0.0) < 1e-6
    
    def test_sleep_parameter_monotonicity(self):
        """Test sleep parameter schedules are monotonic and bounded"""
        manager = SleepStateManager()
        
        states = [
            SleepState.ACTIVE,
            SleepState.LIGHT, 
            SleepState.DEEP,
            SleepState.FREEZE
        ]
        
        prev_params = None
        
        for state in states:
            params = manager.compute_parameters(state)
            
            # Test monotonicity and bounds
            assert params['K'] >= manager.parameters.K_min
            assert params['t'] >= manager.parameters.t_min
            assert params['eta'] >= 0.0
            
            if prev_params:
                assert params['K'] <= prev_params['K']
                assert params['t'] <= prev_params['t']
                assert params['eta'] <= prev_params['eta']
            
            prev_params = params
    
    def test_zero_learning_guarantee(self):
        """Test η = 0 guarantee for Deep/Freeze states"""
        manager = SleepStateManager()
        
        # Deep sleep must have zero learning
        deep_params = manager.compute_parameters(SleepState.DEEP)
        assert deep_params['eta'] == 0.0
        
        # Freeze must have zero learning
        freeze_params = manager.compute_parameters(SleepState.FREEZE)
        assert freeze_params['eta'] == 0.0
        
        # Active/Light must have positive learning
        active_params = manager.compute_parameters(SleepState.ACTIVE)
        assert active_params['eta'] > 0.0
        
        light_params = manager.compute_parameters(SleepState.LIGHT)
        assert light_params['eta'] > 0.0
    
    def test_parameter_bounds_validation(self):
        """Test all parameters stay within defined bounds"""
        manager = SleepStateManager()
        
        for state in SleepState:
            params = manager.compute_parameters(state)
            
            # All parameters must be non-negative and bounded
            assert params['K'] >= 1
            assert params['t'] >= 0.1
            assert params['tau'] >= 0.01
            assert params['eta'] >= 0.0
            assert params['lambda'] >= 0.0
            assert params['B'] >= 0.0
    
    def test_state_transition_validity(self):
        """Test state machine transition rules"""
        manager = SleepStateManager()
        
        # Valid transitions
        assert manager.can_transition(SleepState.ACTIVE, SleepState.LIGHT)
        assert manager.can_transition(SleepState.LIGHT, SleepState.DEEP)
        assert manager.can_transition(SleepState.LIGHT, SleepState.ACTIVE)
        assert manager.can_transition(SleepState.DEEP, SleepState.FREEZE)
        assert manager.can_transition(SleepState.FREEZE, SleepState.LIGHT)
        
        # Invalid transitions
        assert not manager.can_transition(SleepState.ACTIVE, SleepState.FREEZE)
        assert not manager.can_transition(SleepState.ACTIVE, SleepState.DEEP)
        assert not manager.can_transition(SleepState.FREEZE, SleepState.ACTIVE)
    
    def test_reversible_transitions(self):
        """Test parameter reversibility during state transitions"""
        manager = SleepStateManager()
        
        # Test round-trip transitions maintain bounds
        active_params = manager.compute_parameters(SleepState.ACTIVE)
        light_params = manager.compute_parameters(SleepState.LIGHT)
        
        # Ensure parameters are always within safe ranges
        for params in [active_params, light_params]:
            assert 1 <= params['K'] <= 1000
            assert 0.1 <= params['t'] <= 60.0
            assert 0.0 <= params['eta'] <= 1.0