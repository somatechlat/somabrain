Numerics Hardening Report
=========================

Summary
-------

This short report documents the numeric hardening applied to SomaBrain's HRR
primitives and records the math choices made in code.

Changes
-------

- compute_tiny_floor: canonicalized to return an amplitude tiny (L2 units). The
  canonical strategy is ``strategy='sqrt'`` which scales tiny as eps * sqrt(D).
  When used in spectral code callers convert via

    power_per_bin = tiny_amp**2 / D

- normalize_array: uses float64 accumulation, mixes tiny_amp**2 into denominators,
  and offers three fallbacks for low-energy slices: ``legacy_zero``, ``robust``
  (default), and ``strict``. The robust fallback returns the deterministic unit
  baseline vector ones/sqrt(D).

- Spectral denominators (deconvolution) use power units and derive their minimal
  per-bin floor from the amplitude tiny as shown above.

Validation
----------

- Unit tests covering the numerics changes were added and executed locally.
- Microbench and smoke bench runs were executed and artifacts generated.

Next steps
----------

- Optionally run the full benchmark sweep and attach canonical artifacts (JSON/PNG)
  to release notes. This requires more compute time.
- Decide whether to change the project default behavior to ``mode='robust'``
  (the current code default is robust; the PR can preserve legacy_zero during a
  migration window if desired).

Reference
---------

See ``somabrain/numerics.py`` and ``somabrain/quantum.py`` for the precise
implementation.
