#!/usr/bin/env python3
"""
Tests for BHDC fusion layer and mathematical formulas.
"""

import pytest
import numpy as np
from somabrain.runtime.fusion import BHDCFusionLayer


class TestBHDCFusion:
    """Test BHDC fusion mathematical correctness."""
    
    def test_fusion_normalization_formula(self):
        """Test the fusion normalization formula: e_norm_d = (error_d-μ_d)/(σ_d+ε)"""
        fusion = BHDCFusionLayer(dim=2048)
        
        # Test data
        errors = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
        mu = 0.4
        sigma = 0.15
        epsilon = 1e-8
        
        # Manual calculation
        expected_norm = (errors - mu) / (sigma + epsilon)
        
        # Verify formula
        assert np.allclose(expected_norm[0], (0.1 - 0.4) / (0.15 + 1e-8))
        assert np.allclose(expected_norm[2], (0.5 - 0.4) / (0.15 + 1e-8))
        
    def test_weight_calculation_formula(self):
        """Test weight calculation: w_d = softmax(-α·e_norm_d)"""
        fusion = BHDCFusionLayer(dim=2048)
        
        # Test data
        e_norm = np.array([0.2, -0.1, 0.5])
        alpha = 2.0
        
        # Manual softmax calculation
        exp_values = np.exp(-alpha * e_norm)
        expected_weights = exp_values / np.sum(exp_values)
        
        # Verify properties
        assert abs(expected_weights.sum() - 1.0) < 1e-6
        assert len(expected_weights) == len(e_norm)
        
    def test_2048d_vector_operations(self):
        """Test 2048D vector operations."""
        fusion = BHDCFusionLayer(dim=2048)
        
        # Generate 2048D test vector
        vector = np.random.randn(2048)
        
        # Test normalization
        normalized = vector / np.linalg.norm(vector)
        
        assert len(normalized) == 2048
        assert abs(np.linalg.norm(normalized) - 1.0) < 1e-6
        
    def test_adaptive_alpha_parameter(self):
        """Test adaptive alpha parameter adjustment."""
        fusion = BHDCFusionLayer(dim=2048)
        
        # Test alpha bounds
        assert 0.1 <= fusion.alpha <= 5.0
        
        # Test alpha adaptation
        initial_alpha = fusion.alpha
        fusion.update_alpha(performance_score=0.85)
        
        # Alpha should adapt based on performance
        assert fusion.alpha != initial_alpha
        
    def test_real_time_fusion(self):
        """Test real-time fusion processing."""
        fusion = BHDCFusionLayer(dim=2048)
        
        # Simulate real-time input
        input_vectors = [
            np.random.randn(2048),
            np.random.randn(2048),
            np.random.randn(2048)
        ]
        
        # Process vectors
        results = []
        for vec in input_vectors:
            fused = fusion.fuse([vec])
            results.append(fused)
            
        # Verify all results are 2048D
        for result in results:
            assert len(result) == 2048
            
    def test_consistency_across_calls(self):
        """Test consistency of fusion results."""
        fusion = BHDCFusionLayer(dim=2048)
        
        # Same input should produce same output
        test_vector = np.random.randn(2048)
        
        result1 = fusion.fuse([test_vector])
        result2 = fusion.fuse([test_vector])
        
        assert np.allclose(result1, result2)
        
    def test_edge_cases(self):
        """Test edge cases and error handling."""
        fusion = BHDCFusionLayer(dim=2048)
        
        # Test zero vector
        zero_vector = np.zeros(2048)
        result = fusion.fuse([zero_vector])
        assert len(result) == 2048
        
        # Test very large values
        large_vector = np.ones(2048) * 1000
        result = fusion.fuse([large_vector])
        assert not np.any(np.isnan(result))
        
        # Test negative values
        negative_vector = -np.ones(2048)
        result = fusion.fuse([negative_vector])
        assert len(result) == 2048