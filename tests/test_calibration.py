#!/usr/bin/env python3
"""
Tests for calibration pipeline and metrics.
"""

import pytest
import numpy as np
from somabrain.runtime.calibration import CalibrationPipeline


class TestCalibration:
    """Test calibration pipeline and metric calculations."""
    
    def test_ece_calculation(self):
        """Test Expected Calibration Error (ECE) calculation."""
        calib = CalibrationPipeline()
        
        # Perfect calibration case
        predictions = np.array([0.3, 0.7, 0.9])
        actual = np.array([0, 1, 1])
        
        ece = calib.calculate_ece(predictions, actual, n_bins=10)
        assert 0 <= ece <= 1, "ECE must be in [0,1]"
        
        # Perfect predictions should have ECE ~ 0
        perfect_predictions = actual.astype(float)
        perfect_ece = calib.calculate_ece(perfect_predictions, actual)
        assert abs(perfect_ece) < 1e-6, "Perfect predictions should have ECE ~ 0"
        
    def test_brier_score_calculation(self):
        """Test Brier score calculation."""
        calib = CalibrationPipeline()
        
        # Test with binary outcomes
        predictions = np.array([0.8, 0.3, 0.9, 0.2])
        actual = np.array([1, 0, 1, 0])
        
        brier = calib.calculate_brier(predictions, actual)
        assert 0 <= brier <= 1, "Brier score must be in [0,1]"
        
        # Perfect predictions
        perfect_brier = calib.calculate_brier(actual.astype(float), actual)
        assert abs(perfect_brier) < 1e-6, "Perfect predictions should have Brier ~ 0"
        
    def test_reliability_diagram(self):
        """Test reliability diagram generation."""
        calib = CalibrationPipeline()
        
        # Generate test data
        np.random.seed(42)
        n_samples = 1000
        predictions = np.random.beta(2, 5, n_samples)
        actual = np.random.binomial(1, predictions)
        
        # Generate reliability diagram
        bins, accuracies, confidences = calib.generate_reliability_diagram(
            predictions, actual, n_bins=10
        )
        
        assert len(bins) == 10, "Should have 10 bins"
        assert len(accuracies) == 10, "Should have 10 accuracy values"
        assert len(confidences) == 10, "Should have 10 confidence values"
        
    def test_calibration_curve(self):
        """Test calibration curve calculation."""
        calib = CalibrationPipeline()
        
        # Test data with known calibration
        predictions = np.array([0.2, 0.4, 0.6, 0.8])
        actual = np.array([0.1, 0.3, 0.7, 0.9])  # Slightly miscalibrated
        
        fraction_positives, mean_predicted = calib.calibration_curve(
            predictions, actual, n_bins=4
        )
        
        assert len(fraction_positives) == 4, "Should have 4 points"
        assert len(mean_predicted) == 4, "Should have 4 points"
        
    def test_temperature_scaling(self):
        """Test temperature scaling calibration."""
        calib = CalibrationPipeline()
        
        # Generate logits and labels
        np.random.seed(42)
        n_samples, n_classes = 100, 3
        logits = np.random.randn(n_samples, n_classes)
        labels = np.random.randint(0, n_classes, n_samples)
        
        # Apply temperature scaling
        calibrated_probs = calib.temperature_scaling(logits, labels)
        
        assert calibrated_probs.shape == (n_samples, n_classes)
        assert np.all(calibrated_probs >= 0), "Probabilities must be non-negative"
        assert np.all(calibrated_probs <= 1), "Probabilities must be <= 1"
        assert np.allclose(calibrated_probs.sum(axis=1), 1.0), "Probabilities must sum to 1"
        
    def test_adaptive_calibration(self):
        """Test adaptive calibration based on drift detection."""
        calib = CalibrationPipeline()
        
        # Simulate data with drift
        batch1_predictions = np.random.rand(100)
        batch1_actual = np.random.binomial(1, batch1_predictions)
        
        batch2_predictions = np.random.rand(100) * 0.8 + 0.1  # Shifted
        batch2_actual = np.random.binomial(1, batch2_predictions)
        
        # Check if recalibration needed
        drift_detected = calib.detect_calibration_drift(
            batch1_predictions, batch1_actual,
            batch2_predictions, batch2_actual
        )
        
        assert isinstance(drift_detected, bool)
        
    def test_online_calibration_update(self):
        """Test online calibration updates."""
        calib = CalibrationPipeline()
        
        # Initial calibration
        predictions = np.array([0.7, 0.8, 0.9])
        actual = np.array([1, 1, 1])
        
        calib.update_calibration(predictions, actual)
        
        # Online update with new data
        new_predictions = np.array([0.6, 0.85])
        new_actual = np.array([1, 1])
        
        calib.update_calibration(new_predictions, new_actual)
        
        # Should have updated parameters
        assert hasattr(calib, 'calibration_params')
        
    def test_multiclass_calibration(self):
        """Test multiclass calibration."""
        calib = CalibrationPipeline()
        
        # 3-class classification
        n_samples = 100
        predictions = np.random.dirichlet([1, 1, 1], n_samples)
        actual = np.eye(3)[np.random.choice(3, n_samples)]
        
        # Calculate ECE for multiclass
        multiclass_ece = calib.multiclass_ece(predictions, actual)
        assert 0 <= multiclass_ece <= 1, "Multiclass ECE must be in [0,1]"
        
    def test_confidence_intervals(self):
        """Test confidence interval calculation for calibration metrics."""
        calib = CalibrationPipeline()
        
        predictions = np.array([0.7, 0.8, 0.6, 0.9])
        actual = np.array([1, 1, 0, 1])
        
        # Calculate confidence intervals
        ece_ci = calib.calculate_ece_confidence_interval(predictions, actual)
        brier_ci = calib.calculate_brier_confidence_interval(predictions, actual)
        
        assert len(ece_ci) == 2, "Should return (lower, upper) bounds"
        assert len(brier_ci) == 2, "Should return (lower, upper) bounds"
        assert ece_ci[0] <= ece_ci[1], "Lower bound must be <= upper bound"
        assert brier_ci[0] <= brier_ci[1], "Lower bound must be <= upper bound"