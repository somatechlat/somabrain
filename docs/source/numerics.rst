Numerics
========

Canonical numerics guidance and quick runnable example for SomaBrain's
HRR (High-dimensional Representations) implementation. This page is concise
and intended to be linkable from the API reference and benchmarks.

Key assumptions
---------------

- Dimensionality: D is the time-domain vector length. For real-FFT layouts
  (``rfft``/``irfft``) D is the full real vector length; the spectral bins are
  the output length of ``rfft``.
- FFT convention: unitary normalization (``norm='ortho'``) to preserve energy.

Tiny-floor and spectral floor
-----------------------------


We use a tiny amplitude floor (``tiny_amp``) in amplitude units (L2). Convert
it to a per-frequency-bin power floor::

  power_floor = tiny_amp**2 / D

This keeps units consistent when used in spectral denominators.

Spectral unbinding (robust stabilized inversion)
-----------------------------------------------

Let a and b be real time-domain vectors and denote their unitary rFFT's by
F[a](k)=fa_k and F[b](k)=fb_k. The stabilized unbind proceeds:

1. Per-frequency power: S_k = :math:`|fb_k|**2`
2. Candidate floors: :math:`p_tiny = tiny_amp**2 / D`, :math:`p_data = beta * mean(S_k)`
3. Combined floor: :math:`eps = max(p_tiny, p_data)`
4. Stabilized inversion::

  X_hat_k = (fa_k * conj(fb_k)) / (S_k + eps)

Numerical best practices
------------------------

- Compute spectral numerators/denominators in float64/complex128 to reduce
  rounding error, then cast back to the configured runtime dtype.
- After inverse rFFT, renormalize to unit L2 if required by configuration.
- Prefer robust unbind (default) in production; use exact methods only for
  controlled experiments.

Benchmarks (quick pointers)
---------------------------

- Canonical SNR sweep: ``benchmarks/numerics_workbench.py`` produces
  ``benchmarks/results_numerics.json``.
- Nulling and colored-noise tests: see ``benchmarks/nulling_test.py`` and
  ``benchmarks/colored_noise_bench.py`` for runnable examples.

Minimal runnable example
------------------------

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
   est_robust = q.unbind(bound, b_null)

   def cosine(x, y):
       return float(np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y)))

   print('cosine_robust', cosine(a, est_robust))
