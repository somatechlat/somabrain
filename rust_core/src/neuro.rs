//! Neuromodulators and Amygdala modules.
//!
//! Part of GMD MathCore implementation.

use pyo3::prelude::*;

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
    pub fn new() -> Self {
        Neuromodulators {
            dopamine: 0.5,
            serotonin: 0.5,
            noradrenaline: 0.05,
            acetylcholine: 0.05,
        }
    }

    pub fn get_m(&self) -> Vec<f64> {
        vec![self.dopamine, self.serotonin, self.noradrenaline, self.acetylcholine]
    }

    pub fn set_m(&mut self, m: Vec<f64>) {
        if m.len() == 4 {
            self.dopamine = m[0];
            self.serotonin = m[1];
            self.noradrenaline = m[2];
            self.acetylcholine = m[3];
        }
    }

    pub fn update(&mut self, x: Vec<f64>, u: Vec<f64>, dt: f64) -> PyResult<()> {
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

    pub fn get_state(&self) -> Vec<f64> {
        vec![self.dopamine, self.serotonin, self.noradrenaline, self.acetylcholine]
    }

    pub fn set_state(&mut self, state: Vec<f64>) {
        if state.len() == 4 {
            self.dopamine = state[0];
            self.serotonin = state[1];
            self.noradrenaline = state[2];
            self.acetylcholine = state[3];
        }
    }

    pub fn reset(&mut self) {
        self.dopamine = 0.5;
        self.serotonin = 0.5;
        self.noradrenaline = 0.05;
        self.acetylcholine = 0.05;
    }
}

impl Default for Neuromodulators {
    fn default() -> Self {
        Self::new()
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
    pub fn new(threshold: f64, weights: Vec<f64>) -> Self {
        Amygdala { threshold, weights }
    }

    pub fn salience(&self, novelty: f64, error: f64, energy: f64) -> f64 {
        self.weights[0] * novelty + self.weights[1] * error + self.weights[2] * energy
    }

    pub fn gate(&self, score: f64) -> bool {
        score > self.threshold
    }

    pub fn update_weights(&mut self, new_weights: Vec<f64>) {
        if new_weights.len() == self.weights.len() {
            self.weights = new_weights;
        }
    }
}
