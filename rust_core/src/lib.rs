//! SomaBrain Rust Core - GMD MathCore Implementation
//!
//! High-performance CPU-bound operations for SomaBrain.
//! Split into modules for maintainability (max 650 lines per file).

use pyo3::prelude::*;

// Module declarations
mod bhdc;
mod neuro;
mod prediction;
mod mathcore;
mod adaptation;

// Re-exports for internal use
pub use bhdc::{BHDCEncoder, PermutationBinder, QuantumState, QuantumModule, ensure_binary};
pub use neuro::{Neuromodulators, Amygdala};
pub use prediction::{SlowPredictor, BudgetedPredictor, MahalanobisPredictor, LLMPredictor,
                    Consolidation, MultiConsolidation, HebbianConsolidation};
pub use mathcore::{FNOM, BatchNorm, Dropout, MatrixOps, BayesianMemory,
                  norm_l2, softmax, softmax_temperature, compute_entropy, softmax_leader_selection,
                  cosine_similarity, batch_norm_inference,
                  fwht, fwht_inplace, compute_optimal_p, compute_capacity_theorem1,
                  compute_wiener_lambda, quantize_8bit, quantize_vector, wiener_unbind};
pub use adaptation::{RetrievalWeights, UtilityWeights, AdaptationEngine,
                    apply_tau_annealing, linear_tau_decay, exponential_tau_decay,
                    compute_td_return, compute_td_error, compute_n_step_return, decay_eligibility};

// ==================== Module Registration ====================

#[pymodule]
fn somabrain_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // BHDC Module
    m.add_class::<BHDCEncoder>()?;
    m.add_class::<PermutationBinder>()?;
    m.add_class::<QuantumState>()?;
    m.add_class::<QuantumModule>()?;
    m.add_function(wrap_pyfunction!(bhdc::ensure_binary, m)?)?;

    // Neuro Module
    m.add_class::<Neuromodulators>()?;
    m.add_class::<Amygdala>()?;

    // Prediction Module
    m.add_class::<SlowPredictor>()?;
    m.add_class::<BudgetedPredictor>()?;
    m.add_class::<MahalanobisPredictor>()?;
    m.add_class::<LLMPredictor>()?;
    m.add_class::<Consolidation>()?;
    m.add_class::<MultiConsolidation>()?;
    m.add_class::<HebbianConsolidation>()?;

    // MathCore Module
    m.add_class::<FNOM>()?;
    m.add_class::<BatchNorm>()?;
    m.add_class::<Dropout>()?;
    m.add_class::<MatrixOps>()?;
    m.add_class::<BayesianMemory>()?;

    // Adaptation Module
    m.add_class::<RetrievalWeights>()?;
    m.add_class::<UtilityWeights>()?;
    m.add_class::<AdaptationEngine>()?;

    // Utility functions
    m.add_function(wrap_pyfunction!(mathcore::norm_l2, m)?)?;
    m.add_function(wrap_pyfunction!(mathcore::softmax, m)?)?;
    m.add_function(wrap_pyfunction!(mathcore::batch_norm_inference, m)?)?;

    // Karpathy temperature-scaled softmax and entropy
    m.add_function(wrap_pyfunction!(mathcore::softmax_temperature, m)?)?;
    m.add_function(wrap_pyfunction!(mathcore::compute_entropy, m)?)?;
    m.add_function(wrap_pyfunction!(mathcore::softmax_leader_selection, m)?)?;
    m.add_function(wrap_pyfunction!(mathcore::cosine_similarity, m)?)?;

    // GMD MathCore Functions (Theorems 1-4)
    m.add_function(wrap_pyfunction!(mathcore::fwht, m)?)?;
    m.add_function(wrap_pyfunction!(mathcore::compute_optimal_p, m)?)?;
    m.add_function(wrap_pyfunction!(mathcore::compute_capacity_theorem1, m)?)?;
    m.add_function(wrap_pyfunction!(mathcore::compute_wiener_lambda, m)?)?;
    m.add_function(wrap_pyfunction!(mathcore::quantize_8bit, m)?)?;
    m.add_function(wrap_pyfunction!(mathcore::quantize_vector, m)?)?;
    m.add_function(wrap_pyfunction!(mathcore::wiener_unbind, m)?)?;

    // Karpathy tau annealing
    m.add_function(wrap_pyfunction!(adaptation::apply_tau_annealing, m)?)?;
    m.add_function(wrap_pyfunction!(adaptation::linear_tau_decay, m)?)?;
    m.add_function(wrap_pyfunction!(adaptation::exponential_tau_decay, m)?)?;

    // Sutton TD learning
    m.add_function(wrap_pyfunction!(adaptation::compute_td_return, m)?)?;
    m.add_function(wrap_pyfunction!(adaptation::compute_td_error, m)?)?;
    m.add_function(wrap_pyfunction!(adaptation::compute_n_step_return, m)?)?;
    m.add_function(wrap_pyfunction!(adaptation::decay_eligibility, m)?)?;

    Ok(())
}

// ==================== Unit Tests ====================

#[cfg(test)]
mod tests {
    use super::mathcore::*;
    use super::adaptation::*;

    #[test]
    fn test_optimal_p_theorem1() {
        let test_cases: [(f64, f64); 4] = [
            (0.01, 0.55), (0.04, 0.60), (0.09, 0.65), (0.25, 0.75),
        ];
        for (delta, expected) in test_cases {
            let computed = compute_optimal_p(delta);
            assert!((computed - expected).abs() < 1e-10);
        }
    }

    #[test]
    fn test_wiener_lambda_theorem3() {
        let p = 0.1;
        let delta = 2.0 / 255.0;
        let expected = (delta * delta) / (3.0 * 2.0 * p * (1.0 - p));
        let actual = compute_wiener_lambda(p, 8);
        assert!((actual - expected).abs() < 1e-15);
    }

    #[test]
    fn test_quantize_8bit_theorem3() {
        let test_cases: [(f64, f64); 4] = [
            (0.0, 0.0), (1.0, 1.0), (-1.0, -1.0), (0.5, 0.5039370078740157),
        ];
        for (x, expected) in test_cases {
            let actual = quantize_8bit(x);
            assert!((actual - expected).abs() < 0.01);
        }
    }

    #[test]
    fn test_fwht_orthogonality() {
        let mut v = vec![1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0];
        fwht_inplace(&mut v);
        let expected = 1.0 / (8.0_f64).sqrt();
        for val in &v {
            assert!((val - expected).abs() < 1e-10);
        }
    }

    #[test]
    fn test_fwht_inverse() {
        let original = vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0];
        let mut v = original.clone();
        fwht_inplace(&mut v);
        fwht_inplace(&mut v);
        for (orig, recovered) in original.iter().zip(v.iter()) {
            assert!((orig - recovered).abs() < 1e-10);
        }
    }

    #[test]
    fn test_bayesian_memory_snr() {
        let mut mem = BayesianMemory::new(1024, 0.08, 2.05e-5);
        for _ in 0..10 {
            let binding: Vec<f64> = (0..1024).map(|i| (i as f64).sin()).collect();
            mem.update(binding);
        }
        assert_eq!(mem.get_items_stored(), 10);
        let p = 0.1;
        let expected_snr = ((2.0 * 0.08 - 0.08 * 0.08) / 9.0) * (1024.0 / (p * (1.0 - p)));
        let actual_snr = mem.compute_snr(p);
        assert!((actual_snr - expected_snr).abs() / expected_snr < 0.0001);
    }

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
        assert!((actual_gamma - expected_gamma).abs() < 1e-10);
    }

    #[test]
    fn test_capacity_estimation() {
        let mem = BayesianMemory::new(2048, 0.08, 2.05e-5);
        let expected = (2048.0 / (640.0 * 0.08)) as usize;
        assert_eq!(mem.estimate_capacity(), expected);
    }

    #[test]
    fn test_wiener_unbind_normalization() {
        let memory = vec![1.0, 2.0, 3.0, 4.0];
        let key = vec![0.5, 0.5, 0.5, 0.5];
        let result = wiener_unbind(memory, key, 2.05e-5);
        let norm: f64 = result.iter().map(|x| x * x).sum::<f64>().sqrt();
        assert!((norm - 1.0).abs() < 1e-10);
    }

    // ==================== Karpathy Tests ====================

    #[test]
    fn test_softmax_temperature() {
        use super::mathcore::{softmax_temperature, compute_entropy};

        let scores = vec![1.0, 2.0, 3.0];

        // τ = 1: standard softmax
        let probs = softmax_temperature(scores.clone(), 1.0);
        let sum: f64 = probs.iter().sum();
        assert!((sum - 1.0).abs() < 1e-10);

        // τ → 0: more deterministic (higher prob on max)
        let probs_low_tau = softmax_temperature(scores.clone(), 0.1);
        assert!(probs_low_tau[2] > probs[2]);

        // τ → ∞: more uniform
        let probs_high_tau = softmax_temperature(scores.clone(), 10.0);
        assert!(probs_high_tau[2] < probs[2]);
    }

    #[test]
    fn test_compute_entropy() {
        use super::mathcore::compute_entropy;

        // Uniform distribution: max entropy = ln(n)
        let uniform = vec![0.25, 0.25, 0.25, 0.25];
        let expected_uniform = 4.0_f64.ln();  // ln(4)
        let actual = compute_entropy(uniform);
        assert!((actual - expected_uniform).abs() < 1e-10);

        // Deterministic: entropy = 0
        let deterministic = vec![1.0, 0.0, 0.0, 0.0];
        let actual_det = compute_entropy(deterministic);
        assert!(actual_det.abs() < 1e-10);
    }

    #[test]
    fn test_softmax_leader_selection() {
        use super::mathcore::softmax_leader_selection;

        let scores = vec![1.0, 2.0, 3.0, 4.0];
        let tau = 0.5;
        let entropy_cap = 1.0;

        let (probs, entropy, exceeded) = softmax_leader_selection(scores.clone(), tau, entropy_cap);

        assert_eq!(probs.len(), 4);
        let sum: f64 = probs.iter().sum();
        assert!((sum - 1.0).abs() < 1e-10);
        assert!(entropy >= 0.0);

        // Low entropy cap should be exceeded with high temperature
        let (_, entropy_high, exceeded_high) = softmax_leader_selection(scores, 5.0, 0.1);
        assert!(entropy_high > 0.1);
        assert!(exceeded_high);
    }

    // ==================== Sutton Tests ====================

    #[test]
    fn test_td_return() {
        use super::adaptation::compute_td_return;

        let reward = 1.0;
        let next_value = 10.0;
        let gamma = 0.9;

        let expected = 1.0 + 0.9 * 10.0;  // 10.0
        let actual = compute_td_return(reward, next_value, gamma);
        assert!((actual - expected).abs() < 1e-10);
    }

    #[test]
    fn test_td_error() {
        use super::adaptation::compute_td_error;

        let reward = 1.0;
        let next_value = 10.0;
        let current_value = 5.0;
        let gamma = 0.9;

        // δ = R + γV(s') - V(s) = 1 + 0.9*10 - 5 = 5.0
        let expected = 5.0;
        let actual = compute_td_error(reward, next_value, current_value, gamma);
        assert!((actual - expected).abs() < 1e-10);
    }

    #[test]
    fn test_n_step_return() {
        use super::adaptation::compute_n_step_return;

        let rewards = vec![1.0, 2.0, 3.0];
        let final_value = 10.0;
        let gamma = 0.9;

        // G = r1 + γr2 + γ²r3 + γ³V
        // G = 1 + 0.9*2 + 0.81*3 + 0.729*10
        let expected = 1.0 + 0.9 * 2.0 + 0.81 * 3.0 + 0.729 * 10.0;
        let actual = compute_n_step_return(rewards, final_value, gamma);
        assert!((actual - expected).abs() < 1e-10);
    }

    #[test]
    fn test_tau_annealing() {
        use super::adaptation::apply_tau_annealing;

        // Linear: τ - rate
        let tau = 1.0;
        let result = apply_tau_annealing(tau, "linear", 0.1, 0, 0, 0.01);
        assert!((result - 0.9).abs() < 1e-10);

        // Exponential: τ * exp(-rate)
        let result_exp = apply_tau_annealing(tau, "exponential", 0.1, 0, 0, 0.01);
        let expected_exp = tau * (-0.1_f64).exp();
        assert!((result_exp - expected_exp).abs() < 1e-10);

        // Step: only at intervals
        let result_step_no = apply_tau_annealing(tau, "step", 0.1, 5, 10, 0.01);
        assert!((result_step_no - 1.0).abs() < 1e-10);

        let result_step_yes = apply_tau_annealing(tau, "step", 0.1, 10, 10, 0.01);
        assert!((result_step_yes - 0.9).abs() < 1e-10);
    }
}

