Math reference — Numerics
=========================

This page documents the numeric contract and design choices used by the SomaBrain core.

Key invariants
--------------

- Tiny-floor semantics: ``compute_tiny_floor(D)`` returns an amplitude threshold (L2 units).
  When you need a per-FFT-bin spectral floor (power units) convert explicitly::

    power_per_bin = tiny_amp**2 / D

- FFTs are unitary: use ``rfft_norm`` / ``irfft_norm`` with ``norm='ortho'``.
  Unitary FFTs make circular convolution a norm-preserving linear map and simplify
  analytic reasoning about binding/unbinding.

- Normalization: ``normalize_array`` uses float64 accumulation and compares slice energy
  ``E = sum(|x|^2)`` against ``tiny_amp**2``. If ``E < tiny_amp**2`` the fallback is:
  * ``'legacy_zero'`` -> zero-vector
  * ``'robust'`` -> deterministic baseline ``ones/sqrt(D)``
  * ``'strict'`` -> raise ValueError

- Spectral denominators (for deconvolution) operate in power units: ``denom := |R|^2 + lambda``
  where ``lambda`` is chosen from ``tiny_amp`` (squared and divided by ``D``) and optionally
  SNR-derived heuristics. Explicitly converting amplitude -> power keeps the units auditable.

Determinism and fallback
------------------------

- Baseline fallback is deterministic: ``ones / sqrt(D)``. This makes low-energy slices
  produce explainable vectors rather than noisy artifacts.

- Role spectra and other pseudo-random choices are seeded deterministically using a
  keyed blake2b hashing of ``(global_seed, name)``.

Why amplitude vs power?
------------------------

The API for normalization is naturally L2-amplitude oriented. Spectral math is power-oriented.
Returning an amplitude tiny and requiring explicit conversion to power for spectral floors makes
the unit change explicit and avoids silent bugs.

See ``somabrain/numerics.py`` for the canonical implementation.

Production readiness
--------------------

These numeric improvements are designed to make SomaBrain safe for production workloads:

- Deterministic fallbacks (``ones/sqrt(D)``) prevent noisy or non-reproducible outputs when
  energy is very low, which reduces variance in downstream systems and makes debugging easier.
- Unitary FFT wrappers preserve L2 energy across transforms, enabling analytically correct
  binding/unbinding and stable error bounds when decoding HRRs.
- Explicit amplitude-to-power conversions make unit changes visible and auditable, reducing
  accidental unit-mismatch bugs in spectral math and deconvolution.
- Float64 accumulation and conservative tiny-floor policies avoid catastrophic underflow or
  divide-by-zero during cleanups and deconvolutions, improving numerical stability across
  BLAS/FFTW backends and platforms.

Together these changes reduce floating-point brittleness, make behavior reproducible across
hardware, and simplify reasoning about safety margins — all necessary properties for a
production-ready numeric core.
Math reference  Numerics
=========================

This page documents the numeric contract and design choices used by the
SomaBrain core.

Key invariants
--------------

- Tiny-floor semantics: ``compute_tiny_floor`` returns an amplitude threshold (L2-norm units).
  For spectral operations that operate per-FFT-bin in power, callers MUST convert.

  .. code-block:: none

     power_per_bin = tiny_amp**2 / D

- FFTs: we use unitary real-FFT wrappers ``rfft_norm`` and ``irfft_norm`` with ``norm='ortho'``.
  This preserves energy and simplifies mathematical reasoning about convolution and deconvolution.

- Normalization: ``normalize_array(x, axis, ...)`` computes sum-of-squares (energy) per slice,
  compares it with ``tiny_amp**2``, and uses either a deterministic baseline vector
  (``ones/sqrt(D)``) or a zero-vector depending on the chosen mode. All energy mixing is done
  in power units and amplitude thresholds are squared before mixing.

- Spectral floors: when dividing in the frequency domain during unbinding, denominators are
  formed from spectral power (``|F(B)|^2``) with a floor in power-per-bin units. That floor is derived
  from the amplitude tiny by squaring and dividing by ``D``.

Determinism and fallback
------------------------

- Baseline fallback is deterministic: the baseline unit-vector is ``ones / sqrt(D)`` and is used
  when the slice energy is below the subtiny threshold. This produces deterministic, explainable
  outputs for low-energy inputs.

- Seeding for pseudo-random role vectors is deterministic where used in tests and benchmarks;
  the default numerics operations are pure deterministic numeric transforms.

Why amplitude vs power?
------------------------

Using an amplitude tiny keeps the API consistent with L2-normalization semantics (||x||_2).
Spectral operations naturally operate on power (square of amplitudes); therefore the explicit
conversion step (square and divide by ``D``) makes the unit change visible and auditable.

See ``somabrain/numerics.py`` for the implementation.
