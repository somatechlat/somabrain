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

    pub fn error(&self, prediction: Vec<f64>, actual: Vec<f64>) -> f64 {
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

#[pyclass]
pub struct MahalanobisPredictor {
    mean: Vec<f64>,
    #[allow(dead_code)]
    covariance: Vec<Vec<f64>>,
    ewma_alpha: f64,
}

#[pymethods]
impl MahalanobisPredictor {
    #[new]
    pub fn new(dimension: usize, ewma_alpha: f64) -> Self {
        MahalanobisPredictor {
            mean: vec![0.0; dimension],
            covariance: vec![vec![0.0; dimension]; dimension],
            ewma_alpha,
        }
    }

    pub fn update(&mut self, input: Vec<f64>) {
        for i in 0..self.mean.len() {
            self.mean[i] = (1.0 - self.ewma_alpha) * self.mean[i] + self.ewma_alpha * input[i];
        }
    }

    pub fn distance(&self, input: Vec<f64>) -> f64 {
        let diff: Vec<f64> = input.iter().zip(self.mean.iter()).map(|(a, b)| a - b).collect();
        diff.iter().map(|x| x * x).sum::<f64>().sqrt()
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
