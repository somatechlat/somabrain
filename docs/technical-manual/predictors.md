# Diffusion-backed Predictors

This document describes the predictor core (`somabrain/predictors/base.py`) and how the three predictor services use it to emit mathematically grounded BeliefUpdate events.

## Overview

- Core: `somabrain/predictors/base.py`
  - `PredictorConfig`: diffusion time `t`, alpha for confidence mapping, Chebyshev degree, and Lanczos dimension.
  - `PredictorBase`: shared utilities for salience, error, and confidence.
  - `HeatDiffusionPredictor`: computes salience via heat-kernel diffusion and maps error→confidence.
  - Helpers: `make_line_graph_laplacian(n)`, `matvec_from_matrix(M)`.
- Services: `services/predictor-{state,agent,action}/main.py` now use the core to produce `BeliefUpdate`.

## Math

Let `L` be a graph Laplacian and `x0` a one-hot source. Salience at time `t` is

$$ y = e^{-tL} x_0 $$

We approximate the matrix exponential via one of:
- Chebyshev polynomial expansion on a normalized spectrum (Clenshaw recurrence)
- Lanczos/Krylov subspace with small `m` (dense exp on the tridiagonal `T`)

Error is the mean-squared deviation between predicted salience and an observed vector `o`:

$$ \mathrm{mse}(y, o) = \frac{1}{n}\sum_i (y_i - o_i)^2 $$

Confidence is a monotone transform of error:

$$ c = e^{-\alpha \cdot \mathrm{mse}} \in (0, 1] $$

## Configuration

- `SOMA_HEAT_METHOD` = `chebyshev` | `lanczos`
- `SOMABRAIN_DIFFUSION_T` (float, default 0.5)
- `SOMABRAIN_CONF_ALPHA` (float, default 2.0)
- `SOMABRAIN_CHEB_K` (int, default 30)
- `SOMABRAIN_LANCZOS_M` (int, default 20)
- `SOMABRAIN_PREDICTOR_DIM` (int, fallback; used when no graph file is provided)
- Production graph files (JSON):
  - `SOMABRAIN_GRAPH_FILE` (global fallback)
  - `SOMABRAIN_GRAPH_FILE_STATE` | `SOMABRAIN_GRAPH_FILE_AGENT` | `SOMABRAIN_GRAPH_FILE_ACTION`
  - Supported JSON formats:
    - `{ "adjacency": [[...]] }` (we compute Laplacian `L = D - A`)
    - `{ "laplacian": [[...]] }`
    - `{ "type": "adjacency"|"laplacian", "matrix": [[...]] }`
  - Loader API: `somabrain.predictors.base.load_operator_from_file(path)`

## Service Integration

Each predictor service constructs a predictor via `build_predictor_from_env(domain)`, which prefers a domain-specific graph file if provided and falls back to a small line-graph Laplacian. In production, supply your domain graph file via the envs above to avoid the fallback.

Runtime defaults (always-on):
- Feature flags for predictors default to ON so the services are available unless explicitly disabled:
  - `SOMABRAIN_FF_PREDICTOR_STATE=1`
  - `SOMABRAIN_FF_PREDICTOR_AGENT=1`
  - `SOMABRAIN_FF_PREDICTOR_ACTION=1`
- To disable a specific predictor, set its FF to `0`.

Quickstart (local):
1) Provide graph files (optional): set `SOMABRAIN_GRAPH_FILE_*` envs or rely on fallback.
2) Ensure Kafka is reachable via `SOMABRAIN_KAFKA_URL`.
3) Start the services (e.g., via docker-compose or your process supervisor).
4) Observe metrics: `somabrain_predictor_error{domain}` and Integrator metrics when enabled.

Emitted schema: `proto/cog/belief_update.avsc`.

## Metrics

- `somabrain_predictor_error{domain}` — per-update MSE
- `somabrain_predictor_{state,agent,action}_emitted_total`
- `somabrain_predictor_{state,agent,action}_next_total`

## Tests

`tests/predictors/test_heat_diffusion_predictor.py` verifies:
- Chebyshev/Lanczos outputs match `scipy.linalg.expm` on a small Laplacian (tight tolerances)
- Confidence decreases monotonically with increasing error

## Integrator Alignment

IntegratorHub can enforce confidence normalization from `delta_error` to ensure consistent softmax inputs:
- `SOMABRAIN_INTEGRATOR_ALPHA` (float, default 2.0)
- `SOMABRAIN_INTEGRATOR_ENFORCE_CONF` (bool; if on, always recomputes `confidence = exp(-alpha·delta_error)`)

Additionally, Integrator exposes `somabrain_integrator_leader_total{leader}` to track leader frequency.

## Migration Notes

- Existing topic and schema contracts are preserved.
- Predictor services keep health endpoints and metrics; only the internal confidence/error calculation changed.
- No changes are required for downstream consumers of `cog.global.frame` or `cog.segments`.
