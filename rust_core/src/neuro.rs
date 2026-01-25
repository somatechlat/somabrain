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
    // Configurable dynamics constants (from brain_settings)
    k_d: [f64; 4],  // Drive coefficients
    k_r: [f64; 4],  // Recovery coefficients
    bias: [f64; 4], // Baseline bias
    u_scale: f64,   // Control input scale
}

#[pymethods]
impl Neuromodulators {
    #[new]
    #[pyo3(signature = (k_d=None, k_r=None, bias=None, u_scale=0.1))]
    pub fn new(k_d: Option<Vec<f64>>, k_r: Option<Vec<f64>>, bias: Option<Vec<f64>>, u_scale: f64) -> Self {
        // Default values from brain_settings: neuro_k_d_*, neuro_k_r_*
        let k_d_arr = match k_d {
            Some(v) if v.len() == 4 => [v[0], v[1], v[2], v[3]],
            _ => [0.8, 0.3, 0.1, 0.2],  // dopamine, serotonin, norad, acetyl
        };
        let k_r_arr = match k_r {
            Some(v) if v.len() == 4 => [v[0], v[1], v[2], v[3]],
            _ => [0.1, 0.2, 0.3, 0.4],
        };
        let bias_arr = match bias {
            Some(v) if v.len() == 4 => [v[0], v[1], v[2], v[3]],
            _ => [0.0, 0.0, 0.0, 0.0],
        };
        Neuromodulators {
            dopamine: 0.5,
            serotonin: 0.5,
            noradrenaline: 0.05,
            acetylcholine: 0.05,
            k_d: k_d_arr,
            k_r: k_r_arr,
            bias: bias_arr,
            u_scale,
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
        // Use configurable constants from struct (loaded from brain_settings)
        let mut d_m = [0.0; 4];
        let m = self.get_m();
        for i in 0..4 {
            d_m[i] = self.k_d[i] * x[i] - self.k_r[i] * m[i] + self.bias[i] + self.u_scale * u[i];
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

    /// Set dynamics constants (from brain_settings)
    pub fn set_dynamics(&mut self, k_d: Vec<f64>, k_r: Vec<f64>, bias: Vec<f64>, u_scale: f64) {
        if k_d.len() == 4 {
            self.k_d = [k_d[0], k_d[1], k_d[2], k_d[3]];
        }
        if k_r.len() == 4 {
            self.k_r = [k_r[0], k_r[1], k_r[2], k_r[3]];
        }
        if bias.len() == 4 {
            self.bias = [bias[0], bias[1], bias[2], bias[3]];
        }
        self.u_scale = u_scale;
    }

    /// Get current dynamics constants
    pub fn get_dynamics(&self) -> (Vec<f64>, Vec<f64>, Vec<f64>, f64) {
        (self.k_d.to_vec(), self.k_r.to_vec(), self.bias.to_vec(), self.u_scale)
    }
}

impl Default for Neuromodulators {
    fn default() -> Self {
        Self::new(None, None, None, 0.1)
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
