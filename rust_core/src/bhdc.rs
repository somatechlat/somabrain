//! BHDC (Binary Hyperdimensional Computing) and Quantum modules.
//!
//! Part of GMD MathCore implementation.

use pyo3::prelude::*;
use sha2::{Sha256, Digest};
use rand_pcg::Pcg64;
use rand::{SeedableRng, Rng};

// ==================== BHDC Module ====================

/// Binary Hyperdimensional Computing (BHDC) Encoder
#[pyclass]
pub struct BHDCEncoder {
    #[pyo3(get)]
    pub dimension: usize,
    #[pyo3(get)]
    pub sparsity: f64,
    #[pyo3(get)]
    pub mode: String,
    seed: u64,
}

#[pymethods]
impl BHDCEncoder {
    #[new]
    #[pyo3(signature = (dimension, sparsity, seed, mode))]
    pub fn new(dimension: usize, sparsity: f64, seed: u64, mode: String) -> Self {
        BHDCEncoder { dimension, sparsity, seed, mode }
    }

    pub fn encode(&self, key: String, value: f64) -> Vec<f64> {
        let mut hasher = Sha256::new();
        hasher.update(key.as_bytes());
        hasher.update(&value.to_le_bytes());
        let result = hasher.finalize();
        let seed_bytes: [u8; 8] = result[0..8].try_into().unwrap();
        let seed = u64::from_le_bytes(seed_bytes);
        let mut rng = Pcg64::seed_from_u64(seed);

        let mut vector = vec![0.0; self.dimension];
        let mut indices: Vec<usize> = (0..self.dimension).collect();

        for _ in 0..(self.dimension as f64 * self.sparsity) as usize {
            if let Some(idx) = indices.pop() {
                let val = if self.mode == "zero_one" {
                    1.0
                } else {
                    if rng.gen::<f64>() > 0.5 { 1.0 } else { -1.0 }
                };
                vector[idx] = val;
            }
        }

        if self.mode == "zero_one" {
            let mean: f64 = vector.iter().sum::<f64>() / self.dimension as f64;
            for v in vector.iter_mut() {
                *v -= mean;
            }
        }

        vector
    }

    pub fn bind(&self, v1: Vec<f64>, v2: Vec<f64>) -> Vec<f64> {
        v1.iter().zip(v2.iter()).map(|(a, b)| a * b).collect()
    }

    pub fn unbind(&self, v1: Vec<f64>, v2: Vec<f64>) -> Vec<f64> {
        v1.iter().zip(v2.iter()).map(|(a, b)| a / (b + 1e-8)).collect()
    }

    pub fn bundle(&self, vectors: Vec<Vec<f64>>) -> Vec<f64> {
        let mut result = vec![0.0; self.dimension];
        let len = vectors.len();
        for v in &vectors {
            for (i, val) in v.iter().enumerate() {
                result[i] += val;
            }
        }
        for r in result.iter_mut() {
            *r /= len as f64;
        }
        result
    }

    pub fn similarity(&self, v1: Vec<f64>, v2: Vec<f64>) -> f64 {
        let dot: f64 = v1.iter().zip(v2.iter()).map(|(a, b)| a * b).sum();
        let norm1: f64 = v1.iter().map(|x| x * x).sum::<f64>().sqrt();
        let norm2: f64 = v2.iter().map(|x| x * x).sum::<f64>().sqrt();
        if norm1 == 0.0 || norm2 == 0.0 { 0.0 } else { dot / (norm1 * norm2) }
    }

    pub fn permute(&self, v: Vec<f64>) -> Vec<f64> {
        let mut result = vec![0.0; v.len()];
        for i in 0..v.len() {
            result[(i + 1) % v.len()] = v[i];
        }
        result
    }
}

// ==================== Quantum Module ====================

#[pyclass]
pub struct QuantumState {
    #[pyo3(get)]
    pub amplitude: Vec<f64>,
    #[pyo3(get)]
    pub phase: Vec<f64>,
}

#[pymethods]
impl QuantumState {
    #[new]
    pub fn new(amplitude: Vec<f64>, phase: Vec<f64>) -> Self {
        QuantumState { amplitude, phase }
    }

    pub fn norm(&self) -> f64 {
        self.amplitude.iter().map(|x| x * x).sum::<f64>().sqrt()
    }

    pub fn normalize(&self) -> (Vec<f64>, Vec<f64>) {
        let n = self.norm();
        if n == 0.0 {
            (self.amplitude.clone(), self.phase.clone())
        } else {
            let amp = self.amplitude.iter().map(|x| x / n).collect();
            (amp, self.phase.clone())
        }
    }
}

#[pyclass]
pub struct QuantumModule {
    #[pyo3(get)]
    pub dimension: usize,
}

#[pymethods]
impl QuantumModule {
    #[new]
    pub fn new(dimension: usize) -> Self {
        QuantumModule { dimension }
    }

    pub fn superposition(&self, vectors: Vec<Vec<f64>>) -> Vec<f64> {
        let mut result = vec![0.0; self.dimension];
        for v in vectors {
            for (i, val) in v.iter().enumerate() {
                result[i] += val;
            }
        }
        let norm: f64 = result.iter().map(|x| x * x).sum::<f64>().sqrt();
        if norm > 0.0 {
            for r in result.iter_mut() {
                *r /= norm;
            }
        }
        result
    }

    pub fn bind(&self, v1: Vec<f64>, v2: Vec<f64>) -> Vec<f64> {
        v1.iter().zip(v2.iter()).map(|(a, b)| a * b).collect()
    }

    pub fn unbind(&self, v1: Vec<f64>, v2: Vec<f64>) -> Vec<f64> {
        v1.iter().zip(v2.iter()).map(|(a, b)| a / (b + 1e-8)).collect()
    }

    pub fn measure(&self, state: &QuantumState) -> Vec<f64> {
        state.amplitude.clone()
    }
}
