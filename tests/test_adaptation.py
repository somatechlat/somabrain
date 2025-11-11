#!/usr/bin/env python3
"""
Tests for adaptation engine and learning parameters.
"""

import pytest
import numpy as np
from somabrain.learning.adaptation import AdaptationEngine


class TestAdaptation:
    """Test adaptation engine and parameter updates."""
    
    def test_tau_annealing_exponential(self):
        """Test exponential tau annealing: τ_t = τ_0 * γ^t"""
        adapt = AdaptationEngine()
        
        tau_0 = 1.0
        gamma = 0.99
        steps = 100
        
        # Manual calculation
        expected_tau = tau_0 * (gamma ** steps)
        
        # Test monotonic decrease
        taus = [adapt.exponential_decay(tau_0, gamma, t) for t in range(steps)]
        assert all(taus[i] >= taus[i+1] for i in range(steps-1))
        assert abs(taus[-1] - expected_tau) < 1e-6
        
    def test_tau_annealing_linear(self):
        """Test linear tau annealing: τ_t = max(τ_min, τ_0 - αt)"""
        adapt = AdaptationEngine()
        
        tau_0 = 1.0
        alpha = 0.01
        tau_min = 0.1
        steps = 50
        
        # Manual calculation
        expected_tau = max(tau_min, tau_0 - alpha * steps)
        
        # Test linear decrease
        taus = [adapt.linear_decay(tau_0, alpha, tau_min, t) for t in range(steps)]
        assert all(taus[i] >= taus[i+1] for i in range(steps-1))
        assert abs(taus[-1] - expected_tau) < 1e-6
        
    def test_real_time_parameter_update(self):
        """Test real-time parameter updates based on feedback."""
        adapt = AdaptationEngine()
        
        # Initial parameters
        initial_lr = adapt.learning_rate
        initial_tau = adapt.tau
        
        # Simulate positive feedback
        feedback = {"reward": 1.0, "error": 0.1}
        adapt.update_parameters(feedback)
        
        # Parameters should adapt
        assert adapt.learning_rate != initial_lr or adapt.tau != initial_tau
        
    def test_adaptive_learning_rate(self):
        """Test adaptive learning rate adjustment."""
        adapt = AdaptationEngine()
        
        # Test different performance scenarios
        scenarios = [
            {"reward": 1.0, "expected_change": "decrease"},
            {"reward": 0.0, "expected_change": "increase"},
            {"reward": 0.5, "expected_change": "small"}
        ]
        
        for scenario in scenarios:
            initial_lr = adapt.learning_rate
            adapt.update_parameters({"reward": scenario["reward"]})
            
            # Verify learning rate adaptation
            new_lr = adapt.learning_rate
            if scenario["expected_change"] == "decrease":
                assert new_lr <= initial_lr
            elif scenario["expected_change"] == "increase":
                assert new_lr >= initial_lr
                
    def test_online_learning_convergence(self):
        """Test online learning convergence."""
        adapt = AdaptationEngine()
        
        # Simulate learning process
        np.random.seed(42)
        n_steps = 100
        parameters_history = []
        
        for step in range(n_steps):
            # Simulate feedback
            feedback = {
                "reward": np.random.random(),
                "error": np.random.exponential(0.1)
            }
            
            adapt.update_parameters(feedback)
            parameters_history.append({
                "learning_rate": adapt.learning_rate,
                "tau": adapt.tau
            })
            
        # Verify parameters stay within bounds
        for params in parameters_history:
            assert 0.001 <= params["learning_rate"] <= 1.0
            assert 0.01 <= params["tau"] <= 10.0
            
    def test_parameter_bounds_enforcement(self):
        """Test parameter bounds enforcement."""
        adapt = AdaptationEngine()
        
        # Test bounds
        bounds = {
            "learning_rate": (0.001, 1.0),
            "tau": (0.01, 10.0),
            "alpha": (0.1, 5.0)
        }
        
        for param_name, (min_val, max_val) in bounds.items():
            param_value = getattr(adapt, param_name)
            assert min_val <= param_value <= max_val, f"{param_name} out of bounds"
            
    def test_experience_replay_integration(self):
        """Test integration with experience replay."""
        adapt = AdaptationEngine()
        
        # Simulate experience buffer
        experiences = [
            {"state": [1, 2, 3], "action": 0, "reward": 1.0},
            {"state": [4, 5, 6], "action": 1, "reward": 0.5},
            {"state": [7, 8, 9], "action": 2, "reward": 0.8}
        ]
        
        # Update from experiences
        for exp in experiences:
            adapt.update_from_experience(exp)
            
        # Verify parameters updated
        assert adapt.total_experiences >= len(experiences)
        
    def test_meta_learning_initialization(self):
        """Test meta-learning parameter initialization."""
        adapt = AdaptationEngine()
        
        # Test initialization from prior knowledge
        prior_params = {"learning_rate": 0.01, "tau": 1.0}
        adapt.initialize_from_prior(prior_params)
        
        assert adapt.learning_rate == 0.01
        assert adapt.tau == 1.0
        
    def test_performance_monitoring(self):
        """Test performance monitoring and adaptation triggers."""
        adapt = AdaptationEngine()
        
        # Test performance metrics
        metrics = {
            "accuracy": 0.85,
            "loss": 0.15,
            "reward": 0.9
        }
        
        # Should trigger adaptation based on metrics
        adapt.monitor_performance(metrics)
        
        assert hasattr(adapt, 'performance_history')
        assert len(adapt.performance_history) > 0
        
    def test_curriculum_learning_adaptation(self):
        """Test adaptation for curriculum learning."""
        adapt = AdaptationEngine()
        
        # Simulate curriculum stages
        stages = ["easy", "medium", "hard"]
        
        for stage in stages:
            adapt.set_curriculum_stage(stage)
            
            # Different stages should have different parameters
            if stage == "easy":
                assert adapt.learning_rate > 0.01
            elif stage == "hard":
                assert adapt.learning_rate < 0.1
                
    def test_transfer_learning_adaptation(self):
        """Test transfer learning parameter adaptation."""
        adapt = AdaptationEngine()
        
        # Simulate transfer from source to target
        source_task = "classification"
        target_task = "regression"
        
        adapt.transfer_parameters(source_task, target_task)
        
        # Should adjust parameters for new task
        assert adapt.task_type == target_task
        
    def test_hyperparameter_optimization(self):
        """Test hyperparameter optimization integration."""
        adapt = AdaptationEngine()
        
        # Test hyperparameter search
        search_space = {
            "learning_rate": [0.001, 0.01, 0.1],
            "tau": [0.1, 1.0, 10.0]
        }
        
        best_params = adapt.optimize_hyperparameters(search_space, n_trials=10)
        
        assert "learning_rate" in best_params
        assert "tau" in best_params
        assert best_params["learning_rate"] in search_space["learning_rate"]
        assert best_params["tau"] in search_space["tau"]