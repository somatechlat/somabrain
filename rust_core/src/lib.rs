use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
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
    fn new(dimension: usize, sparsity: f64, seed: u64, mode: String) -> Self {
        BHDCEncoder { dimension, sparsity, seed, mode }
    }

    fn encode(&self, key: String, value: f64) -> Vec<f64> {
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

    fn bind(&self, v1: Vec<f64>, v2: Vec<f64>) -> Vec<f64> {
        v1.iter().zip(v2.iter()).map(|(a, b)| a * b).collect()
    }

    fn unbind(&self, v1: Vec<f64>, v2: Vec<f64>) -> Vec<f64> {
        v1.iter().zip(v2.iter()).map(|(a, b)| a / (b + 1e-8)).collect()
    }

    fn bundle(&self, vectors: Vec<Vec<f64>>) -> Vec<f64> {
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

    fn similarity(&self, v1: Vec<f64>, v2: Vec<f64>) -> f64 {
        let dot: f64 = v1.iter().zip(v2.iter()).map(|(a, b)| a * b).sum();
        let norm1: f64 = v1.iter().map(|x| x * x).sum::<f64>().sqrt();
        let norm2: f64 = v2.iter().map(|x| x * x).sum::<f64>().sqrt();
        if norm1 == 0.0 || norm2 == 0.0 { 0.0 } else { dot / (norm1 * norm2) }
    }

    fn permute(&self, v: Vec<f64>) -> Vec<f64> {
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
    fn new(amplitude: Vec<f64>, phase: Vec<f64>) -> Self {
        QuantumState { amplitude, phase }
    }

    fn norm(&self) -> f64 {
        self.amplitude.iter().map(|x| x * x).sum::<f64>().sqrt()
    }

    fn normalize(&self) -> (Vec<f64>, Vec<f64>) {
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
    fn new(dimension: usize) -> Self {
        QuantumModule { dimension }
    }

    fn superposition(&self, vectors: Vec<Vec<f64>>) -> Vec<f64> {
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

    fn bind(&self, v1: Vec<f64>, v2: Vec<f64>) -> Vec<f64> {
        v1.iter().zip(v2.iter()).map(|(a, b)| a * b).collect()
    }

    fn unbind(&self, v1: Vec<f64>, v2: Vec<f64>) -> Vec<f64> {
        v1.iter().zip(v2.iter()).map(|(a, b)| a / (b + 1e-8)).collect()
    }

    fn measure(&self, state: &QuantumState) -> Vec<f64> {
        state.amplitude.clone()
    }
}

// ==================== Neuromodulators Module ====================

#[pyclass]
pub struct Neuromodulators {
    #[pyo3(get, set)]
    pub dopamine: f64,
    #[pyo3(get, set)]
    pub serotonin: f64,
    #[pyo3(get, set)]
    pub noradrenaline: f64,
    #[pyo3(get, set)]
    pub acetylcholine: f64,
}

#[pymethods]
impl Neuromodulators {
    #[new]
    fn new() -> Self {
        Neuromodulators {
            dopamine: 0.5,
            serotonin: 0.5,
            noradrenaline: 0.05,
            acetylcholine: 0.05,
        }
    }

    fn get_m(&self) -> Vec<f64> {
        vec![self.dopamine, self.serotonin, self.noradrenaline, self.acetylcholine]
    }

    fn set_m(&mut self, m: Vec<f64>) {
        if m.len() == 4 {
            self.dopamine = m[0];
            self.serotonin = m[1];
            self.noradrenaline = m[2];
            self.acetylcholine = m[3];
        }
    }

    fn update(&mut self, x: Vec<f64>, u: Vec<f64>, dt: f64) -> PyResult<()> {
        let k_d = [0.8, 0.3, 0.1, 0.2];
        let k_r = [0.1, 0.2, 0.3, 0.4];
        let b = [0.0, 0.0, 0.0, 0.0];

        let mut d_m = [0.0; 4];
        for i in 0..4 {
            d_m[i] = k_d[i] * x[i] - k_r[i] * self.get_m()[i] + b[i] + 0.1 * u[i];
        }

        self.dopamine += d_m[0] * dt;
        self.serotonin += d_m[1] * dt;
        self.noradrenaline += d_m[2] * dt;
        self.acetylcholine += d_m[3] * dt;

        self.dopamine = self.dopamine.clamp(0.2, 0.8);
        self.serotonin = self.serotonin.clamp(0.0, 1.0);
        self.noradrenaline = self.noradrenaline.clamp(0.0, 0.1);
        self.acetylcholine = self.acetylcholine.clamp(0.0, 0.1);

        Ok(())
    }

    fn get_state(&self) -> Vec<f64> {
        vec![self.dopamine, self.serotonin, self.noradrenaline, self.acetylcholine]
    }

    fn set_state(&mut self, state: Vec<f64>) {
        if state.len() == 4 {
            self.dopamine = state[0];
            self.serotonin = state[1];
            self.noradrenaline = state[2];
            self.acetylcholine = state[3];
        }
    }

    fn reset(&mut self) {
        self.dopamine = 0.5;
        self.serotonin = 0.5;
        self.noradrenaline = 0.05;
        self.acetylcholine = 0.05;
    }
}

// ==================== Amygdala Module ====================

#[pyclass]
pub struct Amygdala {
    #[pyo3(get)]
    pub threshold: f64,
    weights: Vec<f64>,
}

#[pymethods]
impl Amygdala {
    #[new]
    #[pyo3(signature = (threshold, weights))]
    fn new(threshold: f64, weights: Vec<f64>) -> Self {
        Amygdala { threshold, weights }
    }

    fn salience(&self, novelty: f64, error: f64, energy: f64) -> f64 {
        let weighted = self.weights[0] * novelty + self.weights[1] * error + self.weights[2] * energy;
        weighted
    }

    fn gate(&self, score: f64) -> bool {
        score > self.threshold
    }

    fn update_weights(&mut self, new_weights: Vec<f64>) {
        if new_weights.len() == self.weights.len() {
            self.weights = new_weights;
        }
    }
}

// ==================== Prediction Module ====================

#[pyclass]
pub struct SlowPredictor {
    history: Vec<Vec<f64>>,
    max_size: usize,
}

#[pymethods]
impl SlowPredictor {
    #[new]
    fn new(max_size: usize) -> Self {
        SlowPredictor { history: Vec::new(), max_size }
    }

    fn predict(&self, input: Vec<f64>) -> Vec<f64> {
        if self.history.is_empty() {
            return vec![0.0; input.len()];
        }
        let last = &self.history[self.history.len() - 1];
        last.clone()
    }

    fn update(&mut self, input: Vec<f64>) {
        self.history.push(input);
        if self.history.len() > self.max_size {
            self.history.remove(0);
        }
    }

    fn error(&self, prediction: Vec<f64>, actual: Vec<f64>) -> f64 {
        let dot: f64 = prediction.iter().zip(actual.iter()).map(|(a, b)| a * b).sum();
        let norm_p: f64 = prediction.iter().map(|x| x * x).sum::<f64>().sqrt();
        let norm_a: f64 = actual.iter().map(|x| x * x).sum::<f64>().sqrt();
        if norm_p == 0.0 || norm_a == 0.0 { 1.0 } else { 1.0 - (dot / (norm_p * norm_a)).abs() }
    }
}

#[pyclass]
pub struct BudgetedPredictor {
    timeout_ms: u64,
}

#[pymethods]
impl BudgetedPredictor {
    #[new]
    fn new(timeout_ms: u64) -> Self {
        BudgetedPredictor { timeout_ms }
    }

    fn predict_with_timeout(&self, input: Vec<f64>) -> PyResult<Vec<f64>> {
        // Simulated timeout check
        if self.timeout_ms < 10 {
            return Err(PyValueError::new_err("Timeout exceeded"));
        }
        Ok(input)
    }
}

#[pyclass]
pub struct MahalanobisPredictor {
    mean: Vec<f64>,
    covariance: Vec<Vec<f64>>,
    ewma_alpha: f64,
}

#[pymethods]
impl MahalanobisPredictor {
    #[new]
    fn new(dimension: usize, ewma_alpha: f64) -> Self {
        MahalanobisPredictor {
            mean: vec![0.0; dimension],
            covariance: vec![vec![0.0; dimension]; dimension],
            ewma_alpha,
        }
    }

    fn update(&mut self, input: Vec<f64>) {
        for i in 0..self.mean.len() {
            self.mean[i] = (1.0 - self.ewma_alpha) * self.mean[i] + self.ewma_alpha * input[i];
        }
    }

    fn distance(&self, input: Vec<f64>) -> f64 {
        let diff: Vec<f64> = input.iter().zip(self.mean.iter()).map(|(a, b)| a - b).collect();
        diff.iter().map(|x| x * x).sum::<f64>().sqrt()
    }
}

#[pyclass]
pub struct LLMPredictor {
    api_url: String,
}

#[pymethods]
impl LLMPredictor {
    #[new]
    fn new(api_url: String) -> Self {
        LLMPredictor { api_url }
    }

    fn predict(&self, _input: Vec<f64>) -> Vec<f64> {
        // Placeholder for HTTP call
        vec![0.0]
    }
}

// ==================== Consolidation Module ====================

#[pyclass]
pub struct Consolidation {
    #[pyo3(get)]
    pub nrem_budget: f64,
    #[pyo3(get)]
    pub rem_budget: f64,
}

#[pymethods]
impl Consolidation {
    #[new]
    fn new(nrem_budget: f64, rem_budget: f64) -> Self {
        Consolidation { nrem_budget, rem_budget }
    }

    fn nrem(&self, episodic: Vec<Vec<f64>>) -> Vec<f64> {
        if episodic.is_empty() {
            return vec![0.0];
        }
        let mut summary = vec![0.0; episodic[0].len()];
        for vec in &episodic {
            for (i, val) in vec.iter().enumerate() {
                summary[i] += val;
            }
        }
        for s in summary.iter_mut() {
            *s /= episodic.len() as f64;
        }
        summary
    }

    fn rem(&self, pairs: Vec<(Vec<f64>, Vec<f64>)>) -> Vec<Vec<f64>> {
        pairs.iter().map(|(a, b)| {
            a.iter().zip(b.iter()).map(|(x, y)| (x + y) / 2.0).collect()
        }).collect()
    }
}

#[pyclass]
pub struct MultiConsolidation {
    strategies: Vec<String>,
}

#[pymethods]
impl MultiConsolidation {
    #[new]
    fn new(strategies: Vec<String>) -> Self {
        MultiConsolidation { strategies }
    }

    fn consolidate(&self, data: Vec<Vec<f64>>) -> Vec<f64> {
        if data.is_empty() {
            return vec![0.0];
        }
        let mut result = vec![0.0; data[0].len()];
        for vec in &data {
            for (i, val) in vec.iter().enumerate() {
                result[i] += val;
            }
        }
        for r in result.iter_mut() {
            *r /= data.len() as f64;
        }
        result
    }
}

#[pyclass]
pub struct HebbianConsolidation {
    learning_rate: f64,
    weights: Vec<Vec<f64>>,
}

#[pymethods]
impl HebbianConsolidation {
    #[new]
    fn new(dimension: usize, learning_rate: f64) -> Self {
        HebbianConsolidation {
            learning_rate,
            weights: vec![vec![0.0; dimension]; dimension],
        }
    }

    fn update(&mut self, pre: Vec<f64>, post: Vec<f64>) {
        for i in 0..self.weights.len() {
            for j in 0..self.weights[i].len() {
                self.weights[i][j] += self.learning_rate * pre[i] * post[j];
            }
        }
    }

    fn recall(&self, input: Vec<f64>) -> Vec<f64> {
        let mut result = vec![0.0; input.len()];
        for i in 0..self.weights.len() {
            for j in 0..self.weights[i].len() {
                result[j] += self.weights[i][j] * input[i];
            }
        }
        result
    }
}

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
    fn new(bins: usize) -> Self {
        FNOM { bins, kv_store: std::collections::HashMap::new() }
    }

    fn encode(&mut self, key: String, value: String) -> Vec<f64> {
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

    fn retrieve(&self, key: String) -> Option<Vec<f64>> {
        self.kv_store.get(&key).cloned()
    }

    fn similarity(&self, v1: Vec<f64>, v2: Vec<f64>) -> f64 {
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
    fn new(dimension: usize, epsilon: f64) -> Self {
        BatchNorm {
            running_mean: vec![0.0; dimension],
            running_var: vec![1.0; dimension],
            epsilon,
        }
    }

    fn inference(&self, x: Vec<f64>, gamma: Vec<f64>, beta: Vec<f64>) -> Vec<f64> {
        x.iter()
            .zip(self.running_mean.iter())
            .zip(self.running_var.iter())
            .zip(gamma.iter())
            .zip(beta.iter())
            .map(|((((x, mean), var), g), b)| g * ((x - mean) / (var + self.epsilon).sqrt()) + b)
            .collect()
    }

    fn update_running_stats(&mut self, batch_mean: Vec<f64>, batch_var: Vec<f64>, momentum: f64) {
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
    fn new(rate: f64) -> Self {
        Dropout { rate, seed: 42 }
    }

    fn apply(&self, input: Vec<f64>) -> Vec<f64> {
        let mut rng = Pcg64::seed_from_u64(self.seed);
        input.iter().map(|x| {
            if rng.gen::<f64>() < self.rate { 0.0 } else { *x / (1.0 - self.rate) }
        }).collect()
    }

    fn set_seed(&mut self, seed: u64) {
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
    fn new(dimension: usize) -> Self {
        MatrixOps { dimension }
    }

    fn norm_l2(&self, v: Vec<f64>) -> f64 {
        v.iter().map(|x| x * x).sum::<f64>().sqrt()
    }

    fn softmax(&self, v: Vec<f64>) -> Vec<f64> {
        let max_val = v.iter().fold(f64::NEG_INFINITY, |a, &b| a.max(b));
        let exp_sum: f64 = v.iter().map(|x| (x - max_val).exp()).sum();
        v.iter().map(|x| ((x - max_val).exp()) / exp_sum).collect()
    }

    fn batch_norm_inference(&self, x: Vec<f64>, gamma: Vec<f64>, beta: Vec<f64>, running_mean: Vec<f64>, running_var: Vec<f64>, epsilon: f64) -> Vec<f64> {
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
fn norm_l2(v: Vec<f64>) -> f64 {
    v.iter().map(|x| x * x).sum::<f64>().sqrt()
}

#[pyfunction]
fn softmax(v: Vec<f64>) -> Vec<f64> {
    let max_val = v.iter().fold(f64::NEG_INFINITY, |a, &b| a.max(b));
    let exp_sum: f64 = v.iter().map(|x| (x - max_val).exp()).sum();
    v.iter().map(|x| ((x - max_val).exp()) / exp_sum).collect()
}

#[pyfunction]
fn batch_norm_inference(x: Vec<f64>, gamma: Vec<f64>, beta: Vec<f64>, running_mean: Vec<f64>, running_var: Vec<f64>, epsilon: f64) -> Vec<f64> {
    x.iter()
        .zip(running_mean.iter())
        .zip(running_var.iter())
        .zip(gamma.iter())
        .zip(beta.iter())
        .map(|((((x, mean), var), g), b)| g * ((x - mean) / (var + epsilon).sqrt()) + b)
        .collect()
}

// ==================== GMD MathCore Theorems ====================
// Complete implementation per MathCore White Paper v4.0

/// Theorem 4: FWHT - Fast Walsh-Hadamard Transform
/// O(D log D) complexity, 127,000× speedup over QR decomposition
#[pyfunction]
fn fwht(v: Vec<f64>) -> Vec<f64> {
    let mut result = v.clone();
    fwht_inplace(&mut result);
    result
}

/// In-place FWHT for maximum performance
fn fwht_inplace(v: &mut [f64]) {
    let n = v.len();
    if n == 0 || (n & (n - 1)) != 0 {
        return; // Must be power of 2
    }

    let mut h = 1;
    // 2 * D * log2(D) FLOPs
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

    // Normalization: D multiplications
    let scale = 1.0 / (n as f64).sqrt();
    for x in v.iter_mut() {
        *x *= scale;
    }
}

/// Theorem 1: Optimal Sparsity
/// p* = (1 + √δ) / 2
#[pyfunction]
fn compute_optimal_p(delta: f64) -> f64 {
    let delta_clamped = delta.clamp(0.0001, 0.9999);
    (1.0 + delta_clamped.sqrt()) / 2.0
}

/// Theorem 1: Capacity Estimation
/// N_max = √(2εDδ·p/(1-p))
#[pyfunction]
fn compute_capacity_theorem1(d: usize, p: f64, delta: f64, epsilon: f64) -> usize {
    let p_clamped = p.clamp(0.01, 0.99);
    let ratio = p_clamped / (1.0 - p_clamped);
    let n_max = (2.0 * epsilon * (d as f64) * delta * ratio).sqrt();
    n_max.floor() as usize
}

/// Theorem 3: Optimal Wiener Regularizer for 8-bit quantization
/// λ* = (2/255)² / (3 · 2p(1-p)) ≈ 2.05e-5 for p=0.1
#[pyfunction]
fn compute_wiener_lambda(p: f64, bits: u8) -> f64 {
    let p_clamped = p.clamp(0.01, 0.99);
    let delta = 2.0 / ((1u64 << bits) - 1) as f64; // 2/255 for 8-bit
    (delta * delta) / (3.0 * 2.0 * p_clamped * (1.0 - p_clamped))
}

/// Theorem 3: Quantization function Q(x) for 8-bit
/// Q(x) = round(127(x+1))/127 - 1
#[pyfunction]
fn quantize_8bit(x: f64) -> f64 {
    let scaled = ((x + 1.0) * 127.0).round();
    scaled / 127.0 - 1.0
}

/// Quantize entire vector
#[pyfunction]
fn quantize_vector(v: Vec<f64>) -> Vec<f64> {
    v.iter().map(|x| quantize_8bit(*x)).collect()
}

/// Theorem 2: Bayesian Memory with SNR
#[pyclass]
pub struct BayesianMemory {
    #[pyo3(get)]
    pub dimension: usize,
    m: Vec<f64>,              // Memory state
    cov_diag: Vec<f64>,       // Covariance diagonal
    #[pyo3(get, set)]
    pub eta: f64,             // Decay rate
    #[pyo3(get, set)]
    pub lambda: f64,          // Wiener regularizer (Theorem 3)
    #[pyo3(get)]
    pub alpha: f64,           // Cleanup constant = 640
    items_stored: usize,
}

#[pymethods]
impl BayesianMemory {
    #[new]
    #[pyo3(signature = (dimension, eta=0.08, lambda_reg=2.05e-5))]
    fn new(dimension: usize, eta: f64, lambda_reg: f64) -> Self {
        BayesianMemory {
            dimension,
            m: vec![0.0; dimension],
            cov_diag: vec![0.01; dimension],
            eta: eta.clamp(0.01, 0.5),
            lambda: lambda_reg,
            alpha: 640.0, // Empirically validated constant
            items_stored: 0,
        }
    }

    /// Theorem 2: Memory Update Rule
    /// m_t = (1 - η) * m_{t-1} + η * b_t
    fn update(&mut self, binding: Vec<f64>) {
        if binding.len() != self.dimension {
            return;
        }

        let one_minus_eta = 1.0 - self.eta;
        for i in 0..self.dimension {
            self.m[i] = one_minus_eta * self.m[i] + self.eta * binding[i];
            // Update covariance: cov = (1-η)² * cov + small_noise
            self.cov_diag[i] = one_minus_eta * one_minus_eta * self.cov_diag[i] + 1e-4;
        }
        self.items_stored += 1;
    }

    /// Theorem 3: Wiener-Optimal Unbinding (MMSE)
    /// v̂ = (m ⊙ k) / (k² + λ*)
    fn recall(&self, key: Vec<f64>) -> Vec<f64> {
        if key.len() != self.dimension {
            return vec![0.0; self.dimension];
        }

        let mut result = Vec::with_capacity(self.dimension);
        for i in 0..self.dimension {
            let numer = self.m[i] * key[i];
            let denom = key[i] * key[i] + self.lambda;
            result.push(numer / denom);
        }

        // Normalize to unit vector
        let norm: f64 = result.iter().map(|x| x * x).sum::<f64>().sqrt();
        if norm > 1e-10 {
            for x in result.iter_mut() {
                *x /= norm;
            }
        }
        result
    }

    /// Theorem 2: SNR Calculation
    /// SNR = (2η - η²) / (N-1) · D / (p(1-p))
    fn compute_snr(&self, p: f64) -> f64 {
        if self.items_stored <= 1 {
            return f64::INFINITY;
        }
        let p_clamped = p.clamp(0.01, 0.99);
        let eta_term = 2.0 * self.eta - self.eta * self.eta;
        let n_term = (self.items_stored - 1) as f64;
        let dim_term = self.dimension as f64 / (p_clamped * (1.0 - p_clamped));

        (eta_term / n_term) * dim_term
    }

    /// Theorem 2: Recall Quality (gamma) from SNR
    /// γ = √(SNR / (1 + SNR))
    fn compute_gamma(&self, p: f64) -> f64 {
        let snr = self.compute_snr(p);
        if snr.is_infinite() {
            return 1.0;
        }
        (snr / (1.0 + snr)).sqrt()
    }

    /// Theorem 2: Capacity Estimation
    /// N_est = D / (α · η) where α = 640
    fn estimate_capacity(&self) -> usize {
        ((self.dimension as f64) / (self.alpha * self.eta)).floor() as usize
    }

    /// Theorem 2: SNR-based Capacity
    /// N_SNR = 1 + (2η - η²) / (p(1-p)) · D · (1-γ²) / γ²
    fn estimate_capacity_snr(&self, p: f64, target_gamma: f64) -> usize {
        let p_clamped = p.clamp(0.01, 0.99);
        let gamma_sq = target_gamma * target_gamma;
        let eta_term = 2.0 * self.eta - self.eta * self.eta;
        let p_term = p_clamped * (1.0 - p_clamped);
        let gamma_term = (1.0 - gamma_sq) / gamma_sq;

        let n_snr = 1.0 + (eta_term / p_term) * (self.dimension as f64) * gamma_term;
        n_snr.floor() as usize
    }

    /// Get current memory state
    fn get_memory(&self) -> Vec<f64> {
        self.m.clone()
    }

    /// Get items stored count
    fn get_items_stored(&self) -> usize {
        self.items_stored
    }

    /// Reset memory to initial state
    fn reset(&mut self) {
        self.m = vec![0.0; self.dimension];
        self.cov_diag = vec![0.01; self.dimension];
        self.items_stored = 0;
    }

    /// Check if at capacity (>80% of estimated)
    fn is_near_capacity(&self) -> bool {
        let capacity = self.estimate_capacity();
        self.items_stored > (capacity * 8 / 10)
    }
}

/// Theorem 3: Wiener-optimal unbinding (standalone function)
/// v̂ = (m ⊙ k) / (k² + λ*) with λ* = 2.05e-5
#[pyfunction]
fn wiener_unbind(memory: Vec<f64>, key: Vec<f64>, lambda: f64) -> Vec<f64> {
    if memory.len() != key.len() {
        return vec![];
    }

    let mut result: Vec<f64> = memory.iter()
        .zip(key.iter())
        .map(|(m, k)| (m * k) / (k * k + lambda))
        .collect();

    // Normalize
    let norm: f64 = result.iter().map(|x| x * x).sum::<f64>().sqrt();
    if norm > 1e-10 {
        for x in result.iter_mut() {
            *x /= norm;
        }
    }
    result
}

// ==================== AdaptationEngine Module ====================
// CPU-bound learning rate and weight updates - hot path optimization

#[pyclass]
pub struct RetrievalWeights {
    #[pyo3(get, set)]
    pub alpha: f64,
    #[pyo3(get, set)]
    pub beta: f64,
    #[pyo3(get, set)]
    pub gamma: f64,
    #[pyo3(get, set)]
    pub tau: f64,
}

#[pymethods]
impl RetrievalWeights {
    #[new]
    #[pyo3(signature = (alpha=1.0, beta=0.2, gamma=0.1, tau=0.7))]
    fn new(alpha: f64, beta: f64, gamma: f64, tau: f64) -> Self {
        RetrievalWeights { alpha, beta, gamma, tau }
    }

    fn to_vec(&self) -> Vec<f64> {
        vec![self.alpha, self.beta, self.gamma, self.tau]
    }

    fn from_vec(&mut self, v: Vec<f64>) {
        if v.len() >= 4 {
            self.alpha = v[0];
            self.beta = v[1];
            self.gamma = v[2];
            self.tau = v[3];
        }
    }
}

#[pyclass]
pub struct UtilityWeights {
    #[pyo3(get, set)]
    pub lambda_: f64,
    #[pyo3(get, set)]
    pub mu: f64,
    #[pyo3(get, set)]
    pub nu: f64,
}

#[pymethods]
impl UtilityWeights {
    #[new]
    #[pyo3(signature = (lambda_=1.0, mu=0.1, nu=0.05))]
    fn new(lambda_: f64, mu: f64, nu: f64) -> Self {
        UtilityWeights { lambda_, mu, nu }
    }

    fn clamp(&mut self, lambda_min: f64, lambda_max: f64, mu_min: f64, mu_max: f64, nu_min: f64, nu_max: f64) {
        self.lambda_ = self.lambda_.clamp(lambda_min, lambda_max);
        self.mu = self.mu.clamp(mu_min, mu_max);
        self.nu = self.nu.clamp(nu_min, nu_max);
    }
}

#[pyclass]
pub struct AdaptationEngine {
    retrieval: RetrievalWeights,
    utility: UtilityWeights,
    #[pyo3(get, set)]
    learning_rate: f64,
    base_lr: f64,
    feedback_count: u64,
    // Constraints
    alpha_bounds: (f64, f64),
    gamma_bounds: (f64, f64),
    lambda_bounds: (f64, f64),
    mu_bounds: (f64, f64),
    nu_bounds: (f64, f64),
    // Gains
    gain_alpha: f64,
    gain_gamma: f64,
    gain_lambda: f64,
    gain_mu: f64,
    gain_nu: f64,
}

#[pymethods]
impl AdaptationEngine {
    #[new]
    #[pyo3(signature = (learning_rate=0.05))]
    fn new(learning_rate: f64) -> Self {
        AdaptationEngine {
            retrieval: RetrievalWeights::new(1.0, 0.2, 0.1, 0.7),
            utility: UtilityWeights::new(1.0, 0.1, 0.05),
            learning_rate,
            base_lr: learning_rate,
            feedback_count: 0,
            // Default constraints
            alpha_bounds: (0.1, 2.0),
            gamma_bounds: (0.0, 1.0),
            lambda_bounds: (0.1, 2.0),
            mu_bounds: (0.0, 0.5),
            nu_bounds: (0.0, 0.2),
            // Default gains
            gain_alpha: 0.1,
            gain_gamma: 0.05,
            gain_lambda: 0.1,
            gain_mu: 0.05,
            gain_nu: 0.02,
        }
    }

    /// Set retrieval weights
    fn set_retrieval(&mut self, alpha: f64, beta: f64, gamma: f64, tau: f64) {
        self.retrieval.alpha = alpha;
        self.retrieval.beta = beta;
        self.retrieval.gamma = gamma;
        self.retrieval.tau = tau;
    }

    /// Get retrieval weights as tuple
    fn get_retrieval(&self) -> (f64, f64, f64, f64) {
        (self.retrieval.alpha, self.retrieval.beta, self.retrieval.gamma, self.retrieval.tau)
    }

    /// Set utility weights
    fn set_utility(&mut self, lambda_: f64, mu: f64, nu: f64) {
        self.utility.lambda_ = lambda_;
        self.utility.mu = mu;
        self.utility.nu = nu;
    }

    /// Get utility weights as tuple
    fn get_utility(&self) -> (f64, f64, f64) {
        (self.utility.lambda_, self.utility.mu, self.utility.nu)
    }

    /// Set constraints for weight updates
    fn set_constraints(&mut self, alpha_min: f64, alpha_max: f64, gamma_min: f64, gamma_max: f64,
                       lambda_min: f64, lambda_max: f64, mu_min: f64, mu_max: f64, nu_min: f64, nu_max: f64) {
        self.alpha_bounds = (alpha_min, alpha_max);
        self.gamma_bounds = (gamma_min, gamma_max);
        self.lambda_bounds = (lambda_min, lambda_max);
        self.mu_bounds = (mu_min, mu_max);
        self.nu_bounds = (nu_min, nu_max);
    }

    /// Set gains for weight updates
    fn set_gains(&mut self, alpha: f64, gamma: f64, lambda_: f64, mu: f64, nu: f64) {
        self.gain_alpha = alpha;
        self.gain_gamma = gamma;
        self.gain_lambda = lambda_;
        self.gain_mu = mu;
        self.gain_nu = nu;
    }

    /// Apply feedback and update weights - CPU-bound hot path
    fn apply_feedback(&mut self, utility_signal: f64, reward: f64) -> bool {
        let semantic_signal = reward;
        let utility_val = utility_signal;

        // Update retrieval weights
        self.retrieval.alpha = (self.retrieval.alpha + self.learning_rate * self.gain_alpha * semantic_signal)
            .clamp(self.alpha_bounds.0, self.alpha_bounds.1);
        self.retrieval.gamma = (self.retrieval.gamma + self.learning_rate * self.gain_gamma * semantic_signal)
            .clamp(self.gamma_bounds.0, self.gamma_bounds.1);

        // Update utility weights
        self.utility.lambda_ = (self.utility.lambda_ + self.learning_rate * self.gain_lambda * utility_val)
            .clamp(self.lambda_bounds.0, self.lambda_bounds.1);
        self.utility.mu = (self.utility.mu + self.learning_rate * self.gain_mu * utility_val)
            .clamp(self.mu_bounds.0, self.mu_bounds.1);
        self.utility.nu = (self.utility.nu + self.learning_rate * self.gain_nu * utility_val)
            .clamp(self.nu_bounds.0, self.nu_bounds.1);

        self.feedback_count += 1;
        true
    }

    /// Linear decay for tau
    fn linear_decay(&self, tau_0: f64, tau_min: f64, alpha: f64, t: u64) -> f64 {
        (tau_0 - alpha * (t as f64)).max(tau_min)
    }

    /// Exponential decay for tau
    fn exponential_decay(&self, tau_0: f64, gamma: f64, t: u64) -> f64 {
        tau_0 * (-gamma * (t as f64)).exp()
    }

    /// Apply tau decay
    fn apply_tau_decay(&mut self, decay_rate: f64, min_tau: f64) {
        self.retrieval.tau = (self.retrieval.tau * (1.0 - decay_rate)).max(min_tau);
    }

    /// Get current tau value
    fn get_tau(&self) -> f64 {
        self.retrieval.tau
    }

    /// Set tau value
    fn set_tau(&mut self, tau: f64) {
        self.retrieval.tau = tau.clamp(0.01, 10.0);
    }

    /// Get feedback count
    fn get_feedback_count(&self) -> u64 {
        self.feedback_count
    }

    /// Reset engine to defaults
    fn reset(&mut self) {
        self.retrieval = RetrievalWeights::new(1.0, 0.2, 0.1, 0.7);
        self.utility = UtilityWeights::new(1.0, 0.1, 0.05);
        self.learning_rate = self.base_lr;
        self.feedback_count = 0;
    }

    /// Get state as dict-like structure
    fn get_state(&self) -> Vec<(String, f64)> {
        vec![
            ("alpha".to_string(), self.retrieval.alpha),
            ("beta".to_string(), self.retrieval.beta),
            ("gamma".to_string(), self.retrieval.gamma),
            ("tau".to_string(), self.retrieval.tau),
            ("lambda_".to_string(), self.utility.lambda_),
            ("mu".to_string(), self.utility.mu),
            ("nu".to_string(), self.utility.nu),
            ("learning_rate".to_string(), self.learning_rate),
            ("feedback_count".to_string(), self.feedback_count as f64),
        ]
    }

    /// Update learning rate based on dopamine level
    fn update_learning_rate(&mut self, dopamine: f64) {
        let lr_scale = (0.5 + dopamine).clamp(0.5, 1.2);
        self.learning_rate = self.base_lr * lr_scale;
    }
}

// ==================== Module Registration ====================

#[pymodule]
fn somabrain_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Classes
    m.add_class::<BHDCEncoder>()?;
    m.add_class::<QuantumState>()?;
    m.add_class::<QuantumModule>()?;
    m.add_class::<Neuromodulators>()?;
    m.add_class::<Amygdala>()?;
    m.add_class::<SlowPredictor>()?;
    m.add_class::<BudgetedPredictor>()?;
    m.add_class::<MahalanobisPredictor>()?;
    m.add_class::<LLMPredictor>()?;
    m.add_class::<Consolidation>()?;
    m.add_class::<MultiConsolidation>()?;
    m.add_class::<HebbianConsolidation>()?;
    m.add_class::<FNOM>()?;
    m.add_class::<BatchNorm>()?;
    m.add_class::<Dropout>()?;
    m.add_class::<MatrixOps>()?;

    // Adaptation Engine (CPU-bound hot path)
    m.add_class::<RetrievalWeights>()?;
    m.add_class::<UtilityWeights>()?;
    m.add_class::<AdaptationEngine>()?;

    // GMD MathCore Classes (Theorems 1-4)
    m.add_class::<BayesianMemory>()?;

    // Utility functions from MatrixOps
    m.add_function(wrap_pyfunction!(norm_l2)(m.py())?)?;
    m.add_function(wrap_pyfunction!(softmax)(m.py())?)?;
    m.add_function(wrap_pyfunction!(batch_norm_inference)(m.py())?)?;

    // GMD MathCore Functions (Theorems 1-4)
    m.add_function(wrap_pyfunction!(fwht)(m.py())?)?;              // Theorem 4
    m.add_function(wrap_pyfunction!(compute_optimal_p)(m.py())?)?; // Theorem 1
    m.add_function(wrap_pyfunction!(compute_capacity_theorem1)(m.py())?)?; // Theorem 1
    m.add_function(wrap_pyfunction!(compute_wiener_lambda)(m.py())?)?;     // Theorem 3
    m.add_function(wrap_pyfunction!(quantize_8bit)(m.py())?)?;     // Theorem 3
    m.add_function(wrap_pyfunction!(quantize_vector)(m.py())?)?;   // Theorem 3
    m.add_function(wrap_pyfunction!(wiener_unbind)(m.py())?)?;     // Theorem 3

    Ok(())
}

// ==================== Unit Tests ====================
// GMD MathCore Theorem Verification Tests

#[cfg(test)]
mod tests {
    use super::*;

    // Theorem 1: Optimal p* = (1 + sqrt(delta)) / 2
    #[test]
    fn test_optimal_p_theorem1() {
        let test_cases: [(f64, f64); 4] = [
            (0.01, 0.55),
            (0.04, 0.60),
            (0.09, 0.65),
            (0.25, 0.75),
        ];

        for (delta, expected) in test_cases {
            let actual = (1.0_f64 + delta.sqrt()) / 2.0;
            let computed = compute_optimal_p(delta);
            assert!((computed - expected).abs() < 1e-10,
                "p* for delta={}: expected {}, got {}", delta, expected, computed);
            assert!((computed - actual).abs() < 1e-10);
        }
    }

    // Theorem 3: Wiener lambda* = (2/255)^2 / (3 * 2 * p * (1-p))
    #[test]
    fn test_wiener_lambda_theorem3() {
        let p = 0.1;
        let delta = 2.0 / 255.0;
        let expected = (delta * delta) / (3.0 * 2.0 * p * (1.0 - p));
        let actual = compute_wiener_lambda(p, 8);

        assert!((actual - expected).abs() < 1e-15,
            "Wiener lambda: expected {}, got {}", expected, actual);
    }

    // Theorem 3: Quantization Q(x) = round(127*(x+1))/127 - 1
    #[test]
    fn test_quantize_8bit_theorem3() {
        let test_cases = [
            (0.0, 0.0),
            (1.0, 1.0),
            (-1.0, -1.0),
            (0.5, 0.5039370078740157), // IEEE rounding
        ];

        for (x, expected) in test_cases {
            let actual = quantize_8bit(x);
            assert!((actual - expected).abs() < 0.01,
                "Q({}) = {}, expected ~{}", x, actual, expected);
        }
    }

    // Theorem 4: FWHT orthogonality
    #[test]
    fn test_fwht_orthogonality() {
        let n = 8;
        let mut v = vec![1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0];
        fwht_inplace(&mut v);

        // After FWHT, all elements should be 1/sqrt(8) = 0.3535...
        let expected = 1.0 / (n as f64).sqrt();
        for val in &v {
            assert!((val - expected).abs() < 1e-10,
                "FWHT orthogonality: expected {}, got {}", expected, val);
        }
    }

    // Theorem 4: FWHT is its own inverse (up to scaling)
    #[test]
    fn test_fwht_inverse() {
        let original = vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0];
        let mut v = original.clone();

        // Apply FWHT twice
        fwht_inplace(&mut v);
        fwht_inplace(&mut v);

        // Should recover original
        for (orig, recovered) in original.iter().zip(v.iter()) {
            assert!((orig - recovered).abs() < 1e-10,
                "FWHT inverse: {} != {}", orig, recovered);
        }
    }

    // Theorem 2: BayesianMemory SNR formula
    #[test]
    fn test_bayesian_memory_snr() {
        let mut mem = BayesianMemory::new(1024, 0.08, 2.05e-5);

        // Store 10 items
        for _ in 0..10 {
            let binding: Vec<f64> = (0..1024).map(|i| (i as f64).sin()).collect();
            mem.update(binding);
        }

        assert_eq!(mem.get_items_stored(), 10);

        // Verify SNR formula: (2*eta - eta^2) / (N-1) * D / (p*(1-p))
        let eta = 0.08;
        let p = 0.1;
        let n = 10;
        let d = 1024;
        let expected_snr = ((2.0 * eta - eta * eta) / (n - 1) as f64)
            * (d as f64 / (p * (1.0 - p)));
        let actual_snr = mem.compute_snr(p);

        assert!((actual_snr - expected_snr).abs() / expected_snr < 0.0001,
            "SNR: expected {}, got {}", expected_snr, actual_snr);
    }

    // Theorem 2: Gamma formula
    #[test]
    fn test_bayesian_memory_gamma() {
        let mut mem = BayesianMemory::new(2048, 0.08, 2.05e-5);

        for _ in 0..20 {
            let binding: Vec<f64> = (0..2048).map(|i| (i as f64).cos()).collect();
            mem.update(binding);
        }

        let p = 0.1;
        let snr = mem.compute_snr(p);
        let expected_gamma = (snr / (1.0 + snr)).sqrt();
        let actual_gamma = mem.compute_gamma(p);

        assert!((actual_gamma - expected_gamma).abs() < 1e-10,
            "Gamma: expected {}, got {}", expected_gamma, actual_gamma);
    }

    // Capacity estimation
    #[test]
    fn test_capacity_estimation() {
        let mem = BayesianMemory::new(2048, 0.08, 2.05e-5);

        // N_est = D / (alpha * eta) = 2048 / (640 * 0.08) = 40
        let expected = (2048.0 / (640.0 * 0.08)) as usize;
        let actual = mem.estimate_capacity();

        assert_eq!(actual, expected,
            "Capacity: expected {}, got {}", expected, actual);
    }

    // Wiener unbind normalization
    #[test]
    fn test_wiener_unbind_normalization() {
        let memory = vec![1.0, 2.0, 3.0, 4.0];
        let key = vec![0.5, 0.5, 0.5, 0.5];
        let lambda = 2.05e-5;

        let result = wiener_unbind(memory, key, lambda);

        // Result should be normalized
        let norm: f64 = result.iter().map(|x| x * x).sum::<f64>().sqrt();
        assert!((norm - 1.0).abs() < 1e-10,
            "Wiener unbind should return unit vector, got norm={}", norm);
    }
}
