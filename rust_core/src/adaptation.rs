//! AdaptationEngine module - CPU-bound hot path optimization.
//!
//! Part of GMD MathCore implementation.

use pyo3::prelude::*;

// ==================== AdaptationEngine Module ====================

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
    pub fn new(alpha: f64, beta: f64, gamma: f64, tau: f64) -> Self {
        RetrievalWeights { alpha, beta, gamma, tau }
    }

    pub fn to_vec(&self) -> Vec<f64> {
        vec![self.alpha, self.beta, self.gamma, self.tau]
    }

    pub fn from_vec(&mut self, v: Vec<f64>) {
        if v.len() >= 4 {
            self.alpha = v[0];
            self.beta = v[1];
            self.gamma = v[2];
            self.tau = v[3];
        }
    }
}

impl Default for RetrievalWeights {
    fn default() -> Self {
        Self::new(1.0, 0.2, 0.1, 0.7)
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
    pub fn new(lambda_: f64, mu: f64, nu: f64) -> Self {
        UtilityWeights { lambda_, mu, nu }
    }

    pub fn clamp(&mut self, lambda_min: f64, lambda_max: f64, mu_min: f64, mu_max: f64, nu_min: f64, nu_max: f64) {
        self.lambda_ = self.lambda_.clamp(lambda_min, lambda_max);
        self.mu = self.mu.clamp(mu_min, mu_max);
        self.nu = self.nu.clamp(nu_min, nu_max);
    }
}

impl Default for UtilityWeights {
    fn default() -> Self {
        Self::new(1.0, 0.1, 0.05)
    }
}

#[pyclass]
pub struct AdaptationEngine {
    retrieval: RetrievalWeights,
    utility: UtilityWeights,
    #[pyo3(get, set)]
    pub learning_rate: f64,
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
    pub fn new(learning_rate: f64) -> Self {
        AdaptationEngine {
            retrieval: RetrievalWeights::default(),
            utility: UtilityWeights::default(),
            learning_rate,
            base_lr: learning_rate,
            feedback_count: 0,
            alpha_bounds: (0.1, 2.0),
            gamma_bounds: (0.0, 1.0),
            lambda_bounds: (0.1, 2.0),
            mu_bounds: (0.0, 0.5),
            nu_bounds: (0.0, 0.2),
            gain_alpha: 0.1,
            gain_gamma: 0.05,
            gain_lambda: 0.1,
            gain_mu: 0.05,
            gain_nu: 0.02,
        }
    }

    pub fn set_retrieval(&mut self, alpha: f64, beta: f64, gamma: f64, tau: f64) {
        self.retrieval.alpha = alpha;
        self.retrieval.beta = beta;
        self.retrieval.gamma = gamma;
        self.retrieval.tau = tau;
    }

    pub fn get_retrieval(&self) -> (f64, f64, f64, f64) {
        (self.retrieval.alpha, self.retrieval.beta, self.retrieval.gamma, self.retrieval.tau)
    }

    pub fn set_utility(&mut self, lambda_: f64, mu: f64, nu: f64) {
        self.utility.lambda_ = lambda_;
        self.utility.mu = mu;
        self.utility.nu = nu;
    }

    pub fn get_utility(&self) -> (f64, f64, f64) {
        (self.utility.lambda_, self.utility.mu, self.utility.nu)
    }

    pub fn set_constraints(&mut self, alpha_min: f64, alpha_max: f64, gamma_min: f64, gamma_max: f64,
                       lambda_min: f64, lambda_max: f64, mu_min: f64, mu_max: f64, nu_min: f64, nu_max: f64) {
        self.alpha_bounds = (alpha_min, alpha_max);
        self.gamma_bounds = (gamma_min, gamma_max);
        self.lambda_bounds = (lambda_min, lambda_max);
        self.mu_bounds = (mu_min, mu_max);
        self.nu_bounds = (nu_min, nu_max);
    }

    pub fn set_gains(&mut self, alpha: f64, gamma: f64, lambda_: f64, mu: f64, nu: f64) {
        self.gain_alpha = alpha;
        self.gain_gamma = gamma;
        self.gain_lambda = lambda_;
        self.gain_mu = mu;
        self.gain_nu = nu;
    }

    /// Apply feedback and update weights - CPU-bound hot path
    pub fn apply_feedback(&mut self, utility_signal: f64, reward: f64) -> bool {
        let semantic_signal = reward;
        let utility_val = utility_signal;

        self.retrieval.alpha = (self.retrieval.alpha + self.learning_rate * self.gain_alpha * semantic_signal)
            .clamp(self.alpha_bounds.0, self.alpha_bounds.1);
        self.retrieval.gamma = (self.retrieval.gamma + self.learning_rate * self.gain_gamma * semantic_signal)
            .clamp(self.gamma_bounds.0, self.gamma_bounds.1);

        self.utility.lambda_ = (self.utility.lambda_ + self.learning_rate * self.gain_lambda * utility_val)
            .clamp(self.lambda_bounds.0, self.lambda_bounds.1);
        self.utility.mu = (self.utility.mu + self.learning_rate * self.gain_mu * utility_val)
            .clamp(self.mu_bounds.0, self.mu_bounds.1);
        self.utility.nu = (self.utility.nu + self.learning_rate * self.gain_nu * utility_val)
            .clamp(self.nu_bounds.0, self.nu_bounds.1);

        self.feedback_count += 1;
        true
    }

    pub fn linear_decay(&self, tau_0: f64, tau_min: f64, alpha: f64, t: u64) -> f64 {
        (tau_0 - alpha * (t as f64)).max(tau_min)
    }

    pub fn exponential_decay(&self, tau_0: f64, gamma: f64, t: u64) -> f64 {
        tau_0 * (-gamma * (t as f64)).exp()
    }

    pub fn apply_tau_decay(&mut self, decay_rate: f64, min_tau: f64) {
        self.retrieval.tau = (self.retrieval.tau * (1.0 - decay_rate)).max(min_tau);
    }

    pub fn get_tau(&self) -> f64 {
        self.retrieval.tau
    }

    pub fn set_tau(&mut self, tau: f64) {
        self.retrieval.tau = tau.clamp(0.01, 10.0);
    }

    pub fn get_feedback_count(&self) -> u64 {
        self.feedback_count
    }

    pub fn reset(&mut self) {
        self.retrieval = RetrievalWeights::default();
        self.utility = UtilityWeights::default();
        self.learning_rate = self.base_lr;
        self.feedback_count = 0;
    }

    pub fn get_state(&self) -> Vec<(String, f64)> {
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

    pub fn update_learning_rate(&mut self, dopamine: f64) {
        let lr_scale = (0.5 + dopamine).clamp(0.5, 1.2);
        self.learning_rate = self.base_lr * lr_scale;
    }
}
