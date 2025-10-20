"""
Fractal Memory Architecture for SomaBrain

This module implements nature-inspired scaling principles:
- Fractal self-similarity across cognitive scales
- Emergent intelligence from local interactions
- Hierarchical organization following natural laws
- Energy-efficient information processing

Key Principles:
1. Analogy over microscopic accuracy
2. Natural scaling laws (power laws, allometric scaling)
3. Emergent complexity from simple rules
4. Self-similar processing across scales
"""

import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
import math
import time
from collections import defaultdict

@dataclass
class FractalScale:
    """Represents a cognitive processing scale with natural scaling properties"""
    level: int
    size: float
    time_constant: float
    complexity: float
    energy_efficiency: float
    name: str

@dataclass
class FractalNode:
    """A node in the fractal memory network"""
    position: np.ndarray
    scale: FractalScale
    activity: float
    resonance: float
    connections: List['FractalNode']
    memory_trace: Any
    timestamp: float

class FractalMemorySystem:
    """
    Memory system that scales like nature using fractal principles

    Key Features:
    - Self-similar processing across scales (neural → cognitive → social)
    - Emergent intelligence from local node interactions
    - Natural scaling laws (power laws, allometric relationships)
    - Energy-efficient information processing
    - Hierarchical organization without central control
    """

    def __init__(self, base_scale: float = 0.001, max_scale: float = 100.0, fractal_dimension: float = 1.26):
        """
        Initialize fractal memory system

        Args:
            base_scale: Smallest processing scale (neural level)
            max_scale: Largest processing scale (social/system level)
            fractal_dimension: Fractal dimension (typically 1.0-2.0 for natural systems)
        """
        self.base_scale = base_scale
        self.max_scale = max_scale
        self.fractal_dimension = fractal_dimension

        # Natural scaling laws
        self.scaling_laws = {
            'time': 0.75,      # Time scales with size^0.75 (allometric scaling)
            'energy': 0.67,    # Energy scales with size^0.67
            'complexity': fractal_dimension,  # Complexity scales with fractal dimension
            'efficiency': -0.25  # Efficiency improves with scale (negative exponent)
        }

        # Initialize fractal scales
        self.scales = self._generate_fractal_scales()
        self.nodes = defaultdict(list)  # Nodes organized by scale

        # Emergence parameters
        self.emergence_threshold = 0.7
        self.resonance_strength = 0.3
        self.attunement_rate = 0.1

        print("🌀 Fractal Memory System initialized")
        print(f"   Scales: {len(self.scales)} levels ({base_scale:.3f} to {max_scale:.1f})")
        print(f"   Fractal dimension: {fractal_dimension}")
        print(f"   Natural scaling laws active: {list(self.scaling_laws.keys())}")

    def _generate_fractal_scales(self) -> List[FractalScale]:
        """Generate fractal scales following natural scaling laws"""
        scales = []
        current_scale = self.base_scale
        level = 0

        scale_names = [
            "neural", "synaptic", "ensemble", "regional",
            "cognitive", "system", "social", "cultural"
        ]

        while current_scale <= self.max_scale and level < len(scale_names):
            # Apply natural scaling laws
            time_constant = current_scale ** self.scaling_laws['time']
            complexity = current_scale ** self.scaling_laws['complexity']
            energy_efficiency = current_scale ** self.scaling_laws['efficiency']

            scale = FractalScale(
                level=level,
                size=current_scale,
                time_constant=time_constant,
                complexity=complexity,
                energy_efficiency=energy_efficiency,
                name=scale_names[level] if level < len(scale_names) else f"scale_{level}"
            )

            scales.append(scale)

            # Fractal scaling: each level is self-similar
            current_scale *= (10 ** (1 / self.fractal_dimension))
            level += 1

        return scales

    def encode_fractal(self, content: Any, importance: float = 1.0) -> List[FractalNode]:
        """
        Encode information across multiple fractal scales

        This creates a self-similar representation that captures
        the essence at different levels of abstraction
        """
        nodes = []
        base_representation = self._create_base_representation(content)

        for scale in self.scales:
            # Scale-specific processing
            scaled_representation = self._scale_representation(
                base_representation, scale
            )

            # Create fractal node
            position = self._generate_fractal_position(scale)
            node = FractalNode(
                position=position,
                scale=scale,
                activity=importance * scale.energy_efficiency,
                resonance=0.0,
                connections=[],
                memory_trace=scaled_representation,
                timestamp=time.time()
            )

            nodes.append(node)
            self.nodes[scale.level].append(node)

        # Establish fractal connections (self-similar patterns)
        self._establish_fractal_connections(nodes)

        print(f"🌀 Encoded content across {len(nodes)} fractal scales")
        return nodes

    def _create_base_representation(self, content: Any) -> np.ndarray:
        """Create base representation from content"""
        if isinstance(content, str):
            # Simple text encoding (can be enhanced with embeddings)
            return np.array([hash(word) % 1000 for word in content.split()]) / 1000.0
        elif isinstance(content, dict):
            # Dictionary encoding
            features = []
            for key, value in content.items():
                features.extend([hash(str(key)) % 100, hash(str(value)) % 100])
            return np.array(features) / 100.0
        else:
            # Generic encoding
            return np.array([hash(str(content)) % 1000]) / 1000.0

    def _scale_representation(self, base_rep: np.ndarray, scale: FractalScale) -> np.ndarray:
        """Scale representation according to natural laws"""
        # Apply fractal scaling
        scaled_size = int(len(base_rep) * (scale.size / self.base_scale) ** 0.5)

        if scaled_size <= len(base_rep):
            # Downscale: take most important features
            indices = np.argsort(np.abs(base_rep))[-scaled_size:]
            return base_rep[indices]
        else:
            # Upscale: interpolate with fractal patterns
            # Simple fractal interpolation (can be enhanced)
            scaled = np.interp(
                np.linspace(0, len(base_rep)-1, scaled_size),
                np.arange(len(base_rep)),
                base_rep
            )
            # Add fractal noise for natural variation
            fractal_noise = np.random.normal(0, 0.1 * scale.complexity, scaled_size)
            return np.clip(scaled + fractal_noise, 0, 1)

    def _generate_fractal_position(self, scale: FractalScale) -> np.ndarray:
        """Generate position using fractal (self-similar) patterns"""
        # Use fractal dimension to create self-similar positioning
        dimension = int(min(3, max(1, self.fractal_dimension)))
        position = np.random.normal(0, scale.size, dimension)

        # Add fractal clustering (nodes at similar scales cluster together)
        cluster_center = np.array([scale.level * 10] + [0] * (dimension - 1))
        position += cluster_center

        return position

    def _establish_fractal_connections(self, nodes: List[FractalNode]):
        """Establish connections following fractal patterns"""
        for i, node in enumerate(nodes):
            # Connect to nearby nodes at similar scales (fractal clustering)
            for j, other in enumerate(nodes):
                if i != j:
                    distance = np.linalg.norm(node.position - other.position)
                    scale_similarity = abs(node.scale.level - other.scale.level)

                    # Fractal connection probability
                    connection_prob = np.exp(-distance / node.scale.size) * \
                                    np.exp(-scale_similarity / 2.0)

                    if np.random.random() < connection_prob:
                        node.connections.append(other)
                        other.connections.append(node)  # Bidirectional

    def retrieve_fractal(self, query: Any, top_k: int = 5) -> List[Tuple[FractalNode, float]]:
        """
        Retrieve information using fractal resonance patterns

        This implements emergent retrieval through resonance across scales
        """
        # Create query representation
        query_rep = self._create_base_representation(query)

        # Initialize resonance patterns
        resonance_map = defaultdict(float)

        # Propagate resonance through fractal network
        for scale_level, scale_nodes in self.nodes.items():
            for node in scale_nodes:
                # Calculate resonance with query
                similarity = self._calculate_fractal_similarity(query_rep, node)

                # Propagate resonance through connections
                node_id = id(node)
                resonance_map[node_id] += similarity
                self._propagate_resonance(node, similarity, resonance_map)

        # Find most resonant nodes
        resonant_nodes = []
        for node in [n for nodes in self.nodes.values() for n in nodes]:
            node_id = id(node)
            if resonance_map[node_id] > self.emergence_threshold:
                resonant_nodes.append((node, resonance_map[node_id]))

        # Sort by resonance strength
        resonant_nodes.sort(key=lambda x: x[1], reverse=True)

        print(f"🌀 Retrieved {len(resonant_nodes)} resonant memories")
        return resonant_nodes[:top_k]

    def _calculate_fractal_similarity(self, query_rep: np.ndarray, node: FractalNode) -> float:
        """Calculate similarity using fractal scaling principles"""
        # Scale query to node's scale
        scaled_query = self._scale_representation(query_rep, node.scale)

        # Cosine similarity with scale weighting
        if len(scaled_query) == 0 or len(node.memory_trace) == 0:
            return 0.0

        # Ensure same length for comparison
        min_len = min(len(scaled_query), len(node.memory_trace))
        similarity = np.dot(scaled_query[:min_len], node.memory_trace[:min_len])

        # Weight by scale efficiency (higher scales = more important)
        scale_weight = node.scale.energy_efficiency

        return similarity * scale_weight

    def _propagate_resonance(self, node: FractalNode, initial_resonance: float,
                           resonance_map: Dict[int, float], depth: int = 3):
        """Propagate resonance through fractal connections"""
        if depth <= 0:
            return

        # Attenuate resonance with distance and time
        attenuated_resonance = initial_resonance * self.resonance_strength

        for connected_node in node.connections:
            # Add resonance with temporal decay
            time_decay = np.exp(-(time.time() - connected_node.timestamp) / 3600)  # 1 hour half-life
            connected_id = id(connected_node)
            resonance_map[connected_id] += attenuated_resonance * time_decay

            # Recursive propagation with reduced depth
            self._propagate_resonance(connected_node, attenuated_resonance,
                                    resonance_map, depth - 1)

    def consolidate_fractal(self):
        """Consolidate memories using fractal emergence principles"""
        print("🌀 Running fractal memory consolidation...")

        # Emergence through resonance
        for scale_level in sorted(self.nodes.keys()):
            scale_nodes = self.nodes[scale_level]

            # Find emergent patterns
            emergent_patterns = self._find_emergent_patterns(scale_nodes)

            # Strengthen connections that participate in emergence
            for pattern in emergent_patterns:
                self._strengthen_fractal_connections(pattern)

        print("   Fractal consolidation complete")

    def _find_emergent_patterns(self, nodes: List[FractalNode]) -> List[List[FractalNode]]:
        """Find emergent patterns in fractal node activations"""
        patterns = []

        # Simple emergence detection: highly connected, highly active clusters
        for node in nodes:
            if node.activity > self.emergence_threshold:
                # Find connected component
                cluster = self._find_connected_component(node)
                if len(cluster) >= 3:  # Minimum cluster size for emergence
                    patterns.append(cluster)

        return patterns

    def _find_connected_component(self, start_node: FractalNode) -> List[FractalNode]:
        """Find connected component using breadth-first search"""
        visited = set()
        queue = [start_node]
        component = []

        while queue:
            node = queue.pop(0)
            # Use node position as hashable identifier
            node_id = tuple(node.position.flatten())
            if node_id not in visited:
                visited.add(node_id)
                component.append(node)
                queue.extend([n for n in node.connections if tuple(n.position.flatten()) not in visited])

        return component

    def _strengthen_fractal_connections(self, pattern: List[FractalNode]):
        """Strengthen connections within emergent patterns"""
        for node in pattern:
            # Increase activity (Hebbian-like learning)
            node.activity = min(1.0, node.activity + self.attunement_rate)

            # Strengthen connections to other pattern members
            for other in pattern:
                if other != node and other not in node.connections:
                    node.connections.append(other)
                    other.connections.append(node)

    def get_fractal_statistics(self) -> Dict[str, Any]:
        """Get comprehensive fractal system statistics"""
        total_nodes = sum(len(nodes) for nodes in self.nodes.values())
        total_connections = sum(len(node.connections) for nodes in self.nodes.values() for node in nodes) // 2

        # Calculate emergence metrics
        emergence_count = 0
        for nodes in self.nodes.values():
            emergence_count += len(self._find_emergent_patterns(nodes))

        return {
            'total_nodes': total_nodes,
            'total_connections': total_connections,
            'scales': len(self.scales),
            'emergent_patterns': emergence_count,
            'average_connectivity': total_connections / max(1, total_nodes),
            'fractal_dimension': self.fractal_dimension,
            'scaling_laws': self.scaling_laws
        }

if __name__ == "__main__":
    # Demonstration
    print("🌿 Fractal Memory Architecture Demonstration")
    print("=" * 50)

    # Initialize system
    fractal_brain = FractalMemorySystem()

    # Test data
    test_memories = [
        {
            'concept': 'neural_synchronization',
            'content': 'Neural populations synchronize to bind features into coherent percepts',
            'importance': 0.9
        },
        {
            'concept': 'emergent_intelligence',
            'content': 'Complex cognition emerges from simple local interactions',
            'importance': 0.85
        },
        {
            'concept': 'fractal_scaling',
            'content': 'Natural systems scale using fractal self-similarity',
            'importance': 0.8
        }
    ]

    print("\n1. Encoding memories across fractal scales...")
    for memory in test_memories:
        nodes = fractal_brain.encode_fractal(memory, memory['importance'])
        print(f"   ✓ {memory['concept']}: {len(nodes)} fractal nodes created")

    print("\n2. Testing fractal retrieval...")
    query = {'concept': 'neural_patterns', 'content': 'Coordinated neural activity patterns'}
    results = fractal_brain.retrieve_fractal(query, top_k=3)
    print(f"   Found {len(results)} resonant memories")

    print("\n3. Running fractal consolidation...")
    fractal_brain.consolidate_fractal()

    print("\n4. System statistics:")
    stats = fractal_brain.get_fractal_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")

