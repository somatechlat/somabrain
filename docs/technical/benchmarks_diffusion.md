# Diffusion Predictor Benchmarks

This benchmark evaluates the diffusion-backed predictors (Chebyshev and Lanczos) against the exact matrix exponential for accuracy and measures runtime scaling.

## How to run

- Ensure dev extras are installed (matplotlib is required):
  - make dev
- Run the benchmark:
  - make bench-diffusion

Artifacts are written to timestamped folders to keep the tree clean:
- Results (JSON): `benchmarks/results/diffusion_predictors/<timestamp>/`
  - `accuracy_sweep.json` — MSE and runtime vs K (Chebyshev) or m (Lanczos)
  - `runtime_sweep.json` — runtime vs graph size n
- Plots (PNG): `benchmarks/plots/diffusion_predictors/<timestamp>/`
  - `accuracy_chebyshev_n32_t0.3.png`, `accuracy_lanczos_n32_t0.3.png`
  - `runtime_vs_n.png`
  - `salience_heatmap.png`

The latest timestamp is recorded in `benchmarks/results/diffusion_predictors/latest.txt` for convenience.

## Methodology

- Graph: line-graph Laplacian (path) as a controlled baseline.
- Exact reference: `expm(-t L) @ x0` with `scipy.linalg.expm`.
- Predictors: `HeatDiffusionPredictor` with either Chebyshev (degree K) or Lanczos (dimension m).
- Metrics: mean-squared error vs exact and wall-clock runtime per salience evaluation.

## Interpreting results

- Accuracy plots show how error decreases as K/m increases; both methods reach near machine precision quickly for small n.
- Runtime plots show scaling with graph size n at fixed parameters (K=40, m=20).
- The salience heatmap provides a quick visual comparison (exact vs Chebyshev vs Lanczos).

## Notes

- For large graphs, exact expm is omitted (mse is recorded as NaN) to keep runs fast.
- The benchmark uses a non-interactive Matplotlib backend (`MPLBACKEND=Agg`) and does not open windows.
