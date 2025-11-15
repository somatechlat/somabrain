"""
Synthetic Data Generation for Mathematical Benchmarking

Generate mathematically precise synthetic data for benchmarking and validation.
All synthetic data has known mathematical properties for simple, accessible proofs.
"""

import numpy as np
import math
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
import json
from datetime import datetime


@dataclass
class KnowledgeGraph:
    """Synthetic knowledge graph with mathematical properties."""
    entities: List[str]
    relations: List[str]
    triples: List[Tuple[str, str, str]]
    
    def get_mathematical_properties(self) -> Dict[str, Any]:
        """Get mathematical properties of the knowledge graph."""
        return {
            "num_entities": len(self.entities),
            "num_relations": len(self.relations),
            "num_triples": len(self.triples),
            "sparsity": len(self.triples) / (len(self.entities) * len(self.relations)),
            "avg_relations_per_entity": len(self.triples) / len(self.entities) if self.entities else 0
        }


@dataclass
class SyntheticDataset:
    """Container for synthetic dataset with provenance."""
    name: str
    data: Any
    properties: Dict[str, Any]
    generation_timestamp: str
    mathematical_guarantees: List[str]


class SyntheticDataGenerator:
    """Generate mathematically precise synthetic data."""
    
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            np.random.seed(seed)
        self.seed = seed
        
    def create_knowledge_graph(self, num_entities: int = 50, num_relations: int = 10) -> KnowledgeGraph:
        """Create synthetic knowledge graph with mathematical properties."""
        entities = [f"entity_{i}" for i in range(num_entities)]
        relations = [f"relation_{j}" for j in range(num_relations)]
        
        # Create mathematically precise relationships
        triples = []
        for i in range(num_entities):
            for j in range(num_relations):
                # Mathematical relationship with known properties
                # Use π-based values for mathematical precision
                value = round(math.pi * (i + j) / num_entities, 6)
                triples.append((entities[i], relations[j], str(value)))
        
        return KnowledgeGraph(entities, relations, triples)
    
    def create_bhdc_test_vectors(self, dimension: int = 1024, num_vectors: int = 100) -> List[np.ndarray]:
        """Create synthetic BHDC vectors with known mathematical properties."""
        vectors = []
        for i in range(num_vectors):
            # Unit vector with controlled mathematical properties
            vector = np.random.randn(dimension)
            vector = vector / np.linalg.norm(vector)  # Normalize to unit length
            vectors.append(vector)
        
        return vectors
    
    def create_orthogonal_roles(self, num_roles: int = 10, dimension: int = 1024) -> List[np.ndarray]:
        """Create synthetic orthogonal role vectors."""
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
    
    def create_quantum_states(self, num_qubits: int = 4) -> List[np.ndarray]:
        """Create synthetic quantum states with known density matrix properties."""
        states = []
        dimension = 2**num_qubits
        
        # Create computational basis states
        for i in range(dimension):
            state = np.zeros(dimension)
            state[i] = 1.0  # Computational basis state
            states.append(state)
        
        # Create some superposition states
        for i in range(min(10, dimension)):
            # Equal superposition of first i+1 basis states
            state = np.zeros(dimension)
            for j in range(i + 1):
                state[j] = 1.0 / math.sqrt(i + 1)
            states.append(state)
        
        return states
    
    def create_unitary_matrices(self, dimension: int = 1024, num_matrices: int = 5) -> List[np.ndarray]:
        """Create synthetic unitary matrices with known mathematical properties."""
        matrices = []
        
        for _ in range(num_matrices):
            # Generate random complex matrix
            A = np.random.randn(dimension, dimension) + 1j * np.random.randn(dimension, dimension)
            
            # QR decomposition to get unitary matrix
            Q, R = np.linalg.qr(A)
            
            # Ensure proper unitary (Q*Q = I)
            Q = Q @ np.diag(np.sign(np.diag(R)))
            
            matrices.append(Q)
        
        return matrices
    
    def create_binding_matrices(self, dimension: int = 1024, num_matrices: int = 5) -> List[np.ndarray]:
        """Create synthetic binding matrices with known mathematical properties."""
        matrices = []
        
        for _ in range(num_matrices):
            # Create full-rank matrix for invertible binding
            matrix = np.random.randn(dimension, dimension)
            
            # Ensure full rank by adding small diagonal perturbation
            matrix = matrix + 0.01 * np.eye(dimension)
            
            # Normalize columns for stability
            matrix = matrix / np.linalg.norm(matrix, axis=0)
            
            matrices.append(matrix)
        
        return matrices
    
    def create_learning_curves(self, num_curves: int = 3, max_points: int = 100) -> List[Dict[str, List[float]]]:
        """Create synthetic learning curves with known mathematical properties."""
        curves = []
        
        for i in range(num_curves):
            # Create different learning curve shapes
            if i == 0:
                # Exponential approach to maximum
                x = np.linspace(0, max_points, max_points)
                y = 0.9 * (1 - np.exp(-x / 20)) + 0.1
            elif i == 1:
                # Logistic growth
                x = np.linspace(0, max_points, max_points)
                y = 0.9 / (1 + np.exp(-(x - 30) / 10)) + 0.05
            else:
                # Power law growth
                x = np.linspace(1, max_points, max_points)
                y = 0.9 * (1 - x**(-0.5)) + 0.1
            
            curves.append({
                'x': x.tolist(),
                'y': y.tolist(),
                'type': ['exponential', 'logistic', 'power_law'][i]
            })
        
        return curves
    
    def create_spectral_test_data(self, dimension: int = 1024, num_tests: int = 10) -> List[Dict[str, Any]]:
        """Create synthetic data for spectral property testing."""
        test_data = []
        
        for i in range(num_tests):
            # Create signal with known spectral properties
            frequencies = np.random.uniform(0.1, 0.4, size=dimension//2)
            phases = np.random.uniform(0, 2*np.pi, size=dimension//2)
            
            # Create signal in frequency domain
            spectrum = np.zeros(dimension, dtype=complex)
            spectrum[:dimension//2] = np.exp(1j * phases)
            spectrum[dimension//2:] = np.exp(-1j * phases)[::-1]
            
            # Transform to time domain
            signal = np.fft.ifft(spectrum).real
            
            test_data.append({
                'signal': signal.tolist(),
                'spectrum': spectrum.tolist(),
                'frequencies': frequencies.tolist(),
                'phases': phases.tolist(),
                'expected_energy': np.sum(np.abs(spectrum)**2) / dimension
            })
        
        return test_data
    
    def create_synthetic_dataset(self, dataset_type: str, **kwargs) -> SyntheticDataset:
        """Create synthetic dataset with provenance and guarantees."""
        generation_timestamp = datetime.utcnow().isoformat()
        
        if dataset_type == "knowledge_graph":
            data = self.create_knowledge_graph(**kwargs)
            guarantees = [
                "All entities are unique strings",
                "All relations are unique strings", 
                "All triples follow mathematical precision pattern",
                "Values are derived from π for mathematical consistency"
            ]
            
        elif dataset_type == "bhdc_vectors":
            data = self.create_bhdc_test_vectors(**kwargs)
            guarantees = [
                "All vectors are unit norm (||v|| = 1)",
                "Vectors are randomly distributed on unit sphere",
                "Mathematical properties suitable for BHDC testing"
            ]
            
        elif dataset_type == "orthogonal_roles":
            data = self.create_orthogonal_roles(**kwargs)
            guarantees = [
                "All role vectors are mutually orthogonal (⟨r_i,r_j⟩ = 0 for i≠j)",
                "All role vectors are unit norm (||r_i|| = 1)",
                "Created using Gram-Schmidt orthogonalization"
            ]
            
        elif dataset_type == "quantum_states":
            data = self.create_quantum_states(**kwargs)
            guarantees = [
                "All states are properly normalized (⟨ψ|ψ⟩ = 1)",
                "Density matrices are positive semi-definite",
                "Computational basis states are orthogonal"
            ]
            
        elif dataset_type == "learning_curves":
            data = self.create_learning_curves(**kwargs)
            guarantees = [
                "All curves approach realistic asymptotic values",
                "Curves follow known mathematical models",
                "Suitable for learning rate analysis"
            ]
            
        else:
            raise ValueError(f"Unknown dataset type: {dataset_type}")
        
        # Extract properties
        if hasattr(data, '__dict__'):
            properties = data.__dict__
        elif isinstance(data, list) and data:
            if isinstance(data[0], np.ndarray):
                properties = {
                    "num_items": len(data),
                    "dimension": data[0].shape[0] if len(data[0].shape) > 0 else 0,
                    "type": "numpy_array_list"
                }
            else:
                properties = {
                    "num_items": len(data),
                    "type": "list"
                }
        else:
            properties = {"type": str(type(data))}
        
        return SyntheticDataset(
            name=dataset_type,
            data=data,
            properties=properties,
            generation_timestamp=generation_timestamp,
            mathematical_guarantees=guarantees
        )
    
    def save_dataset(self, dataset: SyntheticDataset, filepath: str):
        """Save synthetic dataset to file."""
        # Convert numpy arrays to lists for JSON serialization
        serializable_data = dataset.data
        if isinstance(dataset.data, list) and dataset.data and isinstance(dataset.data[0], np.ndarray):
            serializable_data = [arr.tolist() for arr in dataset.data]
        elif hasattr(dataset.data, '__dict__'):
            # Handle KnowledgeGraph and similar objects
            if hasattr(dataset.data, 'triples'):
                serializable_data = {
                    'entities': dataset.data.entities,
                    'relations': dataset.data.relations,
                    'triples': dataset.data.triples
                }
            else:
                serializable_data = dataset.data.__dict__
        
        save_dict = {
            'name': dataset.name,
            'data': serializable_data,
            'properties': dataset.properties,
            'generation_timestamp': dataset.generation_timestamp,
            'mathematical_guarantees': dataset.mathematical_guarantees
        }
        
        with open(filepath, 'w') as f:
            json.dump(save_dict, f, indent=2)
    
    def load_dataset(self, filepath: str) -> SyntheticDataset:
        """Load synthetic dataset from file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return SyntheticDataset(
            name=data['name'],
            data=data['data'],
            properties=data['properties'],
            generation_timestamp=data['generation_timestamp'],
            mathematical_guarantees=data['mathematical_guarantees']
        )
    
    def generate_comprehensive_test_suite(self, dimension: int = 1024) -> Dict[str, SyntheticDataset]:
        """Generate comprehensive synthetic test suite."""
        test_suite = {}
        
        # Generate all types of synthetic data
        test_suite['knowledge_graph'] = self.create_synthetic_dataset('knowledge_graph', num_entities=50, num_relations=10)
        test_suite['bhdc_vectors'] = self.create_synthetic_dataset('bhdc_vectors', dimension=dimension, num_vectors=100)
        test_suite['orthogonal_roles'] = self.create_synthetic_dataset('orthogonal_roles', num_roles=10, dimension=dimension)
        test_suite['quantum_states'] = self.create_synthetic_dataset('quantum_states', num_qubits=4)
        test_suite['learning_curves'] = self.create_synthetic_dataset('learning_curves', num_curves=3, max_points=100)
        
        return test_suite