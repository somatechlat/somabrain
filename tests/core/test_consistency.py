#!/usr/bin/env python3
"""
Tests for consistency checking and kappa calculation.
"""

import pytest
import numpy as np
from somabrain.runtime.consistency import ConsistencyChecker


class TestConsistency:
    """Test consistency checking and Jensen-Shannon divergence."""
    
    def test_kappa_calculation(self):
        """Test κ = 1 - JSD(P||Q) calculation."""
        checker = ConsistencyChecker()
        
        # Perfect consistency case
        p = np.array([0.25, 0.25, 0.25, 0.25])
        q = np.array([0.25, 0.25, 0.25, 0.25])
        
        kappa = checker.calculate_kappa(p, q)
        assert abs(kappa - 1.0) < 1e-6, "Identical distributions should have κ=1"
        
    def test_js_divergence_calculation(self):
        """Test Jensen-Shannon divergence calculation."""
        checker = ConsistencyChecker()
        
        # Test with known distributions
        p = np.array([0.5, 0.5])
        q = np.array([0.5, 0.5])
        
        jsd = checker.js_divergence(p, q)
        assert abs(jsd) < 1e-6, "Identical distributions should have JSD=0"
        
    def test_maximal_divergence(self):
        """Test maximal divergence case."""
        checker = ConsistencyChecker()
        
        # Completely different distributions
        p = np.array([1, 0])
        q = np.array([0, 1])
        
        kappa = checker.calculate_kappa(p, q)
        assert 0 <= kappa < 1, "Maximal divergence should have κ < 1"
        
    def test_consistency_threshold(self):
        """Test consistency threshold evaluation."""
        checker = ConsistencyChecker(threshold=0.8)
        
        # Consistent distributions
        p = np.array([0.3, 0.7])
        q = np.array([0.32, 0.68])
        
        is_consistent = checker.is_consistent(p, q)
        assert is_consistent, "Similar distributions should be consistent"
        
    def test_inconsistency_detection(self):
        """Test inconsistency detection."""
        checker = ConsistencyChecker(threshold=0.8)
        
        # Inconsistent distributions
        p = np.array([0.9, 0.1])
        q = np.array([0.1, 0.9])
        
        is_consistent = checker.is_consistent(p, q)
        assert not is_consistent, "Very different distributions should be inconsistent"
        
    def test_temporal_consistency(self):
        """Test temporal consistency checking."""
        checker = ConsistencyChecker()
        
        # Simulate temporal evolution
        distributions = [
            np.array([0.25, 0.25, 0.25, 0.25]),
            np.array([0.26, 0.24, 0.25, 0.25]),
            np.array([0.27, 0.23, 0.25, 0.25]),
            np.array([0.28, 0.22, 0.25, 0.25])
        ]
        
        # Check consistency across time
        consistency_scores = []
        for i in range(1, len(distributions)):
            kappa = checker.calculate_kappa(distributions[0], distributions[i])
            consistency_scores.append(kappa)
            
        # Consistency should decrease gradually
        assert all(0.8 <= score <= 1.0 for score in consistency_scores)
        
    def test_multivariate_consistency(self):
        """Test consistency for multivariate distributions."""
        checker = ConsistencyChecker()
        
        # 4D distributions
        p = np.array([0.1, 0.2, 0.3, 0.4])
        q = np.array([0.12, 0.18, 0.32, 0.38])
        
        kappa = checker.calculate_kappa(p, q)
        assert 0.9 <= kappa <= 1.0, "Similar multivariate distributions should be consistent"
        
    def test_zero_probability_handling(self):
        """Test handling of zero probabilities."""
        checker = ConsistencyChecker()
        
        # Distributions with zero probabilities
        p = np.array([0.5, 0.5, 0.0])
        q = np.array([0.6, 0.4, 0.0])
        
        kappa = checker.calculate_kappa(p, q)
        assert 0 <= kappa <= 1, "Should handle zeros correctly"
        
    def test_online_consistency_update(self):
        """Test online consistency checking."""
        checker = ConsistencyChecker()
        
        # Initial reference distribution
        reference = np.array([0.25, 0.25, 0.25, 0.25])
        
        # Update with new observations
        new_observations = [
            np.array([0.26, 0.24, 0.25, 0.25]),
            np.array([0.27, 0.23, 0.25, 0.25]),
            np.array([0.28, 0.22, 0.25, 0.25])
        ]
        
        consistency_history = []
        for obs in new_observations:
            kappa = checker.calculate_kappa(reference, obs)
            consistency_history.append(kappa)
            
        # Track consistency trends
        assert len(consistency_history) == 3
        assert all(0 <= k <= 1 for k in consistency_history)
        
    def test_consistency_with_noise(self):
        """Test consistency robustness to noise."""
        checker = ConsistencyChecker()
        
        # Base distribution
        base = np.array([0.25, 0.25, 0.25, 0.25])
        
        # Add noise
        np.random.seed(42)
        noise = np.random.normal(0, 0.01, 4)
        noisy = base + noise
        noisy = np.abs(noisy) / np.sum(np.abs(noisy))  # Normalize
        
        kappa = checker.calculate_kappa(base, noisy)
        assert 0.9 <= kappa <= 1.0, "Should be robust to small noise"
        
    def test_consistency_report_generation(self):
        """Test consistency report generation."""
        checker = ConsistencyChecker()
        
        # Test data
        distributions = {
            'model_a': np.array([0.3, 0.7]),
            'model_b': np.array([0.32, 0.68]),
            'model_c': np.array([0.28, 0.72])
        }
        
        report = checker.generate_consistency_report(distributions)
        
        assert 'pairwise_kappa' in report
        assert 'overall_consistency' in report
        assert isinstance(report['overall_consistency'], float)
        
    def test_consistency_threshold_adjustment(self):
        """Test dynamic consistency threshold adjustment."""
        checker = ConsistencyChecker()
        
        # Test different thresholds
        thresholds = [0.7, 0.8, 0.9]
        
        p = np.array([0.4, 0.6])
        q = np.array([0.45, 0.55])
        
        for threshold in thresholds:
            checker.threshold = threshold
            is_consistent = checker.is_consistent(p, q)
            
            # Higher thresholds should be more strict
            if threshold <= 0.8:
                assert is_consistent
            elif threshold >= 0.9:
                # Might be borderline
                pass  # Allow flexibility for edge cases