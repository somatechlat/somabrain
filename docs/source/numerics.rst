Numerics
========

This page documents the canonical numerics contract used by SomaBrain's HRR (High-dimensional Representations) implementation and provides reproducible synthetic benchmark recipes that exercise production‑like numerical conditions. The content below is derived from the implementations in ``somabrain/numerics.py`` and ``somabrain/quantum.py`` and is intended to be the single source of truth for the math used in the code.

.. contents::
   :local:

Math contract (short)
---------------------

- **FFT wrappers**
  - Use the unitary FFT helpers ``rfft_norm`` and ``irfft_norm`` (norm='ortho'). These ensure the forward/inverse transforms are isometric and preserve L2 norms.

- **Tiny‑floor semantics**
  - All "tiny‑floor" values are expressed in amplitude (L2) units: ``compute_tiny_floor(D, dtype)`` returns an amplitude threshold comparable to ``||x||_2``.
  - When used in frequency‑domain denominators (power units), convert to per‑bin power via::

      power_per_bin = tiny_amp**2 / D

  - The compatibility unbinds convert amplitude tiny → per‑bin amplitude floor = ``tiny_amp / sqrt(D)`` and nudge complex denominators below that value.

- **Dtype and precision**

  High‑precision intermediates are used in spectral arithmetic: real power arrays and denominators are computed in ``float64``; complex spectral numerators are computed in ``complex128`` before division. The final inverse FFT result is cast back to the configured runtime dtype (``float32`` or ``float64``) and then renormalized according to ``HRRConfig.renorm``.

- **Deterministic seeding**
  - Deterministic RNG usage is enforced via ``np.random.default_rng(seed)``.
  - Text‑derived seeds use ``blake2b`` 64‑bit hashing for names (see ``_seed64``).

Unbind strategies
-----------------

- Exact / Tikhonov‑style
  - ``unbind_exact`` / ``unbind_exact_unitary`` perform spectral division with amplitude‑aware nudging and NaN/Inf guards. Use for unitary roles when the role spectrum has unit magnitude.

- Robust (spectral floor)
  - ``unbind`` computes a spectrum‑adaptive floor ``eps_used = max(power_floor_per_bin, beta * mean_power)`` to avoid division‑by‑zero and to provide deterministic stability for general role/filler vectors.

- Wiener (MAP)
  - ``unbind_wiener`` maps ``snr_db`` to a spectral floor and applies the conjugate‑filter ``conj(B) / (|B|^2 + floor)``; supports optional spectral floor.

Key assumptions and contract
----------------------------

- Dimensionality: D is the time‑domain vector length. For real‑FFT layouts (``rfft``/``irfft``) D is the full real vector length; the spectral bins used in frequency‑domain operations are the output length of ``rfft``.
- FFT convention: all spectral transforms use the unitary normalization (``norm='ortho'``). This makes the transforms energy‑preserving and simplifies Parseval‑based conversions between time‑ and frequency‑domain power.

Tiny‑floor (amplitude) and spectral power floor
-----------------------------------------------

The implementation uses a tiny amplitude floor (``tiny_amp``) with units of L2 amplitude (same units as a time‑domain vector norm). This prevents unstable divisions when the partner's spectrum has very low power in some frequency bins.

- ``compute_tiny_floor(D, dtype, strategy='sqrt')`` → ``tiny_amp`` returns a positive floating‑point amplitude (float64 in practice) that represents a conservative lower bound on the L2 norm of a legitimate symbol.
- Conversion to per‑frequency‑bin power (used in denominators):

  $$
  power\_floor = \frac{tiny\_amp^2}{D}
  $$

  Rationale: with unitary FFTs, the total time‑domain power ``tiny_amp^2`` is distributed across D real degrees‑of‑freedom; an average per‑bin power is ``tiny_amp^2 / D``. Using this unit‑consistent floor prevents mixing amplitude and power units in spectral denominators.

Spectral unbinding (robust stabilized inversion)
--------------------------------------------------

Let a and b be real time-domain vectors and denote their unitary rFFT's by
\(F[a](k)=\mathrm{fa}_k\) and \(F[b](k)=\mathrm{fb}_k\). The code computes
the following stabilized unbind:

1. Per-frequency power:

   $$
   S_k = \lvert\mathrm{fb}_k\rvert^{2}
   $$

2. Two candidate floors are computed:

   - Spectral floor from tiny amplitude: \(p_{tiny}=\frac{tiny\_amp^2}{D}\).
   - Data-dependent floor: \(p_{data}=\beta \cdot \mathrm{mean}_k(S_k)\)

   The implementation uses the combined floor

   $$\epsilon = \max(p_{tiny}, p_{data})\;.$$

3. Stabilized element-wise inversion (Tikhonov-like / conjugate division):

   $$
   \widehat{X}_k = \frac{\mathrm{fa}_k \cdot \overline{\mathrm{fb}_k}}{S_k + \epsilon}
   $$

   where \(\overline{\cdot}\) denotes complex conjugation. Using
   \(S_k+\epsilon\) prevents blow-ups when \(S_k\approx 0\).

Implementation details
----------------------

- Intermediate precision: spectral numerators/denominators are computed in
  float64/complex128 to reduce rounding error. The final inverse rFFT is
  converted back to the configured runtime dtype (float32/float64).
- Normalization: after inverse transform, the symbol is optionally renormalized
  to unit L2 according to ``HRRConfig.renorm``.
- Deterministic fallback: if a vector's L2 norm is below ``tiny_amp`` and
  ``strict_math`` is False, the deterministic baseline (all-ones scaled by
  1/sqrt(D)) is used to guarantee deterministic behavior across platforms.

Unbind variants (what they mean in practice)
--------------------------------------------

- unbind_exact: direct division by \(S_k\) with NaN/Inf guards. Use only
  when the role spectrum is unitary and callers accept potential numerical
  fragility.
- unbind (robust): the stabilized Tikhonov-style inversion above. This is
  the default for production where deterministic robustness is required.
- unbind_wiener: approximate MMSE-style (Wiener) deconvolution which uses an
  SNR-driven floor; useful when additive, frequency-dependent noise dominates
  and a softer attenuation yields better MSE/cosine performance.

Reproducible synthetic benchmarks (practical, real-world style)
----------------------------------------------------------------------

These recipes use synthetic data but emulate realistic failure modes (spectral
nulls, colored noise, low SNR) so the results reflect operational numerics
rather than idealized toy tests.

1) Canonical SNR sweep (existing harness)

   - Command (venv):

   ```bash
   PYTHONPATH=. ./venv/bin/python benchmarks/numerics_workbench.py --stress --out benchmarks/results_numerics.json
   ```

   - Output: ``benchmarks/results_numerics.json`` (contains cosine/MSE per
     D, seed, SNR) and plots via ``benchmarks/plot_results.py``.

2) Spectral-nulling test (targets exact-division fragility)

   - Purpose: zero a fraction of frequency bins in the role vector to create
     extreme per-bin power deficits. Exact division will blow up; stabilized
     or Wiener methods remain robust.

   - Minimal runnable snippet (save as e.g. ``benchmarks/nulling_test.py``):

   .. code-block:: python

      import numpy as np
      from somabrain.numerics import rfft_norm, irfft_norm
      from somabrain.quantum import HRRConfig, QuantumLayer

      D = 1024
      cfg = HRRConfig(dim=D)
      q = QuantumLayer(cfg)

      rng = np.random.default_rng(1234)
      a = q.random_vector(rng=rng)
      b = q.random_vector(rng=rng)

      fb = rfft_norm(b)
      # zero 20% of bins at random
      n_null = int(0.2 * fb.shape[-1])
      idx = rng.choice(fb.shape[-1], size=n_null, replace=False)
      fb[idx] = 0.0
      b_null = irfft_norm(fb)

      bound = q.bind(a, b_null)
      est_exact = q.unbind_exact(bound, b_null)
      est_robust = q.unbind(bound, b_null)
      est_wiener = q.unbind_wiener(bound, b_null)

      def cosine(x, y):
          return float(np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y)))

      print('cosine_exact', cosine(a, est_exact))
      print('cosine_robust', cosine(a, est_robust))
      print('cosine_wiener', cosine(a, est_wiener))

3) Correlated-noise (colored noise) test

   - Purpose: create filler or channel noise with non-white spectral shape
     (e.g. 1/f) and observe that Wiener/robust unbinds produce better MSE and
     cosine when noise is concentrated in specific frequency bands.

   - Sketch: generate noise in spectral domain with power ~ 1/(k+1), inverse
     FFT to time-domain, add to bound vector, then run unbind variants.

Interpreting results
--------------------

- Metrics: compare cosine similarity (closer to 1 is better) and MSE (lower
  is better) between original symbol and reconstructed symbol.
- Expectation: for uniform, high-SNR signals exact and robust methods are
  similar; for spectral nulls or highly frequency-dependent noise, robust
  and Wiener outperform exact division.

Mapping to code (quick pointers)
================================

- ``somabrain/numerics.py``: ``compute_tiny_floor``,
  ``spectral_floor_from_tiny``, ``rfft_norm``, ``irfft_norm``,
  ``normalize_array``.
- ``somabrain/quantum.py``: ``QuantumLayer.unbind``, ``unbind_exact``,
  ``unbind_wiener`` and configuration parameters ``HRRConfig.beta``,
  ``HRRConfig.tiny_floor_strategy``, ``HRRConfig.strict_math``.

Practical recommendations
-------------------------

- Use the robust unbind (default) in production. Use ``strict_math`` only for
  research experiments where exact algebraic equivalence must be demonstrated.
- Add targeted bench artifacts (nulling tests and colored-noise tests) to
  the canonical benchmark set to provide real-world-style evidence for metric
  trade-offs.

Change log
----------

- 2025-09-13: Rewrote numerics reference to reflect code-first math, added
  spectral-floor equations, and included reproducible synthetic benchmark
  snippets (nulling and colored-noise tests).
