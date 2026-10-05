//! Prediction and Consolidation modules.
//!
//! Part of GMD MathCore implementation.

use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;

// ==================== Prediction Module ====================

#[pyclass]
pub struct SlowPredictor {
    history: Vec<Vec<f64>>,
    max_size: usize,
}

#[pymethods]
impl SlowPredictor {
    #[new]
    pub fn new(max_size: usize) -> Self {
        SlowPredictor { history: Vec::new(), max_size }
    }

    pub fn predict(&self, input: Vec<f64>) -> Vec<f64> {
        if self.history.is_empty() {
            return vec![0.0; input.len()];
        }
        self.history[self.history.len() - 1].clone()
    }

    pub fn update(&mut self, input: Vec<f64>) {
        self.history.push(input);
        if self.history.len() > self.max_size {
            self.history.remove(0);
        }
    }

    /// Cosine error `clamp(1 − cos(prediction, actual), 0, 1)`.
    ///
    /// Matches `somabrain.math.similarity.cosine_error`: opposite vectors
    /// (cos = −1) are maximum error 1.0, never 0.0. No absolute value.
    pub fn error(&self, prediction: Vec<f64>, actual: Vec<f64>) -> f64 {
        let dot: f64 = prediction.iter().zip(actual.iter()).map(|(a, b)| a * b).sum();
        let norm_p: f64 = prediction.iter().map(|x| x * x).sum::<f64>().sqrt();
        let norm_a: f64 = actual.iter().map(|x| x * x).sum::<f64>().sqrt();
        if norm_p == 0.0 || norm_a == 0.0 {
            return 1.0;
        }
        let cos = (dot / (norm_p * norm_a)).clamp(-1.0, 1.0);
        (1.0 - cos).clamp(0.0, 1.0)
    }
}

#[pyclass]
pub struct BudgetedPredictor {
    timeout_ms: u64,
}

#[pymethods]
impl BudgetedPredictor {
    #[new]
    pub fn new(timeout_ms: u64) -> Self {
        BudgetedPredictor { timeout_ms }
    }

    pub fn predict_with_timeout(&self, input: Vec<f64>) -> PyResult<Vec<f64>> {
        if self.timeout_ms < 10 {
            return Err(PyValueError::new_err("Timeout exceeded"));
        }
        Ok(input)
    }
}

/// Online diagonal Mahalanobis predictor.
///
/// Tracks an EWMA mean `μ` and diagonal variance `σ²` and scores inputs with
/// the true diagonal Mahalanobis distance
/// `d(x) = sqrt(Σ_i (x_i − μ_i)² / σ_i²)`.
#[pyclass]
pub struct MahalanobisPredictor {
    #[pyo3(get)]
    pub mean: Vec<f64>,
    /// Diagonal variance σ²_i (EWMA), floored at 1e-6.
    #[pyo3(get)]
    pub var: Vec<f64>,
    ewma_alpha: f64,
    initialized: bool,
}

#[pymethods]
impl MahalanobisPredictor {
    #[new]
    pub fn new(dimension: usize, ewma_alpha: f64) -> Self {
        MahalanobisPredictor {
            mean: vec![0.0; dimension],
            var: vec![0.1; dimension],
            ewma_alpha,
            initialized: false,
        }
    }

    /// EWMA update of the online mean and diagonal variance.
    ///
    /// First sample initialises `μ = x`, `σ² = 0.1`. Afterwards:
    /// `μ ← (1−α)μ + αx`, `σ² ← (1−α)σ² + α(x−μ)²`, `σ² ≥ 1e-6`.
    pub fn update(&mut self, input: Vec<f64>) -> PyResult<()> {
        if input.len() != self.mean.len() {
            return Err(PyValueError::new_err(format!(
                "input length {} does not match dimension {}",
                input.len(),
                self.mean.len()
            )));
        }
        if !self.initialized {
            self.mean.copy_from_slice(&input);
            for v in self.var.iter_mut() {
                *v = 0.1;
            }
            self.initialized = true;
            return Ok(());
        }
        let a = self.ewma_alpha;
        for i in 0..self.mean.len() {
            let mu_new = (1.0 - a) * self.mean[i] + a * input[i];
            let diff = input[i] - mu_new;
            let var_new = (1.0 - a) * self.var[i] + a * (diff * diff);
            self.mean[i] = mu_new;
            self.var[i] = var_new.max(1e-6);
        }
        Ok(())
    }

    /// Diagonal Mahalanobis distance `sqrt((x−μ)ᵀ Σ⁻¹ (x−μ))` with
    /// `Σ = diag(σ²)`. Before the first `update`, the mean is zero and the
    /// variance is the 0.1 prior.
    pub fn distance(&self, input: Vec<f64>) -> PyResult<f64> {
        if input.len() != self.mean.len() {
            return Err(PyValueError::new_err(format!(
                "input length {} does not match dimension {}",
                input.len(),
                self.mean.len()
            )));
        }
        let mut d2 = 0.0;
        for i in 0..input.len() {
            let diff = input[i] - self.mean[i];
            d2 += (diff * diff) / self.var[i];
        }
        Ok(d2.sqrt())
    }
}

#[pyclass]
pub struct LLMPredictor {
    #[allow(dead_code)]
    api_url: String,
}

#[pymethods]
impl LLMPredictor {
    #[new]
    pub fn new(api_url: String) -> Self {
        LLMPredictor { api_url }
    }

    pub fn predict(&self, _input: Vec<f64>) -> Vec<f64> {
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
    pub fn new(nrem_budget: f64, rem_budget: f64) -> Self {
        Consolidation { nrem_budget, rem_budget }
    }

    pub fn nrem(&self, episodic: Vec<Vec<f64>>) -> Vec<f64> {
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

    pub fn rem(&self, pairs: Vec<(Vec<f64>, Vec<f64>)>) -> Vec<Vec<f64>> {
        pairs.iter().map(|(a, b)| {
            a.iter().zip(b.iter()).map(|(x, y)| (x + y) / 2.0).collect()
        }).collect()
    }
}

#[pyclass]
pub struct MultiConsolidation {
    #[allow(dead_code)]
    strategies: Vec<String>,
}

#[pymethods]
impl MultiConsolidation {
    #[new]
    pub fn new(strategies: Vec<String>) -> Self {
        MultiConsolidation { strategies }
    }

    pub fn consolidate(&self, data: Vec<Vec<f64>>) -> Vec<f64> {
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
    pub fn new(dimension: usize, learning_rate: f64) -> Self {
        HebbianConsolidation {
            learning_rate,
            weights: vec![vec![0.0; dimension]; dimension],
        }
    }

    pub fn update(&mut self, pre: Vec<f64>, post: Vec<f64>) {
        for i in 0..self.weights.len() {
            for j in 0..self.weights[i].len() {
                self.weights[i][j] += self.learning_rate * pre[i] * post[j];
            }
        }
    }

    pub fn recall(&self, input: Vec<f64>) -> Vec<f64> {
        let mut result = vec![0.0; input.len()];
        for i in 0..self.weights.len() {
            for j in 0..self.weights[i].len() {
                result[j] += self.weights[i][j] * input[i];
            }
        }
        result
    }
}
