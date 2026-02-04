//! # GMD MathCore Theorems and Utility Modules
//!
//! Implementation per **MathCore White Paper v4.4 (Agentic Formulation)**.
//!
//! ## Theorems Implemented (Truthful Model)
//!
//! | Theorem | Function | Description |
//! |---------|----------|-------------|
//! | T1 | [`compute_optimal_p`] | Optimal sparsity p* for stability |
//! | T2 | [`BayesianMemory`] | Truthful SNR dynamics and Horizon L* |
//! | T3 | [`compute_wiener_lambda`] | Optimal Ridge λ* = σ_ε²/σ_v² |
//! | T3 | [`quantize_8bit`] | 8-bit symmetric quantization Δ=2/255 |
//! | T3 | [`wiener_unbind`] | MMSE-optimal unbinding |
//! | T4 | [`fwht`] | Fast Walsh-Hadamard (Deterministic O(D log D)) |
//!
//! ## Performance
//!
//! - FWHT: O(D log D) complexity (Deterministic)
//! - BayesianMemory: Age-dependent SNR horizon
//!
//! ## Usage
//!
//! ```python
//! import somabrain_rs as rs
//!
//! # Theorem 1: Optimal sparsity
//! p_star = rs.compute_optimal_p(0.01)
//!
//! # Theorem 2: Bayesian Memory
//! mem = rs.BayesianMemory(2048, eta=0.08)
//! mem.update(binding)
//! recalled = mem.recall(key)
//! ```

use pyo3::prelude::*;
use sha2::{Sha256, Digest};
use rand_pcg::Pcg64;
use rand::{SeedableRng, Rng};

// ==================== FNOM Module ====================

#[pyclass]
pub struct FNOM {
    #[pyo3(get)]
    pub bins: usize,
    kv_store: std::collections::HashMap<String, Vec<f64>>,
}

#[pymethods]
impl FNOM {
    #[new]
    pub fn new(bins: usize) -> Self {
        FNOM { bins, kv_store: std::collections::HashMap::new() }
    }

    pub fn encode(&mut self, key: String, value: String) -> Vec<f64> {
        let mut hasher = Sha256::new();
        hasher.update(key.as_bytes());
        hasher.update(value.as_bytes());
        let result = hasher.finalize();

        let mut spectrum = vec![0.0; self.bins];
        for i in 0..self.bins {
            let byte_idx = i % 32;
            spectrum[i] = (result[byte_idx] as f64) / 255.0;
        }

        self.kv_store.insert(key, spectrum.clone());
        spectrum
    }

    pub fn retrieve(&self, key: String) -> Option<Vec<f64>> {
        self.kv_store.get(&key).cloned()
    }

    pub fn similarity(&self, v1: Vec<f64>, v2: Vec<f64>) -> f64 {
        let dot: f64 = v1.iter().zip(v2.iter()).map(|(a, b)| a * b).sum();
        let norm1: f64 = v1.iter().map(|x| x * x).sum::<f64>().sqrt();
        let norm2: f64 = v2.iter().map(|x| x * x).sum::<f64>().sqrt();
        if norm1 == 0.0 || norm2 == 0.0 { 0.0 } else { dot / (norm1 * norm2) }
    }
}

// ==================== BatchNorm Module ====================

#[pyclass]
pub struct BatchNorm {
    #[pyo3(get)]
    pub running_mean: Vec<f64>,
    #[pyo3(get)]
    pub running_var: Vec<f64>,
    #[pyo3(get)]
    pub epsilon: f64,
}

#[pymethods]
impl BatchNorm {
    #[new]
    pub fn new(dimension: usize, epsilon: f64) -> Self {
        BatchNorm {
            running_mean: vec![0.0; dimension],
            running_var: vec![1.0; dimension],
            epsilon,
        }
    }

    pub fn inference(&self, x: Vec<f64>, gamma: Vec<f64>, beta: Vec<f64>) -> Vec<f64> {
        x.iter()
            .zip(self.running_mean.iter())
            .zip(self.running_var.iter())
            .zip(gamma.iter())
            .zip(beta.iter())
            .map(|((((x, mean), var), g), b)| g * ((x - mean) / (var + self.epsilon).sqrt()) + b)
            .collect()
    }

    pub fn update_running_stats(&mut self, batch_mean: Vec<f64>, batch_var: Vec<f64>, momentum: f64) {
        for i in 0..self.running_mean.len() {
            self.running_mean[i] = momentum * self.running_mean[i] + (1.0 - momentum) * batch_mean[i];
            self.running_var[i] = momentum * self.running_var[i] + (1.0 - momentum) * batch_var[i];
        }
    }
}

// ==================== Dropout Module ====================

#[pyclass]
pub struct Dropout {
    #[pyo3(get)]
    pub rate: f64,
    seed: u64,
}

#[pymethods]
impl Dropout {
    #[new]
    pub fn new(rate: f64) -> Self {
        Dropout { rate, seed: 42 }
    }

    pub fn apply(&self, input: Vec<f64>) -> Vec<f64> {
        let mut rng = Pcg64::seed_from_u64(self.seed);
        input.iter().map(|x| {
            if rng.gen::<f64>() < self.rate { 0.0 } else { *x / (1.0 - self.rate) }
        }).collect()
    }

    pub fn set_seed(&mut self, seed: u64) {
        self.seed = seed;
    }
}

// ==================== MatrixOps Module ====================

#[pyclass]
pub struct MatrixOps {
    #[pyo3(get)]
    pub dimension: usize,
}

#[pymethods]
impl MatrixOps {
    #[new]
    pub fn new(dimension: usize) -> Self {
        MatrixOps { dimension }
    }

    pub fn norm_l2(&self, v: Vec<f64>) -> f64 {
        v.iter().map(|x| x * x).sum::<f64>().sqrt()
    }

    pub fn softmax(&self, v: Vec<f64>) -> Vec<f64> {
        let max_val = v.iter().fold(f64::NEG_INFINITY, |a, &b| a.max(b));
        let exp_sum: f64 = v.iter().map(|x| (x - max_val).exp()).sum();
        v.iter().map(|x| ((x - max_val).exp()) / exp_sum).collect()
    }

    pub fn batch_norm_inference(&self, x: Vec<f64>, gamma: Vec<f64>, beta: Vec<f64>, running_mean: Vec<f64>, running_var: Vec<f64>, epsilon: f64) -> Vec<f64> {
        x.iter()
            .zip(running_mean.iter())
            .zip(running_var.iter())
            .zip(gamma.iter())
            .zip(beta.iter())
            .map(|((((x, mean), var), g), b)| g * ((x - mean) / (var + epsilon).sqrt()) + b)
            .collect()
    }
}

// ==================== Utility Functions ====================

#[pyfunction]
pub fn norm_l2(v: Vec<f64>) -> f64 {
    v.iter().map(|x| x * x).sum::<f64>().sqrt()
}

#[pyfunction]
pub fn softmax(v: Vec<f64>) -> Vec<f64> {
    let max_val = v.iter().fold(f64::NEG_INFINITY, |a, &b| a.max(b));
    let exp_sum: f64 = v.iter().map(|x| (x - max_val).exp()).sum();
    v.iter().map(|x| ((x - max_val).exp()) / exp_sum).collect()
}

/// Karpathy temperature-scaled softmax for leader selection
#[pyfunction]
pub fn softmax_temperature(scores: Vec<f64>, tau: f64) -> Vec<f64> {
    if scores.is_empty() {
        return vec![];
    }
    let tau_safe = tau.max(0.01);
    let scaled: Vec<f64> = scores.iter().map(|s| s / tau_safe).collect();
    let max_s = scaled.iter().fold(f64::NEG_INFINITY, |a, &b| a.max(b));
    let exp_sum: f64 = scaled.iter().map(|s| (s - max_s).exp()).sum();
    scaled.iter().map(|s| (s - max_s).exp() / exp_sum).collect()
}

/// Calculate Shannon entropy
#[pyfunction]
pub fn compute_entropy(probs: Vec<f64>) -> f64 {
    probs.iter()
        .filter(|&&p| p > 1e-10)
        .map(|&p| -p * p.ln())
        .sum()
}

/// Karpathy leader selection
#[pyfunction]
pub fn softmax_leader_selection(
    scores: Vec<f64>,
    tau: f64,
    entropy_cap: f64,
) -> (Vec<f64>, f64, bool) {
    if scores.is_empty() {
        return (vec![], 0.0, false);
    }

    let probs = softmax_temperature(scores, tau);
    let entropy = compute_entropy(probs.clone());
    let exceeded = entropy_cap > 0.0 && entropy > entropy_cap;

    (probs, entropy, exceeded)
}

/// Cosine similarity
#[pyfunction]
pub fn cosine_similarity(a: Vec<f64>, b: Vec<f64>) -> f64 {
    if a.len() != b.len() || a.is_empty() {
        return 0.0;
    }
    let dot: f64 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f64 = a.iter().map(|x| x * x).sum::<f64>().sqrt();
    let norm_b: f64 = b.iter().map(|x| x * x).sum::<f64>().sqrt();
    if norm_a < 1e-10 || norm_b < 1e-10 {
        0.0
    } else {
        dot / (norm_a * norm_b)
    }
}

#[pyfunction]
pub fn batch_norm_inference(x: Vec<f64>, gamma: Vec<f64>, beta: Vec<f64>, running_mean: Vec<f64>, running_var: Vec<f64>, epsilon: f64) -> Vec<f64> {
    x.iter()
        .zip(running_mean.iter())
        .zip(running_var.iter())
        .zip(gamma.iter())
        .zip(beta.iter())
        .map(|((((x, mean), var), g), b)| g * ((x - mean) / (var + epsilon).sqrt()) + b)
        .collect()
}


// ==================== GMD MathCore Theorems v4.4 ====================

/// Theorem 4: FWHT - Fast Walsh-Hadamard Transform
/// O(D log D) complexity, Deterministic Orthogonal Rotation
#[pyfunction]
pub fn fwht(v: Vec<f64>) -> Vec<f64> {
    let mut result = v.clone();
    fwht_inplace(&mut result);
    result
}

/// In-place FWHT for maximum performance
pub fn fwht_inplace(v: &mut [f64]) {
    let n = v.len();
    if n == 0 || (n & (n - 1)) != 0 {
        return; // D must be power of 2
    }

    let mut h = 1;
    while h < n {
        for i in (0..n).step_by(2 * h) {
            for j in i..i + h {
                let x = v[j];
                let y = v[j + h];
                v[j] = x + y;
                v[j + h] = x - y;
            }
        }
        h *= 2;
    }

    // Normalization factor 1/sqrt(D) implies orthogonality
    let scale = 1.0 / (n as f64).sqrt();
    for x in v.iter_mut() {
        *x *= scale;
    }
}

/// Theorem 1: Optimal Sparsity
/// Controls computational stability, not just collision.
/// p* ≈ 0.1 recommended for Agentic Formulation.
#[pyfunction]
pub fn compute_optimal_p(delta: f64) -> f64 {
    let delta_clamped = delta.clamp(0.0001, 0.9999);
    (1.0 + delta_clamped.sqrt()) / 2.0
}

/// Theorem 3: Optimal Ridge Regularizer for 8-bit quantization
/// λ* = σ_ε² / σ_v²
/// σ_ε² = Δ²/12 where Δ=2/255
/// σ_v² = p(1-p) for sparse vectors
/// Result: λ* ≈ 5.126e-6 / (p(1-p))
#[pyfunction]
pub fn compute_wiener_lambda(p: f64, bits: u8) -> f64 {
    let p_clamped = p.clamp(0.01, 0.99);
    // Delta = 2/255 for 8-bit [-1, 1]
    let delta = 2.0 / 255.0; // Exact formulation
    let sigma_epsilon_sq = (delta * delta) / 12.0;
    let sigma_v_sq = p_clamped * (1.0 - p_clamped);

    sigma_epsilon_sq / sigma_v_sq
}

/// Theorem 3: Quantization function Q(x) for 8-bit
/// Q(x) = (round((x+1)/2 * 255) / 255) * 2 - 1
/// Exact symmetric mapping to 256 levels
#[pyfunction]
pub fn quantize_8bit(x: f64) -> f64 {
    // Map [-1, 1] to [0, 255]
    let scaled = ((x + 1.0) / 2.0 * 255.0).round();
    let clamped = scaled.clamp(0.0, 255.0);
    // Map back to [-1, 1]
    (clamped / 255.0) * 2.0 - 1.0
}

/// Quantize entire vector
#[pyfunction]
pub fn quantize_vector(v: Vec<f64>) -> Vec<f64> {
    v.iter().map(|x| quantize_8bit(*x)).collect()
}

/// Theorem 2: Bayesian Memory with Agentic Horizon
#[pyclass]
pub struct BayesianMemory {
    #[pyo3(get)]
    pub dimension: usize,
    m: Vec<f64>,
    cov_diag: Vec<f64>,
    #[pyo3(get, set)]
    pub eta: f64,
    #[pyo3(get, set)]
    pub lambda: f64,
    #[pyo3(get)]
    pub alpha: f64,
    items_stored: usize,
}

#[pymethods]
impl BayesianMemory {
    #[new]
    #[pyo3(signature = (dimension, eta, lambda_reg))]
    pub fn new(dimension: usize, eta: f64, lambda_reg: f64) -> Self {
        BayesianMemory {
            dimension,
            m: vec![0.0; dimension],
            cov_diag: vec![0.01; dimension],
            eta: eta.clamp(0.01, 0.5),
            lambda: lambda_reg,
            alpha: 640.0, // Deprecated in v4.4 but kept for ABI compat
            items_stored: 0,
        }
    }

    /// Update with exponential decay
    /// m_t = (1-η) m_{t-1} + η b_t
    pub fn update(&mut self, binding: Vec<f64>) {
        if binding.len() != self.dimension {
            return;
        }
        let one_minus_eta = 1.0 - self.eta;
        for i in 0..self.dimension {
            self.m[i] = one_minus_eta * self.m[i] + self.eta * binding[i];
            // Covariance update is implicit in SNR model
            self.cov_diag[i] = one_minus_eta.powi(2) * self.cov_diag[i] + 1e-6;
        }
        self.items_stored += 1;
    }

    /// Theorem 3: Wiener-Optimal Unbinding (MMSE)
    /// v̂ = (Q(b) ⊙ k) / (k² + λ*)
    pub fn recall(&self, key: Vec<f64>) -> Vec<f64> {
        if key.len() != self.dimension {
            return vec![0.0; self.dimension];
        }
        let mut result = Vec::with_capacity(self.dimension);
        for i in 0..self.dimension {
            let numer = self.m[i] * key[i];
            let denom = key[i] * key[i] + self.lambda;
            result.push(numer / denom);
        }
        let norm: f64 = result.iter().map(|x| x * x).sum::<f64>().sqrt();
        if norm > 1e-10 {
            for x in result.iter_mut() {
                *x /= norm;
            }
        }
        result
    }

    /// Theorem 2: Truthful SNR Calculation
    /// SNR(L) ≈ D · w_L^2 / (W2 - w_L^2)
    /// where w_L = η(1-η)^L and W2 = η²/(2η - η²)
    pub fn compute_snr_at_lag(&self, lag: usize) -> f64 {
        let eta = self.eta;
        let w_l = eta * (1.0 - eta).powi(lag as i32);
        let w2 = (eta * eta) / (2.0 * eta - eta * eta);

        let signal_power = w_l * w_l;
        let noise_power = w2 - signal_power;

        if noise_power <= 0.0 {
            return f64::INFINITY;
        }

        (self.dimension as f64) * signal_power / noise_power
    }

    /// Agentic Horizon L*
    /// Returns the maximum lag where SNR >= snr_min
    pub fn estimate_horizon(&self, snr_min: f64) -> usize {
        // Binary search or iterative? Iterative is fast enough for horizons < 1000
        // But closed form exists approximately.
        // For exactness, we iterate.
        let mut lag = 0;
        loop {
            let snr = self.compute_snr_at_lag(lag);
            if snr < snr_min {
                return if lag > 0 { lag - 1 } else { 0 };
            }
            if lag > 10000 { // Safety break
                return 10000;
            }
            lag += 1;
        }
    }

    pub fn get_memory(&self) -> Vec<f64> {
        self.m.clone()
    }

    pub fn get_items_stored(&self) -> usize {
        self.items_stored
    }

    pub fn reset(&mut self) {
        self.m = vec![0.0; self.dimension];
        self.cov_diag = vec![0.01; self.dimension];
        self.items_stored = 0;
    }
}

/// Theorem 3: Wiener-optimal unbinding (standalone function)
#[pyfunction]
pub fn wiener_unbind(memory: Vec<f64>, key: Vec<f64>, lambda: f64) -> Vec<f64> {
    if memory.len() != key.len() {
        return vec![];
    }
    let mut result: Vec<f64> = memory.iter()
        .zip(key.iter())
        .map(|(m, k)| (m * k) / (k * k + lambda))
        .collect();
    let norm: f64 = result.iter().map(|x| x * x).sum::<f64>().sqrt();
    if norm > 1e-10 {
        for x in result.iter_mut() {
            *x /= norm;
        }
    }
    result
}
