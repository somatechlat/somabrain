"""
Integration Layer for Adaptive System.

This module integrates the adaptive learning system with existing SomaBrain components,
replacing hardcoded values with adaptive parameters.

Key Features:
- Seamless integration with existing scoring system
- Performance monitoring and feedback collection
- Dynamic parameter injection into existing components
- Real-time adaptation coordination
- Backward compatibility with existing APIs

Classes:
    AdaptiveScorer: Enhanced version of UnifiedScorer with adaptive weights
    AdaptiveConfig: Dynamic configuration management
    AdaptiveMonitor: Performance monitoring system
    AdaptiveIntegrator: Main integration coordinator
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from dataclasses import dataclass, field

from .core import (
    AdaptiveCore, PerformanceMetrics, AdaptiveWeights,
    AdaptiveThresholds, AdaptiveLearningRates
)


@dataclass
class ComponentPerformance:
    """Performance tracking for individual components."""
    
    cosine_accuracy: float = 0.0
    fd_coverage: float = 0.0
    recency_effectiveness: float = 0.0
    storage_efficiency: float = 0.0
    activation_effectiveness: float = 0.0
    retrieval_quality: float = 0.0
    convergence_speed: float = 0.0
    stability: float = 0.0
    learning_efficiency: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for processing."""
        return {
            "cosine": self.cosine_accuracy,
            "fd": self.fd_coverage,
            "recency": self.recency_effectiveness,
            "store": self.storage_efficiency,
            "act": self.activation_effectiveness,
            "similarity": self.retrieval_quality,
            "convergence_speed": self.convergence_speed,
            "stability": self.stability,
            "learning_efficiency": self.learning_efficiency
        }


@dataclass
class OperationMetrics:
    """Metrics for individual operations."""
    
    operation_type: str  # "remember" or "recall"
    query: str
    results_count: int
    latency: float
    success: bool
    similarity_scores: List[float] = field(default_factory=list)
    component_scores: Dict[str, float] = field(default_factory=dict)
    
    def calculate_performance(self) -> PerformanceMetrics:
        """Calculate performance metrics from operation data."""
        
        # Basic metrics
        success_rate = 1.0 if self.success else 0.0
        error_rate = 0.0 if self.success else 1.0
        
        # Calculate similarity-based metrics
        if self.similarity_scores:
            avg_similarity = np.mean(self.similarity_scores)
            max_similarity = max(self.similarity_scores) if self.similarity_scores else 0.0
        else:
            avg_similarity = 0.0
            max_similarity = 0.0
        
        # Estimate accuracy based on similarity and success
        accuracy = avg_similarity if self.success else 0.0
        
        # Estimate precision based on result quality
        precision = max_similarity if self.results_count > 0 else 0.0
        
        # Estimate recall based on results count (simplified)
        recall = min(1.0, self.results_count / 10.0) if self.success else 0.0
        
        # Throughput (inverse of latency)
        throughput = 1.0 / max(0.001, self.latency)
        
        return PerformanceMetrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            latency=self.latency,
            throughput=throughput,
            error_rate=error_rate,
            success_rate=success_rate
        )


class AdaptiveScorer:
    """Enhanced version of UnifiedScorer with adaptive weights."""
    
    def __init__(self, adaptive_core: AdaptiveCore):
        self.adaptive_core = adaptive_core
        self.operation_history: List[OperationMetrics] = []
        
    def score(self, query: np.ndarray, candidate: np.ndarray,
               recency_steps: Optional[int] = None,
               cosine_hint: Optional[float] = None) -> Tuple[float, Dict[str, float]]:
        """Score with adaptive weights and component tracking."""
        
        # Get current adaptive weights
        weights = self.adaptive_core.weights.get_normalized_weights()
        
        # Calculate component scores
        cosine_score = self._cosine_similarity(query, candidate)
        if cosine_hint is not None:
            cosine_score = cosine_hint
            
        fd_score = self._fd_similarity(query, candidate)
        recency_score = self._recency_score(recency_steps)
        
        # Track component performance
        component_scores = {
            "cosine": cosine_score,
            "fd": fd_score,
            "recency": recency_score
        }
        
        # Calculate weighted score
        total_score = (
            weights[0] * cosine_score +
            weights[1] * fd_score +
            weights[2] * recency_score
        )
        
        return max(0.0, min(1.0, total_score)), component_scores
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity."""
        na = float(np.linalg.norm(a))
        nb = float(np.linalg.norm(b))
        if na <= 1e-12 or nb <= 1e-12:
            return 0.0
        return float(np.dot(a, b) / (na * nb))
    
    def _fd_similarity(self, query: np.ndarray, candidate: np.ndarray) -> float:
        """Calculate FD subspace similarity (placeholder)."""
        # Placeholder for FD calculation
        # In real implementation, this would use the FD backend
        return self._cosine_similarity(query, candidate) * 0.9
    
    def _recency_score(self, recency_steps: Optional[int]) -> float:
        """Calculate recency score."""
        if recency_steps is None:
            return 0.0
        
        # Use adaptive tau from learning rates
        tau = self.adaptive_core.learning_rates.get_rates().get("tau_anneal", 32.0)
        age = max(0.0, float(recency_steps))
        return max(0.0, min(1.0, float(np.exp(-age / tau))))
    
    def record_operation(self, operation: OperationMetrics):
        """Record operation for performance tracking."""
        self.operation_history.append(operation)
        
        # Trigger adaptation if needed
        if self.adaptive_core.should_adapt():
            self._trigger_adaptation()
    
    def _trigger_adaptation(self):
        """Trigger the adaptation cycle."""
        if len(self.operation_history) < 10:
            return
        
        # Calculate aggregate performance metrics
        recent_ops = self.operation_history[-100:]  # Last 100 operations
        
        # Aggregate performance
        total_performance = PerformanceMetrics(
            accuracy=np.mean([op.calculate_performance().accuracy for op in recent_ops]),
            precision=np.mean([op.calculate_performance().precision for op in recent_ops]),
            recall=np.mean([op.calculate_performance().recall for op in recent_ops]),
            latency=np.mean([op.calculate_performance().latency for op in recent_ops]),
            throughput=np.mean([op.calculate_performance().throughput for op in recent_ops]),
            error_rate=np.mean([op.calculate_performance().error_rate for op in recent_ops]),
            success_rate=np.mean([op.calculate_performance().success_rate for op in recent_ops])
        )
        
        # Calculate component performances
        component_perfs = self._calculate_component_performances(recent_ops)
        
        # Calculate threshold statistics
        threshold_stats = self._calculate_threshold_stats(recent_ops)
        
        # Calculate learning statistics
        learning_stats = self._calculate_learning_stats(recent_ops)
        
        # Run adaptation
        adaptation_result = self.adaptive_core.adapt(
            total_performance,
            component_perfs,
            threshold_stats,
            learning_stats
        )
        
        print(f"🧠 Adaptation Cycle {adaptation_result['cycle']}: "
              f"Performance={adaptation_result['performance_score']:.3f}, "
              f"Weights=({adaptation_result['weights'][0]:.2f}, "
              f"{adaptation_result['weights'][1]:.2f}, "
              f"{adaptation_result['weights'][2]:.2f})")
    
    def _calculate_component_performances(self, operations: List[OperationMetrics]) -> Dict[str, float]:
        """Calculate individual component performances."""
        
        cosine_scores = []
        fd_scores = []
        recency_scores = []
        
        for op in operations:
            if "cosine" in op.component_scores:
                cosine_scores.append(op.component_scores["cosine"])
            if "fd" in op.component_scores:
                fd_scores.append(op.component_scores["fd"])
            if "recency" in op.component_scores:
                recency_scores.append(op.component_scores["recency"])
        
        return {
            "cosine": np.mean(cosine_scores) if cosine_scores else 0.5,
            "fd": np.mean(fd_scores) if fd_scores else 0.5,
            "recency": np.mean(recency_scores) if recency_scores else 0.5
        }
    
    def _calculate_threshold_stats(self, operations: List[OperationMetrics]) -> Dict[str, Dict[str, float]]:
        """Calculate threshold effectiveness statistics."""
        
        # Calculate storage efficiency (successful remembers / total remembers)
        remember_ops = [op for op in operations if op.operation_type == "remember"]
        storage_efficiency = np.mean([op.calculate_performance().success_rate for op in remember_ops]) if remember_ops else 0.5
        
        # Calculate activation effectiveness (successful recalls with results / total recalls)
        recall_ops = [op for op in operations if op.operation_type == "recall"]
        activation_effectiveness = np.mean([op.calculate_performance().success_rate for op in recall_ops if op.results_count > 0]) if recall_ops else 0.5
        
        # Calculate retrieval quality (average similarity of successful recalls)
        successful_recalls = [op for op in recall_ops if op.success and op.similarity_scores]
        retrieval_quality = np.mean([np.mean(op.similarity_scores) for op in successful_recalls]) if successful_recalls else 0.5
        
        return {
            "store": {"efficiency": storage_efficiency},
            "act": {"efficiency": activation_effectiveness},
            "similarity": {"quality": retrieval_quality}
        }
    
    def _calculate_learning_stats(self, operations: List[OperationMetrics]) -> Dict[str, float]:
        """Calculate learning effectiveness statistics."""
        
        # Calculate convergence speed (how quickly performance improves)
        if len(operations) < 20:
            return {"convergence_speed": 0.5, "stability": 0.5, "learning_efficiency": 0.5}
        
        # Look at performance trends
        recent_perfs = [op.calculate_performance().composite_score() for op in operations[-20:]]
        older_perfs = [op.calculate_performance().composite_score() for op in operations[-40:-20]]
        
        if len(older_perfs) == 0:
            return {"convergence_speed": 0.5, "stability": 0.5, "learning_efficiency": 0.5}
        
        # Convergence speed: improvement from older to recent
        convergence_speed = (np.mean(recent_perfs) - np.mean(older_perfs))
        
        # Stability: variance in recent performance
        stability = 1.0 / (1.0 + np.var(recent_perfs))
        
        # Learning efficiency: overall performance level
        learning_efficiency = np.mean(recent_perfs)
        
        return {
            "convergence_speed": convergence_speed,
            "stability": stability,
            "learning_efficiency": learning_efficiency
        }


class AdaptiveConfig:
    """Dynamic configuration management."""
    
    def __init__(self, adaptive_core: AdaptiveCore):
        self.adaptive_core = adaptive_core
        
    def get_scorer_weights(self) -> Tuple[float, float, float]:
        """Get current adaptive scorer weights."""
        return self.adaptive_core.weights.get_normalized_weights()
    
    def get_thresholds(self) -> Dict[str, float]:
        """Get current adaptive thresholds."""
        return self.adaptive_core.thresholds.get_thresholds()
    
    def get_learning_rates(self) -> Dict[str, float]:
        """Get current adaptive learning rates."""
        return self.adaptive_core.learning_rates.get_rates()
    
    def inject_into_config(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Inject adaptive values into configuration dictionary."""
        
        # Inject weights
        weights = self.get_scorer_weights()
        config_dict.update({
            "scorer_w_cosine": weights[0],
            "scorer_w_fd": weights[1],
            "scorer_w_recency": weights[2]
        })
        
        # Inject thresholds
        thresholds = self.get_thresholds()
        config_dict.update({
            "salience_threshold_store": thresholds["store"],
            "salience_threshold_act": thresholds["act"]
        })
        
        # Inject learning rates
        learning_rates = self.get_learning_rates()
        config_dict.update({
            "tau_anneal_rate": learning_rates["tau_anneal"],
            "tau_decay_rate": learning_rates["tau_decay"]
        })
        
        return config_dict


class AdaptiveIntegrator:
    """Main integration coordinator."""
    
    def __init__(self):
        self.adaptive_core = AdaptiveCore()
        self.adaptive_scorer = AdaptiveScorer(self.adaptive_core)
        self.adaptive_config = AdaptiveConfig(self.adaptive_core)
        
    def get_scorer(self) -> AdaptiveScorer:
        """Get the adaptive scorer instance."""
        return self.adaptive_scorer
    
    def get_config(self) -> AdaptiveConfig:
        """Get the adaptive config instance."""
        return self.adaptive_config
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        return self.adaptive_core.get_system_stats()
    
    def force_adaptation(self):
        """Force an adaptation cycle."""
        self.adaptive_scorer._trigger_adaptation()
    
    def record_remember_operation(self, query: str, success: bool, latency: float):
        """Record a remember operation for learning."""
        operation = OperationMetrics(
            operation_type="remember",
            query=query,
            results_count=1,  # Remember operations store one item
            latency=latency,
            success=success
        )
        self.adaptive_scorer.record_operation(operation)
    
    def record_recall_operation(self, query: str, results_count: int, 
                               latency: float, success: bool, similarity_scores: List[float]):
        """Record a recall operation for learning."""
        operation = OperationMetrics(
            operation_type="recall",
            query=query,
            results_count=results_count,
            latency=latency,
            success=success,
            similarity_scores=similarity_scores
        )
        self.adaptive_scorer.record_operation(operation)