Math reference — Numerics
=========================

This page documents the canonical numeric contract implemented in
``somabrain/numerics.py``. Text below is a concise, auditable translation of the
code into mathematics and short usage notes. Where the code provides a choice
(``strategy`` or ``mode``) the documented default is the value used by the
implementation.

Core definitions
----------------

- Dimension: let D be the real vector dimension (positive integer).
- Machine epsilon: for a dtype dtype, eps(dtype) = np.finfo(dtype).eps.
- Amplitude tiny (L2 units): tiny_amp(D, dtype, scale, strategy) is computed as

  - If strategy == "linear":

    tiny_amp = max(tiny_min(dtype), eps(dtype) * scale * D)

  - Otherwise (default, ``"sqrt"``):

    tiny_amp = max(tiny_min(dtype), eps(dtype) * scale * sqrt(D))

  where tiny_min(dtype) is a small dtype-dependent floor used to avoid
  underflow (implementation: 1e-6 for float32, 1e-12 for float64).

- Spectral (per-FFT-bin) power floor: when operating in the frequency domain the
  canonical power-per-bin floor is

    power_floor_per_bin = tiny_amp**2 / D

  The explicit square keeps amplitude (L2) and spectral (power) units distinct.

Unitary FFTs
------------

We use unitary real-FFT wrappers

  X = rfft_norm(x) := rfft(x, norm="ortho")
  x = irfft_norm(X) := irfft(X, norm="ortho", n=D)

which enforce (up to rounding error) the L2 isometry ||x||_2 == ||X||_2 (with
the complex norm on X). This property simplifies analytic reasoning about
binding (multiplication in the spectral domain) and circular correlation.

Normalization contract
----------------------

Given a real slice x (shape (...) + (D,)) we define the slice energy

  E := sum(|x|^2)  (computed in float64)

The canonical normalization computes

  denom := sqrt(E + tiny_amp**2)
  x_hat := x / denom

and then applies a per-slice fallback when E < tiny_amp**2 depending on the
selected mode (code default is "robust"):

- legacy_zero: replace the subtiny slice with the zero-vector (historical).
- robust (default): replace the subtiny slice with the deterministic baseline
  vector b = ones(D) / sqrt(D) (this has unit L2 norm and is deterministic).
- strict: raise ValueError when any slice is subtiny.

After fallback the implementation applies a final L2 renormalization (float64
intermediates) to ensure each output slice is unit norm, and replaces any
non-finite entries with the deterministic baseline. All accumulation is done in
float64 for conservatism.

Spectral denominators and deconvolution
--------------------------------------

When unbinding by division in the spectral domain (e.g. exact deconvolution)
the code uses power-units for denominators. For a role spectrum R (complex)
the canonial mixing uses

  denom_k := |R_k|^2 + lambda_k

where lambda_k is a power-per-bin floor (at minimum power_floor_per_bin) and
may be further adjusted by SNR heuristics (Wiener/Tikhonov regularization).

This keeps spectral units consistent and makes small-denominator handling
auditable (the amplitude tiny is always the source of the spectral floor).

Deterministic role spectra and unitary roles
-------------------------------------------

Role spectra are constructed deterministically from a keyed seed. Let
seed = H(global_seed || ":" || name) where H is blake2b. Draw uniform phases
phi_k ~ Uniform(0, 2π) for the non-redundant rFFT bins, set H_k = exp(i phi_k)
and force DC (and Nyquist when present) to be real (1.0). The resulting
spectrum has |H_k| == 1. The time-domain role r = irfft_norm(H) is finally
renormalized with ``normalize_array(..., mode='robust')`` to guarantee unit
L2 (defensive against tiny machine differences in FFT implementations).

Practical notes
---------------

- API: ``compute_tiny_floor(D, dtype=np.float32, scale=1.0, strategy='sqrt')``
  returns an amplitude tiny (float). Callers converting to a spectral floor
  must square and divide by D.

- Default normalization ``mode`` in this implementation is ``'robust'``.

- Use the unitary FFT wrappers provided by the module: ``rfft_norm`` and
  ``irfft_norm`` to keep energy bookkeeping trivial.

Reference implementation
------------------------

The canonical code is ``somabrain/numerics.py``; this document is intended to be
a short, mathematical translation of that implementation. For exact API
signatures and backward-compatibility details consult the source.
