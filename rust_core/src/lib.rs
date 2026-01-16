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

    // Utility functions from MatrixOps
    m.add_function(wrap_pyfunction!(norm_l2)(m.py())?)?;
    m.add_function(wrap_pyfunction!(softmax)(m.py())?)?;
    m.add_function(wrap_pyfunction!(batch_norm_inference)(m.py())?)?;

    Ok(())
}
