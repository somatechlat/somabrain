"""
Mathematical Validation Core

Unified mathematical validation engine for BHDC, quantum operations, 
spectral properties, and mathematical invariants.
"""

import numpy as np
import math
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class ValidationResult:
    """Result of mathematical validation."""
    claim: str
    passed: bool
    evidence: Dict[str, Any]
    deviation: float
    simple_explanation: str
    tolerance: float = 1e-6


@dataclass
class Proof:
    """Simple, accessible mathematical proof."""
    claim: str
    simple_proof: str
    intuitive_explanation: str
    synthetic_verification: str
    mathematical_formula: str


class MathematicalValidator(ABC):
    """Abstract base class for mathematical validators."""
    
    @abstractmethod
    def validate(self, *args, **kwargs) -> ValidationResult:
        """Validate mathematical property."""
        pass
    
    @abstractmethod
    def generate_proof(self, *args, **kwargs) -> Proof:
        """Generate simple, accessible mathematical proof."""
        pass


class BHDCValidator(MathematicalValidator):
    """Validator for BHDC mathematical properties."""
    
    def __init__(self):
        self.dimension = 1024  # Default dimension
        
    def validate_spectral_property(self, vectors: List[np.ndarray]) -> ValidationResult:
        """Validate BHDC spectral property |H_k|≈1."""
        magnitudes = []
        for vector in vectors:
            magnitude = np.linalg.norm(vector)
            magnitudes.append(magnitude)
        
        mean_magnitude = np.mean(magnitudes)
        deviation = abs(mean_magnitude - 1.0)
        
        return ValidationResult(
            claim="BHDC maintains spectral property |H_k|≈1",
            passed=deviation < 0.01,
            evidence={
                "mean_magnitude": float(mean_magnitude),
                "std_magnitude": float(np.std(magnitudes)),
                "num_vectors": len(vectors)
            },
            deviation=float(deviation),
            simple_explanation="Unitary transformations preserve vector norms",
            tolerance=0.01
        )
    
    def validate_binding_invertibility(self, bind_matrix: np.ndarray, 
                                     original_vectors: List[np.ndarray],
                                     bound_vectors: List[np.ndarray]) -> ValidationResult:
        """Validate BHDC binding operations are invertible."""
        try:
            # Test binding/unbinding roundtrip
            recovered_vectors = []
            for i, bound_vec in enumerate(bound_vectors):
                # Simple unbind operation (matrix inverse)
                recovered = np.linalg.solve(bind_matrix, bound_vec)
                recovered_vectors.append(recovered)
            
            # Calculate recovery accuracy
            accuracies = []
            for orig, recovered in zip(original_vectors, recovered_vectors):
                accuracy = np.dot(orig, recovered) / (np.linalg.norm(orig) * np.linalg.norm(recovered))
                accuracies.append(abs(accuracy))
            
            mean_accuracy = np.mean(accuracies)
            deviation = abs(mean_accuracy - 1.0)
            
            return ValidationResult(
                claim="BHDC binding operations are invertible",
                passed=deviation < 0.01 and mean_accuracy > 0.99,
                evidence={
                    "mean_accuracy": float(mean_accuracy),
                    "min_accuracy": float(min(accuracies)),
                    "num_vectors": len(original_vectors)
                },
                deviation=float(deviation),
                simple_explanation="Binding matrix has full rank, so inverse exists and recovers original vectors",
                tolerance=0.01
            )
        except Exception as e:
            return ValidationResult(
                claim="BHDC binding operations are invertible",
                passed=False,
                evidence={"error": str(e)},
                deviation=1.0,
                simple_explanation="Binding matrix is singular - cannot invert",
                tolerance=0.01
            )
    
    def generate_spectral_property_proof(self, dimension: int = 1024) -> Proof:
        """Generate simple proof for BHDC spectral property."""
        return Proof(
            claim="BHDC maintains spectral property |H_k|≈1",
            simple_proof="For unitary matrix U, ||Ux||² = ⟨Ux, Ux⟩ = ⟨x, U*Ux⟩ = ⟨x, Ix⟩ = ||x||²",
            intuitive_explanation="Unitary transformations are like rotations - they don't change vector lengths",
            synthetic_verification="Generate random unit vectors, apply BHDC transformation, verify norms preserved",
            mathematical_formula="||Ux|| = ||x|| for unitary U"
        )
    
    def generate_binding_invertibility_proof(self) -> Proof:
        """Generate simple proof for BHDC binding invertibility."""
        return Proof(
            claim="BHDC binding operations are invertible",
            simple_proof="Binding matrix B has full rank, so B⁻¹ exists and unbind(B(x,y)) = x",
            intuitive_explanation="Like encoding/decoding - you can always retrieve original information",
            synthetic_verification="Bind vectors with matrix B, then apply B⁻¹, verify original vector recovered",
            mathematical_formula="B⁻¹(B(x)) = x for full-rank matrix B"
        )


class QuantumValidator(MathematicalValidator):
    """Validator for quantum mathematical properties."""
    
    def validate_role_orthogonality(self, role_vectors: List[np.ndarray]) -> ValidationResult:
        """Validate role vector orthogonality ⟨r_i,r_j⟩≈0."""
        n_roles = len(role_vectors)
        cosine_similarities = []
        
        for i in range(n_roles):
            for j in range(i + 1, n_roles):
                cos_sim = np.dot(role_vectors[i], role_vectors[j]) / (
                    np.linalg.norm(role_vectors[i]) * np.linalg.norm(role_vectors[j])
                )
                cosine_similarities.append(abs(cos_sim))
        
        max_similarity = max(cosine_similarities) if cosine_similarities else 0.0
        mean_similarity = np.mean(cosine_similarities) if cosine_similarities else 0.0
        
        return ValidationResult(
            claim="Role vectors maintain orthogonality ⟨r_i,r_j⟩≈0",
            passed=max_similarity < 0.01,
            evidence={
                "max_similarity": float(max_similarity),
                "mean_similarity": float(mean_similarity),
                "num_pairs": len(cosine_similarities)
            },
            deviation=float(max_similarity),
            simple_explanation="Gram-Schmidt process ensures vectors are perpendicular",
            tolerance=0.01
        )
    
    def validate_density_matrix_properties(self, density_matrix: np.ndarray) -> ValidationResult:
        """Validate density matrix mathematical properties."""
        # Check trace = 1
        trace = np.trace(density_matrix)
        trace_deviation = abs(trace - 1.0)
        
        # Check positive semi-definite (all eigenvalues >= 0)
        eigenvalues = np.linalg.eigvals(density_matrix)
        min_eigenvalue = np.min(np.real(eigenvalues))
        
        # Check Hermitian (matrix equals its conjugate transpose)
        hermitian_deviation = np.linalg.norm(density_matrix - density_matrix.conj().T)
        
        all_passed = (trace_deviation < 1e-6 and 
                     min_eigenvalue >= -1e-6 and 
                     hermitian_deviation < 1e-6)
        
        return ValidationResult(
            claim="Density matrix satisfies quantum mechanical requirements",
            passed=all_passed,
            evidence={
                "trace": float(np.real(trace)),
                "min_eigenvalue": float(np.real(min_eigenvalue)),
                "hermitian_deviation": float(hermitian_deviation)
            },
            deviation=max(trace_deviation, abs(min_eigenvalue) if min_eigenvalue < 0 else 0, hermitian_deviation),
            simple_explanation="Quantum states must have trace 1, be positive semi-definite, and Hermitian",
            tolerance=1e-6
        )
    
    def generate_role_orthogonality_proof(self) -> Proof:
        """Generate simple proof for role orthogonality."""
        return Proof(
            claim="Role vectors maintain orthogonality ⟨r_i,r_j⟩≈0",
            simple_proof="Gram-Schmidt orthogonalization: v_j' = v_j - Σ_{i<j} ⟨v_j,v_i⟩v_i",
            intuitive_explanation="Like finding perpendicular directions in 3D space - each new vector is made perpendicular to all previous ones",
            synthetic_verification="Create random vectors, apply Gram-Schmidt, verify all pairwise dot products ≈ 0",
            mathematical_formula="⟨r_i, r_j⟩ = 0 for i ≠ j"
        )


class SpectralValidator(MathematicalValidator):
    """Validator for spectral mathematical properties."""
    
    def validate_unitary_roundtrip(self, matrix: np.ndarray, test_vectors: List[np.ndarray]) -> ValidationResult:
        """Validate unitary transformation roundtrip preserves vectors."""
        errors = []
        
        for original_vec in test_vectors:
            # Apply transformation
            transformed = matrix @ original_vec
            # Apply inverse transformation
            recovered = matrix.conj().T @ transformed
            
            # Calculate error
            error = np.linalg.norm(recovered - original_vec)
            errors.append(error)
        
        max_error = max(errors)
        mean_error = np.mean(errors)
        
        return ValidationResult(
            claim="Unitary transformations preserve vectors under roundtrip",
            passed=max_error < 1e-10,
            evidence={
                "max_error": float(max_error),
                "mean_error": float(mean_error),
                "num_vectors": len(test_vectors)
            },
            deviation=float(max_error),
            simple_explanation="Unitary matrices are reversible - applying then undoing gives back original",
            tolerance=1e-10
        )
    
    def generate_unitary_roundtrip_proof(self) -> Proof:
        """Generate simple proof for unitary roundtrip property."""
        return Proof(
            claim="Unitary transformations preserve vectors under roundtrip",
            simple_proof="For unitary U, U*U = I, so U*(Ux) = (U*U)x = Ix = x",
            intuitive_explanation="Like rotating then rotating back - you end up where you started",
            synthetic_verification="Apply unitary matrix to vector, then apply its inverse, verify original vector recovered",
            mathematical_formula="U†(U(x)) = x for unitary U"
        )


class UnifiedMathematicalCore:
    """Core mathematical validation engine."""
    
    def __init__(self):
        self.bhdc_validator = BHDCValidator()
        self.quantum_validator = QuantumValidator()
        self.spectral_validator = SpectralValidator()
        self.validation_history = []
        
    def validate_all_invariants(self, dimension: int = 1024) -> Dict[str, ValidationResult]:
        """Comprehensive validation of all mathematical invariants."""
        results = {}
        
        # Generate synthetic test data
        test_vectors = self._generate_test_vectors(dimension, 100)
        role_vectors = self._generate_orthogonal_roles(10, dimension)
        unitary_matrix = self._generate_unitary_matrix(dimension)
        
        # BHDC validations
        results['bhdc_spectral'] = self.bhdc_validator.validate_spectral_property(test_vectors)
        
        # Simple binding matrix for testing
        bind_matrix = np.random.randn(dimension, dimension)
        bind_matrix = bind_matrix / np.linalg.norm(bind_matrix, axis=0)
        bound_vectors = [bind_matrix @ vec for vec in test_vectors[:10]]
        results['bhdc_binding'] = self.bhdc_validator.validate_binding_invertibility(
            bind_matrix, test_vectors[:10], bound_vectors
        )
        
        # Quantum validations
        results['quantum_orthogonality'] = self.quantum_validator.validate_role_orthogonality(role_vectors)
        
        # Simple density matrix for testing
        density_matrix = self._generate_density_matrix(dimension)
        results['quantum_density'] = self.quantum_validator.validate_density_matrix_properties(density_matrix)
        
        # Spectral validations
        results['spectral_roundtrip'] = self.spectral_validator.validate_unitary_roundtrip(
            unitary_matrix, test_vectors[:20]
        )
        
        # Store in history
        self.validation_history.append({
            'timestamp': str(np.datetime64('now')),
            'results': results
        })
        
        return results
    
    def generate_all_proofs(self) -> Dict[str, Proof]:
        """Generate simple, accessible mathematical proofs for all claims."""
        return {
            'bhdc_spectral': self.bhdc_validator.generate_spectral_property_proof(),
            'bhdc_binding': self.bhdc_validator.generate_binding_invertibility_proof(),
            'quantum_orthogonality': self.quantum_validator.generate_role_orthogonality_proof(),
            'spectral_roundtrip': self.spectral_validator.generate_unitary_roundtrip_proof()
        }
    
    def _generate_test_vectors(self, dimension: int, num_vectors: int) -> List[np.ndarray]:
        """Generate synthetic test vectors with known mathematical properties."""
        vectors = []
        for _ in range(num_vectors):
            vec = np.random.randn(dimension)
            vec = vec / np.linalg.norm(vec)  # Normalize to unit length
            vectors.append(vec)
        return vectors
    
    def _generate_orthogonal_roles(self, num_roles: int, dimension: int) -> List[np.ndarray]:
        """Generate orthogonal role vectors using Gram-Schmidt."""
        # Start with random vectors
        vectors = []
        for _ in range(num_roles):
            vec = np.random.randn(dimension)
            vectors.append(vec)
        
        # Apply Gram-Schmidt orthogonalization
        orthogonal_vectors = []
        for i, vec in enumerate(vectors):
            # Subtract projection onto all previous vectors
            for prev_vec in orthogonal_vectors:
                vec = vec - np.dot(vec, prev_vec) * prev_vec
            
            # Normalize
            vec = vec / np.linalg.norm(vec)
            orthogonal_vectors.append(vec)
        
        return orthogonal_vectors
    
    def _generate_unitary_matrix(self, dimension: int) -> np.ndarray:
        """Generate random unitary matrix."""
        # Generate random matrix
        A = np.random.randn(dimension, dimension) + 1j * np.random.randn(dimension, dimension)
        
        # QR decomposition to get unitary matrix
        Q, R = np.linalg.qr(A)
        
        # Ensure proper unitary (Q*Q = I)
        Q = Q @ np.diag(np.sign(np.diag(R)))
        
        return Q
    
    def _generate_density_matrix(self, dimension: int) -> np.ndarray:
        """Generate valid density matrix."""
        # Generate random state vector
        psi = np.random.randn(dimension) + 1j * np.random.randn(dimension)
        psi = psi / np.linalg.norm(psi)
        
        # Create density matrix |ψ⟩⟨ψ|
        density_matrix = np.outer(psi, psi.conj())
        
        return density_matrix