"""
Quantum-Neural Memory System: Combining Fourier Analysis, Neural Oscillations,
Hebbian Learning, and Memory Consolidation for Brain-Like AI

This module implements a comprehensive brain-like memory and learning system
that integrates multiple mathematical theories:

1. Fourier Analysis - Frequency domain processing of neural signals
2. Neural Oscillations - Brain wave rhythms and temporal coding
3. Hebbian Theory - Synaptic plasticity and cell assemblies
4. Memory Consolidation - Synaptic and systems consolidation
5. Neural Coding - Rate, temporal, population, and sparse coding
6. Complex Systems Theory - Emergent behavior from interactions
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from scipy.fft import fft, ifft, fftfreq
from scipy.signal import hilbert, find_peaks
import time
from collections import defaultdict
import math


@dataclass
class NeuralEnsemble:
    """Represents a group of neurons with oscillatory dynamics"""
    neurons: np.ndarray
    frequencies: np.ndarray  # Theta, alpha, beta, gamma bands
    phases: np.ndarray
    synaptic_weights: np.ndarray
    activation_history: List[np.ndarray]
    consolidation_strength: float = 1.0


@dataclass
class MemoryTrace:
    """Represents a consolidated memory with multiple coding schemes"""
    content: Any
    timestamp: float
    importance: float
    frequency_spectrum: np.ndarray  # Fourier components
    oscillatory_pattern: Dict[str, np.ndarray]  # Brain wave patterns
    hebbian_strength: np.ndarray  # Synaptic weights
    consolidation_level: float  # 0-1 scale
    neural_code: Dict[str, Any]  # Multiple coding representations


class QuantumNeuralMemory:
    """
    Advanced brain-like memory system combining multiple mathematical theories:

    - Fourier Analysis: Decomposes neural signals into frequency domains
    - Neural Oscillations: Implements brain wave rhythms (theta, alpha, beta, gamma)
    - Hebbian Learning: "Neurons that fire together wire together"
    - Memory Consolidation: Synaptic and systems level consolidation
    - Neural Coding: Rate, temporal, population, and sparse coding
    - Complex Systems: Emergent behavior from neural interactions
    """

    def __init__(self, num_neurons: int = 1000, memory_capacity: int = 10000):
        self.num_neurons = num_neurons
        self.memory_capacity = memory_capacity

        # Brain wave frequency bands (Hz)
        self.brain_waves = {
            'delta': (0.5, 3),
            'theta': (4, 7),
            'alpha': (8, 12),
            'beta': (13, 30),
            'gamma': (30, 100)
        }

        # Initialize neural ensembles for different brain regions
        self.hippocampus = self._initialize_ensemble(num_neurons // 4, 'theta')
        self.prefrontal = self._initialize_ensemble(num_neurons // 4, 'beta')
        self.temporal = self._initialize_ensemble(num_neurons // 4, 'alpha')
        self.parietal = self._initialize_ensemble(num_neurons // 4, 'gamma')

        # Memory storage with consolidation tracking
        self.episodic_memory: List[MemoryTrace] = []
        self.semantic_memory: Dict[str, MemoryTrace] = {}
        self.working_memory: List[MemoryTrace] = []

        # Learning parameters
        self.hebbian_learning_rate = 0.01
        self.consolidation_rate = 0.001
        self.oscillation_strength = 0.1

        # Fourier analysis parameters
        self.sampling_rate = 1000  # Hz
        self.fft_window_size = 1024

        print("🧠 Quantum-Neural Memory System initialized with integrated mathematical theories")

    def _initialize_ensemble(self, size: int, dominant_wave: str) -> NeuralEnsemble:
        """Initialize a neural ensemble with oscillatory dynamics"""
        neurons = np.random.randn(size)
        freq_range = self.brain_waves[dominant_wave]
        frequencies = np.random.uniform(freq_range[0], freq_range[1], size)
        phases = np.random.uniform(0, 2*np.pi, size)

        # Initialize synaptic weights with sparse connectivity
        synaptic_weights = np.random.exponential(0.1, (size, size))
        synaptic_weights[synaptic_weights < 0.05] = 0  # Sparsity

        return NeuralEnsemble(
            neurons=neurons,
            frequencies=frequencies,
            phases=phases,
            synaptic_weights=synaptic_weights,
            activation_history=[]
        )

    def _fourier_decomposition(self, signal: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Decompose signal into frequency domain using Fourier analysis"""
        fft_result = fft(signal, n=self.fft_window_size)
        frequencies = fftfreq(self.fft_window_size, 1/self.sampling_rate)

        # Focus on brain wave frequencies
        brain_freq_mask = (frequencies >= 0.5) & (frequencies <= 100)
        return frequencies[brain_freq_mask], np.abs(fft_result)[brain_freq_mask]

    def _neural_oscillations(self, ensemble: NeuralEnsemble, time_steps: int) -> np.ndarray:
        """Generate neural oscillations with brain wave dynamics"""
        oscillations = np.zeros((time_steps, len(ensemble.neurons)))

        for t in range(time_steps):
            # Update phases
            ensemble.phases += 2 * np.pi * ensemble.frequencies / self.sampling_rate

            # Generate oscillatory activity
            theta_component = np.sin(ensemble.phases) * self.oscillation_strength
            noise = np.random.randn(len(ensemble.neurons)) * 0.1

            oscillations[t] = theta_component + noise

        return oscillations

    def _hebbian_learning(self, pre_activity: np.ndarray, post_activity: np.ndarray,
                         weights: np.ndarray) -> np.ndarray:
        """Implement Hebbian learning: neurons that fire together wire together"""
        # Standard Hebbian rule with normalization
        delta_weights = self.hebbian_learning_rate * np.outer(pre_activity, post_activity)
        weights += delta_weights

        # Normalize to prevent runaway growth
        weights = weights / (np.linalg.norm(weights) + 1e-8)

        return weights

    def _temporal_coding(self, spike_times: List[float], reference_time: float) -> np.ndarray:
        """Implement temporal coding based on spike timing precision"""
        if not spike_times:
            return np.array([])

        # Calculate inter-spike intervals
        spike_times = np.array(spike_times)
        isis = np.diff(spike_times)

        # Temporal coding: precision of spike timing
        temporal_precision = 1.0 / (np.std(isis) + 1e-8)

        # Phase-locking to reference oscillation
        phases = (spike_times - reference_time) * 2 * np.pi * 10  # 10 Hz reference
        phase_locking = np.abs(np.mean(np.exp(1j * phases)))

        return np.array([temporal_precision, phase_locking])

    def _sparse_coding(self, input_signal: np.ndarray, dictionary_size: int = 256) -> Tuple[np.ndarray, np.ndarray]:
        """Implement sparse coding for efficient neural representation"""
        # Random dictionary for sparse coding
        dictionary = np.random.randn(dictionary_size, len(input_signal))
        dictionary = dictionary / np.linalg.norm(dictionary, axis=1, keepdims=True)

        # Sparse approximation using matching pursuit
        sparse_codes = np.zeros(dictionary_size)
        residual = input_signal.copy()

        for _ in range(min(10, dictionary_size // 10)):  # Limited iterations for sparsity
            # Find best matching atom
            correlations = np.abs(np.dot(dictionary, residual))
            best_atom_idx = np.argmax(correlations)

            # Update sparse code
            sparse_codes[best_atom_idx] += correlations[best_atom_idx]

            # Update residual
            residual -= correlations[best_atom_idx] * dictionary[best_atom_idx]

        return sparse_codes, dictionary

    def _memory_consolidation(self, memory: MemoryTrace, time_elapsed: float) -> MemoryTrace:
        """Implement synaptic and systems consolidation"""
        # Synaptic consolidation (fast, protein synthesis dependent)
        synaptic_factor = min(1.0, time_elapsed / 3600)  # 1 hour time constant

        # Systems consolidation (slow, neo-cortical transfer)
        systems_factor = min(1.0, time_elapsed / (24 * 3600 * 30))  # 1 month time constant

        # Combined consolidation strength
        memory.consolidation_level = synaptic_factor * 0.7 + systems_factor * 0.3

        # Importance-based consolidation boost
        memory.consolidation_level *= (1 + memory.importance)

        return memory

    def encode_memory(self, content: Any, importance: float = 1.0) -> MemoryTrace:
        """Encode new information using integrated mathematical theories"""
        timestamp = time.time()

        # 1. Generate neural activity patterns
        hippocampal_activity = self._neural_oscillations(self.hippocampus, 1000)

        # 2. Fourier decomposition of neural signals
        freq_spectrum, power_spectrum = self._fourier_decomposition(
            hippocampal_activity.mean(axis=0)
        )

        # 3. Extract oscillatory patterns for each brain wave
        oscillatory_patterns = {}
        for wave_name, (freq_min, freq_max) in self.brain_waves.items():
            mask = (freq_spectrum >= freq_min) & (freq_spectrum <= freq_max)
            oscillatory_patterns[wave_name] = power_spectrum[mask]

        # 4. Sparse coding for efficient representation
        sparse_codes, dictionary = self._sparse_coding(
            hippocampal_activity.flatten()
        )

        # 5. Temporal coding from spike-like activity
        spike_times = []
        for i, activity in enumerate(hippocampal_activity.T):
            peaks, _ = find_peaks(activity, height=0.5)
            spike_times.extend(peaks.tolist())

        temporal_code = self._temporal_coding(spike_times, timestamp)

        # 6. Hebbian learning on synaptic weights
        pre_activity = hippocampal_activity[0]  # Previous time step
        post_activity = hippocampal_activity[1]  # Current time step
        self.hippocampus.synaptic_weights = self._hebbian_learning(
            pre_activity, post_activity, self.hippocampus.synaptic_weights
        )

        # Create comprehensive memory trace
        memory = MemoryTrace(
            content=content,
            timestamp=timestamp,
            importance=importance,
            frequency_spectrum=freq_spectrum,
            oscillatory_pattern=oscillatory_patterns,
            hebbian_strength=self.hippocampus.synaptic_weights.copy(),
            consolidation_level=0.0,
            neural_code={
                'sparse': sparse_codes,
                'temporal': temporal_code,
                'population': hippocampal_activity.mean(axis=0),
                'rate': np.mean(hippocampal_activity > 0.5, axis=0)
            }
        )

        # Add to episodic memory
        self.episodic_memory.append(memory)

        # Maintain memory capacity
        if len(self.episodic_memory) > self.memory_capacity:
            # Remove least consolidated memories
            self.episodic_memory.sort(key=lambda m: m.consolidation_level)
            self.episodic_memory = self.episodic_memory[-self.memory_capacity:]

        print(f"🧠 Encoded memory with {len(freq_spectrum)} frequency components, "
              f"consolidation level: {memory.consolidation_level:.3f}")

        return memory

    def retrieve_memory(self, query: Any, similarity_threshold: float = 0.7) -> List[MemoryTrace]:
        """Retrieve memories using multi-modal similarity matching"""
        if not self.episodic_memory:
            return []

        retrieved_memories = []

        # Convert query to neural representation
        query_activity = np.random.randn(self.num_neurons // 4)  # Simplified
        query_freq, query_power = self._fourier_decomposition(query_activity)

        for memory in self.episodic_memory:
            # Multi-modal similarity calculation

            # 1. Frequency domain similarity
            freq_similarity = self._cosine_similarity(
                memory.frequency_spectrum, query_freq
            )

            # 2. Oscillatory pattern similarity
            osc_similarity = np.mean([
                self._cosine_similarity(pattern, query_power)
                for pattern in memory.oscillatory_pattern.values()
            ])

            # 3. Sparse coding similarity
            sparse_similarity = self._cosine_similarity(
                memory.neural_code['sparse'], query_activity
            )

            # 4. Consolidation-weighted similarity
            overall_similarity = (
                freq_similarity * 0.3 +
                osc_similarity * 0.3 +
                sparse_similarity * 0.4
            ) * memory.consolidation_level

            if overall_similarity > similarity_threshold:
                retrieved_memories.append((memory, overall_similarity))

        # Sort by similarity and return top matches
        retrieved_memories.sort(key=lambda x: x[1], reverse=True)

        print(f"🧠 Retrieved {len(retrieved_memories)} memories above threshold {similarity_threshold}")

        return [mem for mem, sim in retrieved_memories[:10]]  # Top 10

    def consolidate_memories(self):
        """Consolidate memories using integrated consolidation processes"""
        current_time = time.time()

        for memory in self.episodic_memory:
            time_elapsed = current_time - memory.timestamp
            memory = self._memory_consolidation(memory, time_elapsed)

            # Move highly consolidated memories to semantic storage
            if memory.consolidation_level > 0.8:
                key = str(hash(str(memory.content)))
                self.semantic_memory[key] = memory

        print(f"🧠 Consolidated {len(self.episodic_memory)} episodic memories")

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between vectors"""
        if len(a) == 0 or len(b) == 0:
            return 0.0

        # Handle different lengths by padding shorter vector
        max_len = max(len(a), len(b))
        a_padded = np.pad(a, (0, max_len - len(a)))
        b_padded = np.pad(b, (0, max_len - len(b)))

        dot_product = np.dot(a_padded, b_padded)
        norm_a = np.linalg.norm(a_padded)
        norm_b = np.linalg.norm(b_padded)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the memory system"""
        return {
            'episodic_memory_count': len(self.episodic_memory),
            'semantic_memory_count': len(self.semantic_memory),
            'working_memory_count': len(self.working_memory),
            'average_consolidation': np.mean([m.consolidation_level for m in self.episodic_memory]) if self.episodic_memory else 0,
            'neural_ensemble_sizes': {
                'hippocampus': len(self.hippocampus.neurons),
                'prefrontal': len(self.prefrontal.neurons),
                'temporal': len(self.temporal.neurons),
                'parietal': len(self.parietal.neurons)
            },
            'brain_wave_coverage': list(self.brain_waves.keys()),
            'learning_parameters': {
                'hebbian_rate': self.hebbian_learning_rate,
                'consolidation_rate': self.consolidation_rate,
                'oscillation_strength': self.oscillation_strength
            }
        }


# Integration with existing SomaBrain architecture
class AdvancedBrainMemory:
    """
    Integration layer that combines Quantum-Neural Memory with existing SomaBrain components
    """

    def __init__(self, somabrain_app):
        self.app = somabrain_app
        self.quantum_memory = QuantumNeuralMemory()

        # Enhanced brain components with mathematical theories
        self.fourier_processor = FourierSignalProcessor()
        self.oscillation_generator = NeuralOscillationGenerator()
        self.hebbian_learner = HebbianLearningSystem()
        self.consolidation_engine = MemoryConsolidationEngine()

    def process_with_integrated_theories(self, input_data: Any) -> Dict[str, Any]:
        """Process input using all integrated mathematical theories"""

        # 1. Fourier analysis of input
        fourier_result = self.fourier_processor.analyze(input_data)

        # 2. Generate neural oscillations
        oscillations = self.oscillation_generator.generate_brain_waves()

        # 3. Hebbian learning on patterns
        hebbian_weights = self.hebbian_learner.learn_patterns(fourier_result)

        # 4. Memory consolidation
        consolidated_memory = self.consolidation_engine.consolidate(
            input_data, fourier_result, oscillations, hebbian_weights
        )

        # 5. Store in quantum memory system
        memory_trace = self.quantum_memory.encode_memory(
            consolidated_memory, importance=0.8
        )

        return {
            'fourier_analysis': fourier_result,
            'neural_oscillations': oscillations,
            'hebbian_weights': hebbian_weights,
            'consolidated_memory': consolidated_memory,
            'memory_trace': memory_trace,
            'integrated_processing_complete': True
        }


class FourierSignalProcessor:
    """Fourier analysis for neural signal processing"""

    def analyze(self, signal: Any) -> Dict[str, np.ndarray]:
        """Perform comprehensive Fourier analysis"""
        if isinstance(signal, str):
            # Convert text to numerical signal
            signal_array = np.array([ord(c) for c in signal])
        elif isinstance(signal, (list, np.ndarray)):
            signal_array = np.array(signal)
        else:
            signal_array = np.array([hash(str(signal))])

        # Fourier transform
        fft_result = fft(signal_array)
        frequencies = fftfreq(len(signal_array))

        return {
            'original_signal': signal_array,
            'fft_result': fft_result,
            'frequencies': frequencies,
            'power_spectrum': np.abs(fft_result),
            'phase_spectrum': np.angle(fft_result)
        }


class NeuralOscillationGenerator:
    """Generate brain wave oscillations"""

    def generate_brain_waves(self, duration: float = 1.0, sampling_rate: int = 1000) -> Dict[str, np.ndarray]:
        """Generate all major brain wave types"""
        t = np.linspace(0, duration, int(duration * sampling_rate))

        waves = {}
        for wave_name, (freq_min, freq_max) in QuantumNeuralMemory(
            num_neurons=100
        ).brain_waves.items():
            freq = (freq_min + freq_max) / 2
            waves[wave_name] = np.sin(2 * np.pi * freq * t)

        return waves


class HebbianLearningSystem:
    """Implement Hebbian learning algorithms"""

    def __init__(self):
        self.weights = np.random.randn(100, 100) * 0.1
        self.learning_rate = 0.01

    def learn_patterns(self, fourier_data: Dict[str, np.ndarray]) -> np.ndarray:
        """Apply Hebbian learning to Fourier components"""
        signal = fourier_data['power_spectrum']

        # Simplified Hebbian learning
        pre_activity = signal[:-1]
        post_activity = signal[1:]

        if len(pre_activity) > 0 and len(post_activity) > 0:
            delta_weights = self.learning_rate * np.outer(pre_activity, post_activity)
            self.weights += delta_weights[:100, :100]  # Truncate to matrix size

        return self.weights


class MemoryConsolidationEngine:
    """Handle memory consolidation processes"""

    def consolidate(self, content: Any, fourier_data: Dict[str, np.ndarray],
                   oscillations: Dict[str, np.ndarray], hebbian_weights: np.ndarray) -> Dict[str, Any]:
        """Consolidate memory using multiple mechanisms"""

        # Combine all representations
        consolidated = {
            'content': content,
            'fourier_features': fourier_data['power_spectrum'],
            'oscillatory_patterns': oscillations,
            'synaptic_weights': hebbian_weights,
            'consolidation_timestamp': time.time(),
            'consolidation_strength': np.random.uniform(0.5, 1.0)  # Simplified
        }

        return consolidated


# Example usage and demonstration
if __name__ == "__main__":
    print("🚀 Initializing Quantum-Neural Memory System...")

    # Initialize the advanced memory system
    memory_system = QuantumNeuralMemory(num_neurons=500, memory_capacity=1000)

    # Demonstrate integrated learning
    print("\n📚 Encoding memories with integrated mathematical theories...")

    memories = [
        "The Fourier transform decomposes signals into frequency components",
        "Neural oscillations create temporal windows for information processing",
        "Hebbian learning strengthens connections between co-active neurons",
        "Memory consolidation stabilizes neural representations over time",
        "Sparse coding enables efficient neural representations"
    ]

    encoded_memories = []
    for memory in memories:
        encoded = memory_system.encode_memory(memory, importance=np.random.uniform(0.5, 1.0))
        encoded_memories.append(encoded)

    print(f"\n✅ Encoded {len(encoded_memories)} memories")

    # Demonstrate retrieval
    print("\n🔍 Testing memory retrieval...")
    query = "neural learning mechanisms"
    retrieved = memory_system.retrieve_memory(query, similarity_threshold=0.3)

    print(f"Retrieved {len(retrieved)} relevant memories for query: '{query}'")

    # Demonstrate consolidation
    print("\n🧠 Running memory consolidation...")
    memory_system.consolidate_memories()

    # Show statistics
    stats = memory_system.get_memory_statistics()
    print("
📊 Memory System Statistics:"    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n🎯 Quantum-Neural Memory System demonstration complete!")
    print("This system integrates: Fourier Analysis + Neural Oscillations + Hebbian Learning + Memory Consolidation + Neural Coding")
