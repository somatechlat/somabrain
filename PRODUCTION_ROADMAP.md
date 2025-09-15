# Production Roadmap

This file is the canonical roadmap for Somabrain production readiness. It focuses on numerics hardening, observability, determinism, testing, benchmarking, and CI. The content below is derived directly from the source code and recent audit.

## Numerics Roadmap (consolidated)

Phases:

- P0 — Safety & reproducible baseline
  - Fix typing/call-site for `compute_tiny_floor`.
  - Add deterministic tests for role reproducibility, tiny->spectral conversion, and dtype boundary checks.
  - Acceptance: P0 tests pass locally.

- P1 — Numeric correctness & robust unbinds
  - Standardize spectral arithmetic: float64 power arrays, complex128 spectral numerators, denom in float64, NaN/Inf guards.
  - Centralize tiny->spectral conversion in `spectral_floor_from_tiny`.
  - Add tests for unbind strategies (SNR sweep) and unitary isometry.
  - Acceptance: tests pass and Wiener shows robustness at low SNR.

- P2 — Benchmarks & capacity experiments
  - Add `benchmarks/numerics_workbench.py` sweeping D, tiny_amp, SNR, seeds.
  - Produce JSON and PNG artifacts; record capacity N where cosine < 0.9.
  - Immediate experiments (recommended order):
    - Stress tests: small-D (D ∈ {128,256}), extreme SNRs (down to -30 dB), impulsive spectral nulls and correlated fillers to demonstrate clear failure modes for exact deconvolution and highlight where Wiener/Tikhonov helps.
      - Artifacts: JSON `benchmarks/results_numerics.json`, plots in `benchmarks/plots/` (e.g. `mse_D128.png`, `cosine_D128.png`).
      - Estimated runtime: 20–40 minutes (local venv), reproducible via `PYTHONPATH=. ./venv/bin/python benchmarks/numerics_workbench.py --stress`.
    - Capacity curve: measure recall cosine vs N (number of superposed items) for D ∈ {256,1024} and identify N where mean cosine < 0.9.
      - Artifacts: `benchmarks/workbench_numerics_results.json` and summary CSV/PNG.
      - Estimated runtime: 20–40 minutes.
    - Task demo (optional): small FastAPI demo or quick-start script (`examples/soma_quickstart.py`) that exercises binding/unbinding in a short pipeline and records numeric stability.
    - Run everything: full sweep combining stress + capacity + SNR sweep for publication-quality figures (longer run; 1–3 hours depending on seeds and D grid).

- P3 — Observability & telemetry
  - Add metrics: unbind.path_total, spectral_bins_clamped_total, eps_used histogram, reconstruction_cosine.
  - Add debug logs for robust fallback usage.

- P4 — Docs & reproducibility
  - Add `docs/source/numerics.rst` documenting tiny-floor, dtype policy, RNG seed guidance, strict_math behavior.
  - Ensure Sphinx builds.

- P5 — CI & pinning
  - Add CI to run lint, tests, docs build, bench smoke and pin numpy/pocketfft versions.

Notes:
- Keep `strict_math` as a configuration gate to preserve exact algebraic behavior for research.
- Use deterministic RNG (`np.random.default_rng(seed)`) for role/filler generation.


## Status & Next Steps
- P0: Implemented (typing fix + P0 tests added and passed).
 - P1: Numeric correctness & robust unbinds
   - Standardized spectral patterns partially enforced in `somabrain/quantum.py` for `unbind` and `unbind_exact`.
   - Centralized tiny->spectral conversion in `spectral_floor_from_tiny` (in `somabrain/numerics.py`).
   - Tests: SNR sweep and unbind strategy tests added and run for a focused set of cases.
   - Acceptance criteria: unit tests pass and a focused bench shows Wiener improves stability in stressed settings.

 - P2: Benchmarks & capacity experiments — In progress
   - Stress bench script and plotting helper added. Example artifacts present in `benchmarks/` (JSON + PNGs).
   - Next: run the stress-suite (D=128,256, extreme SNRs) and store canonical artifacts.

 - P3: Observability — Partial
   - Metric labels and counters were added in code paths but need final names, histograms, and bench sink wiring.

 - P4: Docs & reproducibility — Partial
   - Sphinx build smoke tested; add `docs/source/numerics.rst` and reproducibility how-to (commands to reproduce bench/plots).

 - P5: CI & pinning — Pending
   - Add GitHub Actions workflow for lint/test/docs/bench-smoke and pin numeric deps in `pyproject.toml`/`requirements-dev.txt`.

## Artifacts produced so far (local paths)
- `benchmarks/results_numerics.json` — extended bench results (SNR sweep)
- `benchmarks/workbench_numerics_results.json` — workbench runs (capacity-style experiments)
- `benchmarks/plots/` — PNGs: `cosine_D512.png`, `mse_D512.png`, `cosine_D1024.png`, `mse_D1024.png`
- Tests added: `tests/test_role_reproducible.py`, `tests/test_tiny_floor_power_conversion.py`, `tests/test_numerics_dtype_boundaries.py` (P0 acceptance tests)

## Next recommended actions (pick one)
1. Run stress bench (recommended): produces strong examples where Wiener helps. Command (local):

   PYTHONPATH=. ./venv/bin/python benchmarks/numerics_workbench.py --stress --out benchmarks/results_numerics.json

2. Run capacity curves: measure recall vs N and record N where mean cosine < 0.9.
3. Wire metrics sink and re-run bench to collect metrics JSON.
4. Add `docs/source/numerics.rst` and a short reproducibility section; rebuild Sphinx.

If you want, I can run option 1 (stress bench) now and commit the canonical artifacts and update the docs with a short how-to.
