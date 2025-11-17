"""
Core Adaptive Learning Infrastructure for SomaBrain.

This module transforms SomaBrain from a hardcoded mathematical engine
into a true dynamic learning system with self-evolving parameters.

Key Features:
- Parameter evolution based on performance feedback
- Adaptive weight optimization
- Emergent threshold discovery
- Self-tuning learning rates
- Performance-driven parameter adaptation

Classes:
    AdaptiveParameter: Core parameter with learning capability
    AdaptiveWeights: Dynamic weight management system
    AdaptiveThresholds: Self-discovering threshold system
    AdaptiveLearningRates: Self-tuning rate system
    AdaptiveCore: Main adaptive system coordinator
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from collections import deque


@dataclass
class PerformanceMetrics:
    """Performance metrics for parameter adaptation."""
    
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    latency: float = 0.0
    throughput: float = 0.0
    error_rate: float = 1.0
    success_rate: float = 0.0
    
    def composite_score(self) -> float:
        """Calculate composite performance score."""
        # Weighted combination of metrics
        return (
            0.3 * self.accuracy +
            0.2 * self.precision +
            0.2 * self.recall +
            0.1 * self.success_rate +
            0.1 * (1.0 - self.error_rate) +
            0.1 * min(1.0, 100.0 / max(0.001, self.latency))
        )


@dataclass
class AdaptiveParameter:
    """A parameter that learns and adapts based on performance feedback."""
    
    name: str
    initial_value: float
    min_value: float
    max_value: float
    learning_rate: float = 0.01
    momentum: float = 0.9
    
    # Internal state
    current_value: float = field(init=False)
    best_value: float = field(init=False)
    best_performance: float = field(init=False)
    history: deque = field(init=False)
    gradients: deque = field(init=False)
    
    def __post_init__(self):
        self.current_value = self.initial_value
        self.best_value = self.initial_value
        self.best_performance = 0.0
        self.history = deque(maxlen=100)  # Keep last 100 values
        self.gradients = deque(maxlen=10)  # Keep last 10 gradients
        
    def update(self, performance: PerformanceMetrics, gradient: Optional[float] = None) -> float:
        """Update parameter based on performance feedback."""
        
        current_perf = performance.composite_score()
        
        # Store current state
        self.history.append((self.current_value, current_perf, time.time()))
        
        # Update best value if performance improved
        if current_perf > self.best_performance:
            self.best_performance = current_perf
            self.best_value = self.current_value
        
        # Calculate gradient if not provided
        if gradient is None:
            gradient = self._estimate_gradient()
        
        # Apply momentum-based gradient descent
        self.gradients.append(gradient)
        avg_gradient = np.mean(list(self.gradients)) if self.gradients else gradient
        
        # Update parameter with momentum
        momentum_term = self.momentum * avg_gradient if self.gradients else 0.0
        update = self.learning_rate * (gradient + momentum_term)
        
        # Apply update with bounds checking
        new_value = self.current_value + update
        self.current_value = max(self.min_value, min(self.max_value, new_value))
        
        # Adaptive learning rate adjustment
        self._adjust_learning_rate(current_perf)
        
        return self.current_value
    
    def _estimate_gradient(self) -> float:
        """Estimate gradient from historical performance."""
        if len(self.history) < 2:
            return 0.0
        
        # Simple finite difference approximation
        recent_values = [v for v, _, _ in list(self.history)[-5:]]
        recent_perfs = [p for _, p, _ in list(self.history)[-5:]]
        
        if len(recent_values) < 2 or len(recent_perfs) < 2:
            return 0.0
        
        # Correlation between parameter changes and performance changes
        value_changes = np.diff(recent_values)
        perf_changes = np.diff(recent_perfs)
        
        if np.std(value_changes) == 0:
            return 0.0
        
        correlation = np.corrcoef(value_changes, perf_changes)[0, 1]
        return correlation if not math.isnan(correlation) else 0.0
    
    def _adjust_learning_rate(self, current_perf: float):
        """Adapt learning rate based on performance trends."""
        if len(self.history) < 10:
            return
        
        # Check if performance is improving or plateauing
        recent_perfs = [p for _, p, _ in list(self.history)[-10:]]
        perf_trend = np.polyfit(range(len(recent_perfs)), recent_perfs, 1)[0]
        
        # Increase learning rate if improving, decrease if plateauing/declining
        if perf_trend > 0.01:  # Improving
            self.learning_rate *= 1.05
        elif perf_trend < -0.01:  # Declining
            self.learning_rate *= 0.95
        else:  # Plateauing
            self.learning_rate *= 0.99
        
        # Keep learning rate in reasonable bounds
        self.learning_rate = max(0.001, min(0.1, self.learning_rate))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get parameter statistics."""
        return {
            "name": self.name,
            "current_value": self.current_value,
            "initial_value": self.initial_value,
            "best_value": self.best_value,
            "best_performance": self.best_performance,
            "learning_rate": self.learning_rate,
            "momentum": self.momentum,
            "history_size": len(self.history),
            "adaptation_count": len(self.gradients)
        }


@dataclass
class AdaptiveWeights:
    """Dynamic weight management system for scoring components."""
    
    # Core scoring weights
    cosine: AdaptiveParameter = field(init=False)
    fd: AdaptiveParameter = field(init=False)
    recency: AdaptiveParameter = field(init=False)
    
    def __post_init__(self):
        # Initialize adaptive parameters for weights
        self.cosine = AdaptiveParameter(
            name="cosine_weight",
            initial_value=0.6,
            min_value=0.0,
            max_value=1.0,
            learning_rate=0.02
        )
        
        self.fd = AdaptiveParameter(
            name="fd_weight",
            initial_value=0.25,
            min_value=0.0,
            max_value=1.0,
            learning_rate=0.02
        )
        
        self.recency = AdaptiveParameter(
            name="recency_weight",
            initial_value=0.15,
            min_value=0.0,
            max_value=1.0,
            learning_rate=0.02
        )
    
    def get_normalized_weights(self) -> Tuple[float, float, float]:
        """Get normalized weights that sum to 1.0."""
        weights = [
            self.cosine.current_value,
            self.fd.current_value,
            self.recency.current_value
        ]
        
        # Normalize to sum to 1.0
        total = sum(weights)
        if total == 0:
            return (0.33, 0.33, 0.34)  # Equal fallback
        
        return tuple(w / total for w in weights)
    
    def update(self, performance: PerformanceMetrics, 
               component_performances: Dict[str, float]) -> None:
        """Update weights based on component performance."""
        
        # Update each weight based on its component's performance
        if "cosine" in component_performances:
            self.cosine.update(performance, component_performances["cosine"])
        
        if "fd" in component_performances:
            self.fd.update(performance, component_performances["fd"])
        
        if "recency" in component_performances:
            self.recency.update(performance, component_performances["recency"])
    
    def get_stats(self) -> Dict[str, Any]:
        """Get weight statistics."""
        normalized = self.get_normalized_weights()
        return {
            "raw": {
                "cosine": self.cosine.current_value,
                "fd": self.fd.current_value,
                "recency": self.recency.current_value
            },
            "normalized": {
                "cosine": normalized[0],
                "fd": normalized[1],
                "recency": normalized[2]
            },
            "details": {
                "cosine": self.cosine.get_stats(),
                "fd": self.fd.get_stats(),
                "recency": self.recency.get_stats()
            }
        }


@dataclass
class AdaptiveThresholds:
    """Self-discovering threshold system."""
    
    store_threshold: AdaptiveParameter = field(init=False)
    act_threshold: AdaptiveParameter = field(init=False)
    similarity_threshold: AdaptiveParameter = field(init=False)
    
    def __post_init__(self):
        self.store_threshold = AdaptiveParameter(
            name="store_threshold",
            initial_value=0.5,
            min_value=0.0,
            max_value=1.0,
            learning_rate=0.015
        )
        
        self.act_threshold = AdaptiveParameter(
            name="act_threshold",
            initial_value=0.7,
            min_value=0.0,
            max_value=1.0,
            learning_rate=0.015
        )
        
        self.similarity_threshold = AdaptiveParameter(
            name="similarity_threshold",
            initial_value=0.2,
            min_value=0.0,
            max_value=1.0,
            learning_rate=0.015
        )
    
    def update(self, performance: PerformanceMetrics, 
               threshold_stats: Dict[str, Dict[str, float]]) -> None:
        """Update thresholds based on performance statistics."""
        
        # Update store threshold based on storage efficiency
        if "store" in threshold_stats:
            store_efficiency = threshold_stats["store"].get("efficiency", 0.5)
            self.store_threshold.update(performance, store_efficiency)
        
        # Update act threshold based on activation effectiveness
        if "act" in threshold_stats:
            act_efficiency = threshold_stats["act"].get("efficiency", 0.5)
            self.act_threshold.update(performance, act_efficiency)
        
        # Update similarity threshold based on retrieval quality
        if "similarity" in threshold_stats:
            similarity_quality = threshold_stats["similarity"].get("quality", 0.5)
            self.similarity_threshold.update(performance, similarity_quality)
    
    def get_thresholds(self) -> Dict[str, float]:
        """Get current threshold values."""
        return {
            "store": self.store_threshold.current_value,
            "act": self.act_threshold.current_value,
            "similarity": self.similarity_threshold.current_value
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get threshold statistics."""
        return {
            "thresholds": self.get_thresholds(),
            "details": {
                "store": self.store_threshold.get_stats(),
                "act": self.act_threshold.get_stats(),
                "similarity": self.similarity_threshold.get_stats()
            }
        }


@dataclass
class AdaptiveLearningRates:
    """Self-tuning learning rate system."""
    
    tau_anneal: AdaptiveParameter = field(init=False)
    tau_decay: AdaptiveParameter = field(init=False)
    base_learning_rate: AdaptiveParameter = field(init=False)
    
    def __post_init__(self):
        self.tau_anneal = AdaptiveParameter(
            name="tau_anneal_rate",
            initial_value=0.05,
            min_value=0.001,
            max_value=0.2,
            learning_rate=0.01
        )
        
        self.tau_decay = AdaptiveParameter(
            name="tau_decay_rate",
            initial_value=0.02,
            min_value=0.001,
            max_value=0.1,
            learning_rate=0.01
        )
        
        self.base_learning_rate = AdaptiveParameter(
            name="base_learning_rate",
            initial_value=0.01,
            min_value=0.001,
            max_value=0.1,
            learning_rate=0.005
        )
    
    def update(self, performance: PerformanceMetrics,
               learning_stats: Dict[str, float]) -> None:
        """Update learning rates based on learning performance."""
        
        # Update tau anneal rate based on convergence speed
        if "convergence_speed" in learning_stats:
            self.tau_anneal.update(performance, learning_stats["convergence_speed"])
        
        # Update tau decay rate based on stability
        if "stability" in learning_stats:
            self.tau_decay.update(performance, learning_stats["stability"])
        
        # Update base learning rate based on overall learning efficiency
        if "learning_efficiency" in learning_stats:
            self.base_learning_rate.update(performance, learning_stats["learning_efficiency"])
    
    def get_rates(self) -> Dict[str, float]:
        """Get current learning rate values."""
        return {
            "tau_anneal": self.tau_anneal.current_value,
            "tau_decay": self.tau_decay.current_value,
            "base": self.base_learning_rate.current_value
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get learning rate statistics."""
        return {
            "rates": self.get_rates(),
            "details": {
                "tau_anneal": self.tau_anneal.get_stats(),
                "tau_decay": self.tau_decay.get_stats(),
                "base": self.base_learning_rate.get_stats()
            }
        }


@dataclass
class AdaptiveCore:
    """Main adaptive system coordinator."""
    
    weights: AdaptiveWeights = field(init=False)
    thresholds: AdaptiveThresholds = field(init=False)
    learning_rates: AdaptiveLearningRates = field(init=False)
    
    # Performance tracking
    performance_history: deque = field(init=False)
    adaptation_cycle: int = field(init=False)
    
    def __post_init__(self):
        self.weights = AdaptiveWeights()
        self.thresholds = AdaptiveThresholds()
        self.learning_rates = AdaptiveLearningRates()
        self.performance_history = deque(maxlen=1000)
        self.adaptation_cycle = 0
    
    def adapt(self, performance: PerformanceMetrics,
              component_performances: Dict[str, float],
              threshold_stats: Dict[str, Dict[str, float]],
              learning_stats: Dict[str, float]) -> Dict[str, Any]:
        """Main adaptation cycle."""
        
        self.adaptation_cycle += 1
        
        # Store performance history
        self.performance_history.append({
            "cycle": self.adaptation_cycle,
            "performance": performance.composite_score(),
            "timestamp": time.time(),
            "metrics": performance.__dict__
        })
        
        # Update all adaptive components
        self.weights.update(performance, component_performances)
        self.thresholds.update(performance, threshold_stats)
        self.learning_rates.update(performance, learning_stats)
        
        # Return adaptation results
        return {
            "cycle": self.adaptation_cycle,
            "weights": self.weights.get_normalized_weights(),
            "thresholds": self.thresholds.get_thresholds(),
            "learning_rates": self.learning_rates.get_rates(),
            "performance_score": performance.composite_score()
        }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        return {
            "adaptation_cycle": self.adaptation_cycle,
            "performance_history_size": len(self.performance_history),
            "weights": self.weights.get_stats(),
            "thresholds": self.thresholds.get_stats(),
            "learning_rates": self.learning_rates.get_stats(),
            "recent_performance": [
                p for p in list(self.performance_history)[-10:]
            ]
        }
    
    def should_adapt(self) -> bool:
        """Determine if adaptation should run."""
        # Adapt every 100 operations or if performance is declining
        if self.adaptation_cycle == 0:
            return True
        
        if len(self.performance_history) < 10:
            return False
        
        # Check recent performance trend
        recent_perfs = [p["performance"] for p in list(self.performance_history)[-10:]]
        perf_trend = np.polyfit(range(len(recent_perfs)), recent_perfs, 1)[0]
        
        # Adapt if performance is declining or every 100 cycles
        return perf_trend < -0.01 or self.adaptation_cycle % 100 == 0