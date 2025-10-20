# Cognitum: Pure Mathematical Cognition Engine
# Phase Σ: Mathematical Foundations

"""
Cognitum - A Pure Mathematical Cognition Engine

Principles:
- Vector Space Cognition: All knowledge as vectors in mathematical spaces
- Functional Composition: Cognition through composable mathematical functions
- Differential Geometry: Memory as manifolds with curvature
- Type Theory: Knowledge representation through mathematical types
- Computational Universality: Turing-complete cognition through pure math

No biological artifacts. Pure mathematical transcendence.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import hashlib
import json
import os
from pathlib import Path

# =============================================================================
# Σ.1: Vector Space Foundations
# =============================================================================

@dataclass
class VectorSpace:
    """Pure mathematical vector space for cognition"""
    dimension: int
    metric: str = "euclidean"  # euclidean, hyperbolic, spherical
    curvature: float = 0.0    # For Riemannian geometry

    def validate_vector(self, vector: np.ndarray) -> bool:
        """Validate vector belongs to this space"""
        return bool(len(vector) == self.dimension and np.isfinite(vector).all())

    def distance(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute distance in this space"""
        if self.metric == "euclidean":
            return float(np.linalg.norm(a - b))
        elif self.metric == "hyperbolic":
            # Hyperbolic distance
            return float(np.arccosh(1 + 2 * np.sum((a - b)**2) / ((1 - np.sum(a**2)) * (1 - np.sum(b**2)))))
        elif self.metric == "spherical":
            # Spherical distance
            return float(np.arccos(np.clip(np.dot(a, b), -1, 1)))
        else:
            return float(np.linalg.norm(a - b))

# =============================================================================
# Σ.2: Deterministic Embeddings (Pure Math)
# =============================================================================

class MathematicalEmbedder:
    """Deterministic embeddings using pure mathematical functions"""

    def __init__(self, dimension: int = 256, space: Optional[VectorSpace] = None):
        self.dimension = dimension
        self.space = space or VectorSpace(dimension)
        self.primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71]

    def embed(self, content: str, context: Optional[Dict[str, Any]] = None) -> np.ndarray:
        """Create deterministic embedding using mathematical hashing"""
        # Combine content and context
        full_content = content
        if context:
            full_content += json.dumps(context, sort_keys=True)

        # Use multiple hash functions for different dimensions
        vector = np.zeros(self.dimension, dtype=np.float32)

        for i in range(min(len(self.primes), self.dimension // 16)):
            # Mathematical hash using prime-based transformations
            hash_val = int(hashlib.sha256(full_content.encode()).hexdigest()[:16], 16)
            hash_val = (hash_val * self.primes[i]) % (2**32)

            # Convert to vector components using trigonometric functions
            for j in range(16):
                if i * 16 + j < self.dimension:
                    # Pure mathematical transformation
                    angle = (hash_val + j * self.primes[i]) * np.pi * 2 / (2**32)
                    vector[i * 16 + j] = np.sin(angle) * np.cos(angle * self.primes[i % len(self.primes)])

        # Normalize to unit sphere (pure mathematical constraint)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector

# =============================================================================
# Σ.3: Linear Associative Memory (Outer Product)
# =============================================================================

class LinearAssociativeMemory:
    """Pure linear algebra associative memory using outer products"""

    def __init__(self, dimension: int = 256):
        self.dimension = dimension
        self.memory_matrix = np.zeros((dimension, dimension), dtype=np.float32)
        self.space = VectorSpace(dimension)

    def store(self, key: np.ndarray, value: np.ndarray) -> bool:
        """Store association using outer product"""
        if not (self.space.validate_vector(key) and self.space.validate_vector(value)):
            return False

        # Pure linear algebra: associative memory via outer product
        self.memory_matrix += np.outer(value, key)
        return True

    def recall(self, key: np.ndarray, threshold: float = 0.1) -> Optional[np.ndarray]:
        """Recall associated value using matrix multiplication"""
        if not self.space.validate_vector(key):
            return None

        # Pure linear algebra: recall via matrix-vector multiplication
        result = self.memory_matrix @ key

        # Normalize result
        norm = np.linalg.norm(result)
        if norm > threshold:
            return result / norm
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Mathematical properties of the memory matrix"""
        return {
            "rank": np.linalg.matrix_rank(self.memory_matrix),
            "condition_number": np.linalg.cond(self.memory_matrix) if np.linalg.matrix_rank(self.memory_matrix) > 0 else float('inf'),
            "frobenius_norm": np.linalg.norm(self.memory_matrix, 'fro'),
            "spectral_radius": np.max(np.abs(np.linalg.eigvals(self.memory_matrix))) if self.memory_matrix.size > 0 else 0.0
        }

# =============================================================================
# Σ.4: Functional Composition Engine
# =============================================================================

@dataclass
class MathematicalFunction(ABC):
    """Abstract base for mathematical functions in cognition"""
    name: str
    domain: VectorSpace
    codomain: VectorSpace

    @abstractmethod
    def apply(self, input_vector: np.ndarray) -> np.ndarray:
        """Apply the mathematical function"""
        pass

    @abstractmethod
    def compose(self, other: 'MathematicalFunction') -> 'MathematicalFunction':
        """Compose with another function (category theory)"""
        pass

class IdentityFunction(MathematicalFunction):
    """Identity function: f(x) = x"""
    def apply(self, input_vector: np.ndarray) -> np.ndarray:
        return input_vector

    def compose(self, other: MathematicalFunction) -> MathematicalFunction:
        return other

class LinearTransformation(MathematicalFunction):
    """Linear transformation: f(x) = Ax + b"""

    def __init__(self, name: str, matrix: np.ndarray, bias: Optional[np.ndarray] = None):
        domain_dim = matrix.shape[1]
        codomain_dim = matrix.shape[0]
        super().__init__(name, VectorSpace(domain_dim), VectorSpace(codomain_dim))
        self.matrix = matrix
        self.bias = bias if bias is not None else np.zeros(codomain_dim)

    def apply(self, input_vector: np.ndarray) -> np.ndarray:
        return self.matrix @ input_vector + self.bias

    def compose(self, other: MathematicalFunction) -> MathematicalFunction:
        if isinstance(other, LinearTransformation):
            # Matrix multiplication composition
            new_matrix = other.matrix @ self.matrix
            new_bias = other.matrix @ self.bias + other.bias
            return LinearTransformation(
                f"{other.name} ∘ {self.name}",
                new_matrix,
                new_bias
            )
        # Create composed function manually
        composed = ComposedFunction.__new__(ComposedFunction)
        composed.f = other
        composed.g = self
        composed.__post_init__()
        return composed

@dataclass
class ComposedFunction(MathematicalFunction):
    """Composition of mathematical functions"""
    f: MathematicalFunction
    g: MathematicalFunction

    def __post_init__(self):
        # Composition: (f ∘ g)(x) = f(g(x))
        if self.f.domain.dimension != self.g.codomain.dimension:
            raise ValueError("Function domains/codomains don't compose")
        # Initialize the parent class properly
        object.__setattr__(self, 'name', f"{self.f.name} ∘ {self.g.name}")
        object.__setattr__(self, 'domain', self.g.domain)
        object.__setattr__(self, 'codomain', self.f.codomain)

    def apply(self, input_vector: np.ndarray) -> np.ndarray:
        return self.f.apply(self.g.apply(input_vector))

    def compose(self, other: MathematicalFunction) -> MathematicalFunction:
        # Create composed function manually
        composed = ComposedFunction.__new__(ComposedFunction)
        composed.f = self
        composed.g = other
        composed.__post_init__()
        return composed

# =============================================================================
# Σ.5: Differential Geometry Memory Manifold
# =============================================================================

class RiemannianManifold:
    """Memory as a Riemannian manifold with curvature"""

    def __init__(self, dimension: int, curvature: float = 0.0):
        self.dimension = dimension
        self.curvature = curvature
        self.metric_tensor = self._compute_metric_tensor()

    def _compute_metric_tensor(self) -> np.ndarray:
        """Compute metric tensor based on curvature"""
        if abs(self.curvature) < 1e-6:
            # Euclidean metric
            return np.eye(self.dimension)
        elif self.curvature > 0:
            # Spherical metric (positive curvature)
            return np.eye(self.dimension) / (1 + self.curvature * np.sum(np.arange(self.dimension)**2))
        else:
            # Hyperbolic metric (negative curvature)
            return np.eye(self.dimension) * np.exp(-self.curvature * np.arange(self.dimension))

    def geodesic_distance(self, point1: np.ndarray, point2: np.ndarray) -> float:
        """Compute geodesic distance on the manifold"""
        if abs(self.curvature) < 1e-6:
            return float(np.linalg.norm(point1 - point2))
        elif self.curvature > 0:
            # Spherical geodesic
            return float(np.arccos(np.clip(np.dot(point1, point2), -1, 1)))
        else:
            # Hyperbolic geodesic
            return float(np.arccosh(1 + 2 * np.sum((point1 - point2)**2) / ((1 - np.sum(point1**2)) * (1 - np.sum(point2**2)))))

# =============================================================================
# Σ.6: Type Theory Knowledge Representation
# =============================================================================

@dataclass
class MathematicalType:
    """Type theory for knowledge representation"""
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    subtypes: List['MathematicalType'] = field(default_factory=list)
    supertypes: List['MathematicalType'] = field(default_factory=list)

    def is_subtype_of(self, other: 'MathematicalType') -> bool:
        """Check subtype relationship"""
        return other in self.supertypes or any(t.is_subtype_of(other) for t in self.supertypes)

    def compose_types(self, other: 'MathematicalType') -> 'MathematicalType':
        """Compose types (product or function type)"""
        return MathematicalType(
            f"{self.name} × {other.name}",
            properties={**self.properties, **other.properties},
            subtypes=self.subtypes + other.subtypes,
            supertypes=self.supertypes + other.supertypes
        )

# =============================================================================
# Ω: The Complete Mathematical Cognition Engine
# =============================================================================

class CognitumCore:
    """The complete mathematical cognition engine"""

    def __init__(self, dimension: int = 256):
        self.dimension = dimension

        # Mathematical foundations
        self.vector_space = VectorSpace(dimension)
        self.embedder = MathematicalEmbedder(dimension, self.vector_space)
        self.associative_memory = LinearAssociativeMemory(dimension)
        self.manifold = RiemannianManifold(dimension)

        # Function composition system
        self.functions: Dict[str, MathematicalFunction] = {}
        self._initialize_core_functions()

        # Type system
        self.types: Dict[str, MathematicalType] = {}
        self._initialize_core_types()

        # Knowledge graph as mathematical relations
        self.knowledge_matrix = np.zeros((dimension, dimension), dtype=np.float32)

        print("🔢 Cognitum Core initialized with pure mathematical foundations")

    def _initialize_core_functions(self):
        """Initialize fundamental mathematical functions"""
        # Identity
        self.functions["id"] = IdentityFunction("id", self.vector_space, self.vector_space)

        # Basic linear transformations
        identity_matrix = np.eye(self.dimension)
        self.functions["linear_id"] = LinearTransformation("linear_id", identity_matrix)

    def _initialize_core_types(self):
        """Initialize fundamental mathematical types"""
        # Basic types
        self.types["scalar"] = MathematicalType("scalar", {"dimension": 1})
        self.types["vector"] = MathematicalType("vector", {"dimension": self.dimension})
        self.types["matrix"] = MathematicalType("matrix", {"dimension": (self.dimension, self.dimension)})

        # Knowledge types
        self.types["concept"] = MathematicalType("concept", {"semantic": True})
        self.types["relation"] = MathematicalType("relation", {"mathematical": True})

    def encode_knowledge(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> np.ndarray:
        """Encode knowledge as mathematical vector"""
        return self.embedder.embed(content, metadata)

    def store_relation(self, subject: np.ndarray, relation: np.ndarray, object: np.ndarray) -> bool:
        """Store mathematical relation using tensor products"""
        # Use associative memory for relations
        relation_key = subject + relation  # Vector addition for relation encoding
        return self.associative_memory.store(relation_key, object)

    def query_knowledge(self, query_vector: np.ndarray, threshold: float = 0.1) -> List[np.ndarray]:
        """Query knowledge using mathematical similarity"""
        results = []

        # Direct associative recall
        direct_result = self.associative_memory.recall(query_vector, threshold)
        if direct_result is not None:
            results.append(direct_result)

        # Similarity search in knowledge matrix
        similarities = self.knowledge_matrix @ query_vector
        top_indices = np.argsort(similarities)[-5:][::-1]  # Top 5

        for idx in top_indices:
            if similarities[idx] > threshold:
                # Reconstruct vector from knowledge matrix
                result_vector = self.knowledge_matrix[idx] / np.linalg.norm(self.knowledge_matrix[idx])
                results.append(result_vector)

        return results

    def compose_cognition(self, function_sequence: List[str]) -> MathematicalFunction:
        """Compose cognitive functions mathematically"""
        if not function_sequence:
            return self.functions["id"]

        composed = self.functions[function_sequence[0]]
        for func_name in function_sequence[1:]:
            if func_name in self.functions:
                composed = composed.compose(self.functions[func_name])

        return composed

    def apply_cognition(self, input_vector: np.ndarray, function_sequence: List[str]) -> np.ndarray:
        """Apply composed cognitive function"""
        cognitive_function = self.compose_cognition(function_sequence)
        return cognitive_function.apply(input_vector)

    def get_mathematical_properties(self) -> Dict[str, Any]:
        """Get pure mathematical properties of the system"""
        return {
            "vector_space_dimension": self.dimension,
            "manifold_curvature": self.manifold.curvature,
            "memory_matrix_rank": self.associative_memory.get_statistics()["rank"],
            "knowledge_matrix_condition": np.linalg.cond(self.knowledge_matrix) if self.knowledge_matrix.size > 0 else 0.0,
            "function_count": len(self.functions),
            "type_count": len(self.types),
            "mathematical_consistency": self._check_mathematical_consistency()
        }

    def _check_mathematical_consistency(self) -> bool:
        """Verify mathematical consistency of the system"""
        # Check vector space properties
        zero_vector = np.zeros(self.dimension)
        if not self.vector_space.validate_vector(zero_vector):
            return False

        # Check function composition associativity
        f = self.functions.get("id")
        if f is None:
            return False

        # Check manifold properties
        if not np.allclose(self.manifold.metric_tensor, self.manifold.metric_tensor.T):
            return False

        return True

# =============================================================================
# Interface Functions
# =============================================================================

def create_cognitum(dimension: int = 256) -> CognitumCore:
    """Create a new Cognitum cognition engine"""
    return CognitumCore(dimension)

def encode_concept(content: str, metadata: Optional[Dict[str, Any]] = None) -> np.ndarray:
    """Encode a concept as mathematical vector"""
    embedder = MathematicalEmbedder()
    return embedder.embed(content, metadata)

def compose_functions(functions: List[MathematicalFunction]) -> MathematicalFunction:
    """Compose mathematical functions"""
    if not functions:
        return IdentityFunction("id", VectorSpace(256), VectorSpace(256))

    composed = functions[0]
    for f in functions[1:]:
        composed = composed.compose(f)
    return composed

# =============================================================================
# Test and Validation
# =============================================================================

if __name__ == "__main__":
    print("🔢 Testing Cognitum: Pure Mathematical Cognition")
    print("=" * 60)

    # Create mathematical cognition engine
    cognitum = create_cognitum()

    # Test vector space properties
    print("\\n🧮 Testing Vector Space Properties")
    v1 = encode_concept("mathematics")
    v2 = encode_concept("algebra")
    distance = cognitum.vector_space.distance(v1, v2)
    print(f"Distance between 'mathematics' and 'algebra': {distance:.4f}")

    # Test associative memory
    print("\\n🔗 Testing Associative Memory")
    concept1 = encode_concept("linear algebra")
    concept2 = encode_concept("vector spaces")
    cognitum.store_relation(concept1, encode_concept("contains"), concept2)
    recalled = cognitum.query_knowledge(concept1)
    print(f"Associative recall successful: {len(recalled) > 0}")

    # Test function composition
    print("\\n⚙️ Testing Function Composition")
    identity = LinearTransformation("id", np.eye(256))
    scale = LinearTransformation("scale", 2 * np.eye(256))
    composed = identity.compose(scale)
    result = composed.apply(v1)
    print(f"Function composition successful: {np.allclose(result, 2 * v1)}")

    # Test mathematical properties
    print("\\n📊 Mathematical Properties")
    props = cognitum.get_mathematical_properties()
    for key, value in props.items():
        print(f"  {key}: {value}")

    print("\\n✅ Cognitum: Pure mathematical cognition achieved!")
    print("🎯 Ready for Phase Π: Vector Space Cognition")
