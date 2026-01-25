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
pub use bhdc::{BHDCEncoder, QuantumState, QuantumModule};
pub use neuro::{Neuromodulators, Amygdala};
pub use prediction::{SlowPredictor, BudgetedPredictor, MahalanobisPredictor, LLMPredictor,
                    Consolidation, MultiConsolidation, HebbianConsolidation};
pub use mathcore::{FNOM, BatchNorm, Dropout, MatrixOps, BayesianMemory,
                  norm_l2, softmax, batch_norm_inference,
                  fwht, fwht_inplace, compute_optimal_p, compute_capacity_theorem1,
                  compute_wiener_lambda, quantize_8bit, quantize_vector, wiener_unbind};
pub use adaptation::{RetrievalWeights, UtilityWeights, AdaptationEngine};

// ==================== Module Registration ====================

#[pymodule]
fn somabrain_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // BHDC Module
    m.add_class::<BHDCEncoder>()?;
    m.add_class::<QuantumState>()?;
    m.add_class::<QuantumModule>()?;

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

    // GMD MathCore Functions (Theorems 1-4)
    m.add_function(wrap_pyfunction!(mathcore::fwht, m)?)?;
    m.add_function(wrap_pyfunction!(mathcore::compute_optimal_p, m)?)?;
    m.add_function(wrap_pyfunction!(mathcore::compute_capacity_theorem1, m)?)?;
    m.add_function(wrap_pyfunction!(mathcore::compute_wiener_lambda, m)?)?;
    m.add_function(wrap_pyfunction!(mathcore::quantize_8bit, m)?)?;
    m.add_function(wrap_pyfunction!(mathcore::quantize_vector, m)?)?;
    m.add_function(wrap_pyfunction!(mathcore::wiener_unbind, m)?)?;

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
}
