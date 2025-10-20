"""
SomaBrain Attention System - Phase 1: Basic Salience

This module implements basic attention and salience using fractal scaling principles.
Focuses on what's REAL and WORKING, not theoretical complexity.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import math


class FractalAttention:
    """
    Basic attention system using fractal scaling principles.

    Key Features:
    - Fractal-based salience calculation
    - Multi-scale attention processing
    - Energy-efficient focus mechanisms
    - Self-similar attention patterns
    """

    def __init__(self, base_scale: float = 0.1, max_scale: float = 10.0):
        """Initialize fractal attention system."""
        self.base_scale = base_scale
        self.max_scale = max_scale
        self.fractal_dimension = 1.26  # Natural scaling

        # Attention state
        self.current_focus = None
        self.attention_energy = 1.0
        self.scale_history = []

        print("🧠 Fractal Attention System initialized")
        print(f"   Scales: {base_scale} to {max_scale}")
        print(f"   Fractal dimension: {self.fractal_dimension}")

    def calculate_fractal_salience(self, content: str, embedding: np.ndarray,
                                 context_memories: List[Dict[str, Any]]) -> float:
        """
        Calculate salience using fractal scaling principles.

        Args:
            content: Content to evaluate
            embedding: Content embedding vector
            context_memories: Recent memories for context

        Returns:
            Salience score (0.0 to 1.0)
        """
        if not context_memories:
            return 0.5  # Default salience for new content

        # Calculate novelty (how different from recent memories)
        novelty_score = self._calculate_novelty(embedding, context_memories)

        # Calculate fractal resonance (self-similar patterns)
        resonance_score = self._calculate_fractal_resonance(embedding, context_memories)

        # Calculate temporal relevance (recency bias)
        temporal_score = self._calculate_temporal_relevance(context_memories)

        # Combine scores using fractal weighting
        salience = (
            0.4 * novelty_score +
            0.4 * resonance_score +
            0.2 * temporal_score
        )

        return min(1.0, max(0.0, salience))

    def _calculate_novelty(self, embedding: np.ndarray,
                          context_memories: List[Dict[str, Any]]) -> float:
        """Calculate novelty based on difference from recent memories."""
        if not context_memories:
            return 1.0

        similarities = []
        for memory in context_memories[-5:]:  # Last 5 memories
            if "embedding" in memory and memory["embedding"] is not None:
                try:
                    mem_embedding = np.array(memory["embedding"])
                    if mem_embedding.shape == embedding.shape:
                        similarity = np.dot(embedding, mem_embedding) / (
                            np.linalg.norm(embedding) * np.linalg.norm(mem_embedding)
                        )
                        similarities.append(similarity)
                except (ValueError, TypeError, ZeroDivisionError):
                    continue

        if not similarities:
            return 1.0

        # Novelty is inverse of average similarity
        avg_similarity = float(np.mean(similarities))
        novelty = 1.0 - avg_similarity

        return float(novelty)

    def _calculate_fractal_resonance(self, embedding: np.ndarray,
                                   context_memories: List[Dict[str, Any]]) -> float:
        """Calculate fractal resonance based on self-similar patterns."""
        if len(context_memories) < 3:
            return 0.5

        # Look for fractal patterns in embedding space
        resonance = 0.0
        scale_factors = [0.5, 0.25, 0.125]  # Fractal scales

        for scale in scale_factors:
            scaled_embedding = embedding * scale
            local_resonance = 0.0
            valid_memories = 0

            for memory in context_memories[-10:]:
                if "embedding" in memory and memory["embedding"] is not None:
                    try:
                        mem_embedding = np.array(memory["embedding"])
                        if mem_embedding.shape == embedding.shape:
                            # Calculate resonance at this scale
                            diff = np.abs(scaled_embedding - mem_embedding)
                            local_resonance += 1.0 / (1.0 + np.sum(diff))
                            valid_memories += 1
                    except (ValueError, TypeError):
                        continue

            if valid_memories > 0:
                resonance += local_resonance / valid_memories

        resonance /= len(scale_factors)
        return min(1.0, resonance * 2.0)  # Scale to 0-1 range

    def _calculate_temporal_relevance(self, context_memories: List[Dict[str, Any]]) -> float:
        """Calculate temporal relevance based on recency."""
        if not context_memories:
            return 0.5

        # Simple recency-based scoring
        now = datetime.now()
        recent_count = 0
        total_count = min(10, len(context_memories))

        for memory in context_memories[-total_count:]:
            if "timestamp" in memory:
                try:
                    mem_time = datetime.fromisoformat(memory["timestamp"])
                    hours_old = (now - mem_time).total_seconds() / 3600

                    # Recent memories (< 1 hour) get higher score
                    if hours_old < 1:
                        recent_count += 1
                    elif hours_old < 24:
                        recent_count += 0.5
                except:
                    pass

        return recent_count / total_count if total_count > 0 else 0.5

    def focus_attention(self, candidates: List[Dict[str, Any]],
                       context_memories: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Focus attention on the most salient candidate.

        Args:
            candidates: Potential items to focus on
            context_memories: Recent memory context

        Returns:
            Most salient candidate or None
        """
        if not candidates:
            return None

        best_candidate = None
        best_salience = -1.0

        for candidate in candidates:
            if "content" in candidate and "embedding" in candidate:
                content = candidate["content"]
                embedding = np.array(candidate["embedding"])

                salience = self.calculate_fractal_salience(
                    content, embedding, context_memories
                )

                if salience > best_salience:
                    best_salience = salience
                    best_candidate = candidate

        self.current_focus = best_candidate
        self.scale_history.append({
            "timestamp": datetime.now().isoformat(),
            "salience": best_salience,
            "focus_content": best_candidate["content"][:50] if best_candidate else None
        })

        # Maintain attention energy
        self.attention_energy *= 0.95  # Gradual decay
        if best_candidate:
            self.attention_energy = min(1.0, self.attention_energy + 0.1)  # Energy boost

        return best_candidate

    def get_attention_state(self) -> Dict[str, Any]:
        """Get current attention state."""
        return {
            "current_focus": self.current_focus["content"][:50] if self.current_focus else None,
            "attention_energy": self.attention_energy,
            "scale_history_length": len(self.scale_history),
            "last_focus_time": self.scale_history[-1]["timestamp"] if self.scale_history else None
        }


def test_fractal_attention():
    """Test the fractal attention system."""
    print("🧠 Testing Fractal Attention System")
    print("=" * 40)

    attention = FractalAttention()

    # Create test memories
    test_memories = [
        {
            "content": "Python programming language",
            "embedding": np.random.normal(0, 1, 256),
            "timestamp": datetime.now().isoformat()
        },
        {
            "content": "Machine learning algorithms",
            "embedding": np.random.normal(0, 1, 256),
            "timestamp": datetime.now().isoformat()
        }
    ]

    # Test salience calculation
    test_content = "Neural networks and AI"
    test_embedding = np.random.normal(0, 1, 256)

    salience = attention.calculate_fractal_salience(
        test_content, test_embedding, test_memories
    )

    print(f"✅ Salience calculation: {salience:.3f}")

    # Test attention focusing
    candidates = [
        {
            "content": "Deep learning models",
            "embedding": np.random.normal(0, 1, 256)
        },
        {
            "content": "Weather forecast",
            "embedding": np.random.normal(0, 1, 256)
        }
    ]

    focus = attention.focus_attention(candidates, test_memories)

    if focus:
        print(f"✅ Attention focused on: {focus['content']}")
    else:
        print("❌ No focus selected")

    # Test attention state
    state = attention.get_attention_state()
    print(f"✅ Attention energy: {state['attention_energy']:.3f}")

    print("🎯 Fractal Attention System test completed!")


if __name__ == "__main__":
    test_fractal_attention()
