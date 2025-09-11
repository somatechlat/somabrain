Math reference — Numerics
=========================

This page documents the numeric contract and design choices used by the
SomaBrain core.

Key invariants
---------------

- Tiny-floor semantics: `compute_tiny_floor` returns an amplitude threshold (L2-norm units).
  For spectral operations that operate per-FFT-bin in power, callers MUST convert:

  power_per_bin = tiny_amp**2 / D

- FFTs: we use unitary real-FFT wrappers `rfft_norm` and `irfft_norm` with `norm='ortho'`.
  This preserves energy and simplifies mathematical reasoning about convolution and deconvolution.

- Normalization: `normalize_array(x, axis, ...)` computes sum-of-squares (energy) per slice,
  compares it with tiny_amp**2, and uses either a deterministic baseline vector
  (ones/sqrt(D)) or a zero-vector depending on the chosen mode. All energy mixing is done
  in power units and amplitude thresholds are squared before mixing.

- Spectral floors: when dividing in the frequency domain during unbinding, denominators are
  formed from spectral power (|F(B)|^2) with a floor in power-per-bin units. That floor is derived
  from the amplitude tiny by squaring and dividing by D.

Determinism and fallback
------------------------

- Baseline fallback is deterministic: the baseline unit-vector is `ones / sqrt(D)` and is used
  when the slice energy is below the subtiny threshold. This produces deterministic, explainable
  outputs for low-energy inputs.

- Seeding for pseudo-random role vectors is deterministic where used in tests and benchmarks;
  the default numerics operations are pure deterministic numeric transforms.

Why amplitude vs power?
------------------------

Using an amplitude tiny keeps the API consistent with L2-normalization semantics (||x||_2).
Spectral operations naturally operate on power (square of amplitudes); therefore the explicit
conversion step (square and divide by D) makes the unit change visible and auditable.

See `somabrain/numerics.py` for the implementation.
