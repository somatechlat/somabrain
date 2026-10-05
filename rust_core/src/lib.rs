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
                  fwht, fwht_inplace, PRODUCTION_SPARSITY_P, production_wiener_lambda,
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

    // GMD MathCore Functions (Theorems 2-4)
    m.add_function(wrap_pyfunction!(mathcore::fwht, m)?)?;
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
    use super::bhdc::PermutationBinder;
    use super::prediction::{MahalanobisPredictor, SlowPredictor};

    fn cosine(a: &[f64], b: &[f64]) -> f64 {
        let dot: f64 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
        let na: f64 = a.iter().map(|x| x * x).sum::<f64>().sqrt();
        let nb: f64 = b.iter().map(|x| x * x).sum::<f64>().sqrt();
        dot / (na * nb)
    }

    #[test]
    fn test_wiener_lambda_theorem3() {
        // λ* = Δ² / (12 p (1-p)) exactly (GMD text / DEBT-014).
        let p = 0.1;
        let delta = 2.0 / 255.0;
        let expected = (delta * delta) / (12.0 * p * (1.0 - p));
        let actual = compute_wiener_lambda(p, 8);
        assert!((actual - expected).abs() < 1e-15);
        // DEBT-014 cross-check: λ*(p=0.1, 8 bit) ≈ 5.695e-5
        assert!((actual - 5.695e-5).abs() < 1e-7);
    }

    #[test]
    fn test_wiener_lambda_honors_bits() {
        // Δ = 2/(2^bits − 1); bits must not be ignored.
        let delta16 = 2.0 / 65535.0;
        let expected = (delta16 * delta16) / (12.0 * 0.1 * 0.9);
        assert!((compute_wiener_lambda(0.1, 16) - expected).abs() < 1e-18);
        assert!((compute_wiener_lambda(0.1, 8) - compute_wiener_lambda(0.1, 16)).abs() > 1e-10);
    }

    #[test]
    fn test_production_wiener_lambda_matches_formula() {
        let expected = compute_wiener_lambda(PRODUCTION_SPARSITY_P, 8);
        assert!((production_wiener_lambda(8) - expected).abs() < 1e-15);
    }

    #[test]
    fn test_quantize_8bit_theorem3() {
        // Q maps [-1, 1] onto 256 levels.
        let test_cases: [(f64, f64); 4] = [
            (0.0, 0.0), (1.0, 1.0), (-1.0, -1.0), (0.5, 0.5039370078740157),
        ];
        for (x, expected) in test_cases {
            let actual = quantize_8bit(x);
            assert!((actual - expected).abs() < 0.01);
        }
        // Exactly 256 distinct output levels on a fine grid.
        let mut levels = std::collections::HashSet::new();
        for i in 0..=255 {
            let x = -1.0 + 2.0 * (i as f64) / 255.0;
            levels.insert(format!("{:.10}", quantize_8bit(x)));
        }
        assert_eq!(levels.len(), 256);
    }

    #[test]
    fn test_fwht_orthogonality() {
        let mut v = vec![1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0];
        fwht_inplace(&mut v).unwrap();
        let expected = 1.0 / (8.0_f64).sqrt();
        for val in &v {
            assert!((val - expected).abs() < 1e-10);
        }
    }

    #[test]
    fn test_fwht_inverse() {
        let original = vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0];
        let mut v = original.clone();
        fwht_inplace(&mut v).unwrap();
        fwht_inplace(&mut v).unwrap();
        for (orig, recovered) in original.iter().zip(v.iter()) {
            assert!((orig - recovered).abs() < 1e-10);
        }
    }

    #[test]
    fn test_fwht_rejects_non_power_of_two() {
        // Silent no-op is forbidden: non-2^r must raise (DEBT W4.4).
        assert!(fwht_inplace(&mut vec![1.0, 2.0, 3.0]).is_err());
        assert!(fwht_inplace(&mut Vec::new()).is_err());
        assert!(fwht_inplace(&mut vec![1.0, 2.0, 3.0, 4.0, 5.0]).is_err());
        assert!(fwht(vec![1.0, 2.0, 3.0]).is_err());
        assert!(fwht(vec![1.0, 2.0, 3.0, 4.0]).is_ok());
    }

    #[test]
    fn test_bayesian_memory_snr() {
        let mut mem = BayesianMemory::new(1024, 0.08, compute_wiener_lambda(PRODUCTION_SPARSITY_P, 8));
        for _ in 0..10 {
            let binding: Vec<f64> = (0..1024).map(|i| (i as f64).sin()).collect();
            mem.update(binding);
        }
        assert_eq!(mem.get_items_stored(), 10);
        let snr0 = mem.compute_snr_at_lag(0);
        assert!(snr0.is_finite() && snr0 > 0.0);
        // SNR decays with lag.
        assert!(mem.compute_snr_at_lag(10) < snr0);
    }

    #[test]
    fn test_capacity_estimation() {
        let mem = BayesianMemory::new(2048, 0.08, compute_wiener_lambda(PRODUCTION_SPARSITY_P, 8));
        let horizon = mem.estimate_horizon(1.0);
        assert!(horizon <= 10000);
        if horizon < 10000 {
            assert!(mem.compute_snr_at_lag(horizon + 1) < 1.0);
            if horizon > 0 {
                assert!(mem.compute_snr_at_lag(horizon) >= 1.0);
            }
        }
    }

    #[test]
    fn test_permutation_binder_roundtrip_pm1() {
        // ±1 codes: bind/unbind round-trip must reach cos ≥ 0.99.
        let dim = 256;
        for mix in ["none", "hadamard"] {
            let binder = PermutationBinder::new(dim, 42, "float32", mix, None, None).unwrap();
            let a: Vec<f64> = (0..dim).map(|i| if i % 2 == 0 { 1.0 } else { -1.0 }).collect();
            let b: Vec<f64> = (0..dim).map(|i| if i % 3 == 0 { -1.0 } else { 1.0 }).collect();
            let c = binder.bind(a.clone(), b.clone()).unwrap();
            let rec = binder.unbind(c, b).unwrap();
            let cos = cosine(&a, &rec);
            assert!(cos >= 0.99, "mix={mix}: round-trip cos {cos} < 0.99");
        }
    }

    #[test]
    fn test_permutation_binder_default_lambda_is_formula() {
        let binder = PermutationBinder::new(64, 7, "float32", "none", None, None).unwrap();
        assert!((binder.lambda_reg - compute_wiener_lambda(PRODUCTION_SPARSITY_P, 8)).abs() < 1e-15);
        let binder_p = PermutationBinder::new(64, 7, "float32", "none", None, Some(0.2)).unwrap();
        assert!((binder_p.lambda_reg - compute_wiener_lambda(0.2, 8)).abs() < 1e-15);
    }

    #[test]
    fn test_permutation_binder_hadamard_requires_pow2() {
        assert!(PermutationBinder::new(100, 1, "float32", "hadamard", None, None).is_err());
        assert!(PermutationBinder::new(128, 1, "float32", "hadamard", None, None).is_ok());
    }

    #[test]
    fn test_slow_predictor_cosine_error() {
        let p = SlowPredictor::new(4);
        // Opposite vectors: maximum error 1.0 (no abs).
        assert!((p.error(vec![1.0, 0.0], vec![-1.0, 0.0]) - 1.0).abs() < 1e-12);
        // Identical: 0.0
        assert!((p.error(vec![1.0, 0.0], vec![1.0, 0.0]) - 0.0).abs() < 1e-12);
        // Orthogonal: 1.0
        assert!((p.error(vec![1.0, 0.0], vec![0.0, 1.0]) - 1.0).abs() < 1e-12);
    }

    #[test]
    fn test_mahalanobis_diagonal_distance() {
        let mut m = MahalanobisPredictor::new(2, 0.5);
        // Anisotropic samples: variance along axis 0 >> axis 1.
        for i in 0..200 {
            let x0 = if i % 2 == 0 { 4.0 } else { -4.0 };
            m.update(vec![x0, 0.0]).unwrap();
        }
        let mean = m.mean.clone();
        let var = m.var.clone();
        // Distance must match sqrt(Σ (x−μ)²/σ²) on the live stats.
        let x = vec![mean[0] + 1.0, mean[1] + 1.0];
        let expected: f64 = (0..2)
            .map(|i| {
                let d = x[i] - mean[i];
                (d * d) / var[i]
            })
            .sum::<f64>()
            .sqrt();
        let actual = m.distance(x).unwrap();
        assert!((actual - expected).abs() < 1e-10);
        // Anisotropy: a unit step on the low-variance axis is far larger than
        // on the high-variance axis (Euclidean would treat them equally).
        let d_axis0 = m.distance(vec![mean[0] + 1.0, mean[1]]).unwrap();
        let d_axis1 = m.distance(vec![mean[0], mean[1] + 1.0]).unwrap();
        assert!(d_axis1 > 10.0 * d_axis0);
    }
}
