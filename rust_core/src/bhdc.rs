//! BHDC (Binary Hyperdimensional Computing) and Quantum modules.
//!
//! Complete implementation matching Python API for production use.
//! Supports: tenant_id, model_version, seed bundles, binary_mode.

use pyo3::prelude::*;
use sha2::{Sha256, Digest};
use rand_pcg::Pcg64;
use rand::{SeedableRng, Rng};

// ==================== Seed Bundle ====================

/// Build deterministic seed from multiple components
fn build_seed_bundle(label: &str, base_seed: u64, extra_seed: Option<&str>,
                     tenant_id: Option<&str>, model_version: Option<&str>) -> u64 {
    let mut hasher = Sha256::new();
    hasher.update(label.as_bytes());
    hasher.update(&base_seed.to_le_bytes());
    if let Some(s) = extra_seed {
        hasher.update(s.as_bytes());
    }
    if let Some(t) = tenant_id {
        hasher.update(t.as_bytes());
    }
    if let Some(m) = model_version {
        hasher.update(m.as_bytes());
    }
    let result = hasher.finalize();
    let seed_bytes: [u8; 8] = result[0..8].try_into().unwrap();
    u64::from_le_bytes(seed_bytes)
}

/// Hash string to u64 seed
fn seed_to_uint64(s: &str) -> u64 {
    let mut hasher = Sha256::new();
    hasher.update(s.as_bytes());
    let result = hasher.finalize();
    let seed_bytes: [u8; 8] = result[0..8].try_into().unwrap();
    u64::from_le_bytes(seed_bytes)
}

// ==================== BHDCEncoder ====================

/// Binary Hyperdimensional Computing Encoder - Full Production API
///
/// Matches Python API: tenant_id, model_version, seed bundles, binary_mode
#[pyclass]
pub struct BHDCEncoder {
    #[pyo3(get)]
    pub dim: usize,
    #[pyo3(get)]
    pub sparsity: f64,
    #[pyo3(get)]
    pub binary_mode: String,
    base_seed: u64,
    bundle_seed: u64,
    active_count: usize,
}

#[pymethods]
impl BHDCEncoder {
    /// Create new encoder with full production options
    #[new]
    #[pyo3(signature = (dim, sparsity, base_seed, _dtype="float32", extra_seed=None, tenant_id=None, model_version=None, binary_mode="pm_one"))]
    pub fn new(dim: usize, sparsity: f64, base_seed: u64, _dtype: &str,
               extra_seed: Option<&str>, tenant_id: Option<&str>,
               model_version: Option<&str>, binary_mode: &str) -> Self {
        let bundle_seed = build_seed_bundle("bhdc", base_seed, extra_seed, tenant_id, model_version);
        let active = ((dim as f64) * sparsity).round() as usize;
        BHDCEncoder {
            dim,
            sparsity,
            binary_mode: binary_mode.to_string(),
            base_seed,
            bundle_seed,
            active_count: active.max(1).min(dim),
        }
    }

    /// Generate random sparse vector
    pub fn random_vector(&self) -> Vec<f64> {
        let mut rng = Pcg64::seed_from_u64(self.bundle_seed ^ rand::random::<u64>());
        self.vector_from_rng(&mut rng)
    }

    /// Generate deterministic vector for key
    pub fn vector_for_key(&self, key: &str) -> Vec<f64> {
        let seed = seed_to_uint64(key) ^ self.bundle_seed;
        let mut rng = Pcg64::seed_from_u64(seed);
        self.vector_from_rng(&mut rng)
    }

    /// Alias for vector_for_key
    pub fn vector_for_token(&self, token: &str) -> Vec<f64> {
        self.vector_for_key(token)
    }

    /// Encode key-value pair (legacy API)
    pub fn encode(&self, key: String, value: f64) -> Vec<f64> {
        let mut hasher = Sha256::new();
        hasher.update(key.as_bytes());
        hasher.update(&value.to_le_bytes());
        let result = hasher.finalize();
        let seed_bytes: [u8; 8] = result[0..8].try_into().unwrap();
        let seed = u64::from_le_bytes(seed_bytes) ^ self.bundle_seed;
        let mut rng = Pcg64::seed_from_u64(seed);
        self.vector_from_rng(&mut rng)
    }

    /// Elementwise product binding
    pub fn bind(&self, v1: Vec<f64>, v2: Vec<f64>) -> Vec<f64> {
        v1.iter().zip(v2.iter()).map(|(a, b)| a * b).collect()
    }

    /// Elementwise division unbinding
    pub fn unbind(&self, v1: Vec<f64>, v2: Vec<f64>) -> Vec<f64> {
        v1.iter().zip(v2.iter()).map(|(a, b)| a / (b.abs() + 1e-8) * b.signum()).collect()
    }

    /// Bundle (superposition) of vectors
    pub fn bundle(&self, vectors: Vec<Vec<f64>>) -> Vec<f64> {
        if vectors.is_empty() {
            return vec![0.0; self.dim];
        }
        let mut result = vec![0.0; self.dim];
        for v in &vectors {
            for (i, val) in v.iter().enumerate() {
                if i < self.dim {
                    result[i] += val;
                }
            }
        }
        // Normalize
        let norm: f64 = result.iter().map(|x| x * x).sum::<f64>().sqrt();
        if norm > 1e-10 {
            for r in result.iter_mut() {
                *r /= norm;
            }
        }
        result
    }

    /// Cosine similarity
    pub fn similarity(&self, v1: Vec<f64>, v2: Vec<f64>) -> f64 {
        let dot: f64 = v1.iter().zip(v2.iter()).map(|(a, b)| a * b).sum();
        let norm1: f64 = v1.iter().map(|x| x * x).sum::<f64>().sqrt();
        let norm2: f64 = v2.iter().map(|x| x * x).sum::<f64>().sqrt();
        if norm1 < 1e-10 || norm2 < 1e-10 { 0.0 } else { dot / (norm1 * norm2) }
    }

    /// Circular permutation
    pub fn permute(&self, v: Vec<f64>, times: i32) -> Vec<f64> {
        let n = v.len();
        if n == 0 { return v; }
        let shift = ((times % n as i32) + n as i32) as usize % n;
        let mut result = vec![0.0; n];
        for i in 0..n {
            result[(i + shift) % n] = v[i];
        }
        result
    }
}

impl BHDCEncoder {
    /// Internal: generate vector from RNG
    fn vector_from_rng(&self, rng: &mut Pcg64) -> Vec<f64> {
        let mut vector = vec![0.0; self.dim];

        // Fisher-Yates shuffle to select random indices
        let mut indices: Vec<usize> = (0..self.dim).collect();
        for i in 0..self.active_count.min(self.dim) {
            let j = rng.gen_range(i..self.dim);
            indices.swap(i, j);
        }

        // Set active positions
        for i in 0..self.active_count {
            let idx = indices[i];
            vector[idx] = if self.binary_mode == "zero_one" {
                1.0
            } else {
                if rng.gen::<f64>() > 0.5 { 1.0 } else { -1.0 }
            };
        }

        // Zero-mean for zero_one mode
        if self.binary_mode == "zero_one" {
            let mean: f64 = vector.iter().sum::<f64>() / self.dim as f64;
            for v in vector.iter_mut() {
                *v -= mean;
            }
        }

        vector
    }
}

// ==================== PermutationBinder ====================

/// Permutation-based binder with optional Hadamard mixing
#[pyclass]
pub struct PermutationBinder {
    #[pyo3(get)]
    pub dim: usize,
    perm: Vec<usize>,
    perm_inv: Vec<usize>,
    #[pyo3(get)]
    pub mix: String,
}

#[pymethods]
impl PermutationBinder {
    #[new]
    #[pyo3(signature = (dim, seed, _dtype="float32", mix="none"))]
    pub fn new(dim: usize, seed: u64, _dtype: &str, mix: &str) -> Self {
        let mut rng = Pcg64::seed_from_u64(seed);

        // Generate random permutation
        let mut perm: Vec<usize> = (0..dim).collect();
        for i in (1..dim).rev() {
            let j = rng.gen_range(0..=i);
            perm.swap(i, j);
        }

        // Compute inverse permutation
        let mut perm_inv = vec![0usize; dim];
        for (i, &p) in perm.iter().enumerate() {
            perm_inv[p] = i;
        }

        PermutationBinder {
            dim,
            perm,
            perm_inv,
            mix: mix.to_string(),
        }
    }

    /// Bind: permute b, then elementwise multiply
    pub fn bind(&self, a: Vec<f64>, b: Vec<f64>) -> Vec<f64> {
        let b_perm = self.apply_perm(&b, &self.perm);
        let mut result: Vec<f64> = a.iter().zip(b_perm.iter()).map(|(x, y)| x * y).collect();

        if self.mix == "hadamard" {
            crate::mathcore::fwht_inplace(&mut result);
        }

        // Normalize
        let norm: f64 = result.iter().map(|x| x * x).sum::<f64>().sqrt();
        if norm > 1e-10 {
            for r in result.iter_mut() {
                *r /= norm;
            }
        }
        result
    }

    /// Unbind: inverse of bind
    pub fn unbind(&self, c: Vec<f64>, b: Vec<f64>) -> Vec<f64> {
        let mut work = c.clone();

        if self.mix == "hadamard" {
            crate::mathcore::fwht_inplace(&mut work);
        }

        let b_perm = self.apply_perm(&b, &self.perm);
        let result: Vec<f64> = work.iter().zip(b_perm.iter())
            .map(|(x, y)| x / (y.abs() + 1e-8) * y.signum())
            .collect();

        // Normalize
        let norm: f64 = result.iter().map(|x| x * x).sum::<f64>().sqrt();
        if norm > 1e-10 {
            result.iter().map(|x| x / norm).collect()
        } else {
            result
        }
    }

    /// Permute vector n times
    pub fn permute(&self, vec: Vec<f64>, times: i32) -> Vec<f64> {
        if times == 0 { return vec; }
        let mut result = vec;
        let perm = if times > 0 { &self.perm } else { &self.perm_inv };
        for _ in 0..times.abs() {
            result = self.apply_perm(&result, perm);
        }
        result
    }

    /// Get permutation indices
    pub fn permutation(&self) -> Vec<usize> {
        self.perm.clone()
    }

    /// Get inverse permutation indices
    pub fn inverse_permutation(&self) -> Vec<usize> {
        self.perm_inv.clone()
    }
}

impl PermutationBinder {
    fn apply_perm(&self, v: &[f64], perm: &[usize]) -> Vec<f64> {
        perm.iter().map(|&i| v[i]).collect()
    }
}

// ==================== QuantumState ====================

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
        if n < 1e-10 {
            (self.amplitude.clone(), self.phase.clone())
        } else {
            (self.amplitude.iter().map(|x| x / n).collect(), self.phase.clone())
        }
    }
}

// ==================== QuantumModule ====================

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
                if i < self.dimension {
                    result[i] += val;
                }
            }
        }
        let norm: f64 = result.iter().map(|x| x * x).sum::<f64>().sqrt();
        if norm > 1e-10 {
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

/// Ensure values are binary {-1, +1}
#[pyfunction]
pub fn ensure_binary(values: Vec<f64>) -> Vec<f64> {
    values.iter().map(|&v| if v >= 0.0 { 1.0 } else { -1.0 }).collect()
}
