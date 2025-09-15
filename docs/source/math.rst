Math reference  Numerics
===========================

This page documents the canonical numeric contract implemented in
``somabrain/numerics.py``. The text below is a concise, auditable translation of
the code into mathematics and short usage notes. When the code exposes a
choice (``strategy`` or ``mode``) the documented default matches the
implementation.

Core definitions
----------------

- Dimension: let :math:`D` be the real vector dimension (positive integer).
- Machine epsilon: for a dtype ``dtype``, :math:`\varepsilon(dtype)=\mathrm{np.finfo(dtype).eps}`.
- Amplitude tiny (L2 units): :math:`\mathrm{tiny\_amp}(D, dtype, scale, strategy)` is computed as::

    - If :math:`\mathrm{strategy} = "linear"`:

        :math:`\mathrm{tiny\_amp} = \max\big(\mathrm{tiny\_min}(dtype),\,\varepsilon(dtype)\cdot\mathrm{scale}\cdot D\big)`

    - Otherwise (default, ``"sqrt"``)::

        :math:`\mathrm{tiny\_amp} = \max\big(\mathrm{tiny\_min}(dtype),\,\varepsilon(dtype)\cdot\mathrm{scale}\cdot\sqrt{D}\big)`

    where :math:`\mathrm{tiny\_min}(dtype)` is a small dtype-dependent floor used to avoid
    underflow (implementation: 1e-6 for float32, 1e-12 for float64).

- Spectral (per-FFT-bin) power floor: when operating in the frequency domain the
  canonical power-per-bin floor is::

    :math:`\mathrm{power\_floor\_per\_bin} = \dfrac{\mathrm{tiny\_amp}^2}{D}`

Unitary FFTs
------------

We use unitary real-FFT wrappers::

  X = rfft_norm(x) := rfft(x, norm="ortho")
  x = irfft_norm(X) := irfft(X, norm="ortho", n=D)

which enforce (up to rounding error) the L2 isometry :math:`\|x\|_2 = \|X\|_2` (with
the complex norm on :math:`X`). This property simplifies analytic reasoning about
binding (multiplication in the spectral domain) and circular correlation.

Normalization contract
----------------------

Given a real slice :math:`x` (shape (...) + (D,)) define the slice energy::

  :math:`E=\sum |x|^2`  (computed in float64).

The canonical normalization computes::

  denom := sqrt(E + tiny_amp**2)
  x_hat := x / denom

and applies a per-slice fallback when :math:`E < \mathrm{tiny\_amp}^2` depending on
the selected mode (code default is ``'robust'``):

- ``legacy_zero``: replace the subtiny slice with the zero-vector.
- ``robust`` (default): replace the subtiny slice with the deterministic baseline
  :math:`b=\mathbf{1}_D/\sqrt{D}` (unit L2 norm).
- ``strict``: raise ``ValueError`` when any slice is subtiny.

After fallback the implementation applies a final L2 renormalization (float64
intermediates) to ensure each output slice is unit norm and replaces any
non-finite entries with the deterministic baseline.

Spectral denominators and deconvolution
--------------------------------------

When unbinding by division in the spectral domain the code uses power-units for
denominators. For a role spectrum :math:`R` (complex) the canonical mixing uses::

  denom_k := |R_k|^2 + lambda_k

where :math:`\lambda_k` is a per-bin power floor (at minimum
:math:`\mathrm{power\_floor\_per\_bin}`) and may be adjusted by SNR
heuristics (Wiener/Tikhonov regularization). Using power units keeps spectral
units consistent and makes small-denominator behavior auditable.

Deterministic role spectra and unitary roles
-------------------------------------------

Role spectra are built deterministically from a keyed seed. Let
``seed = H(global_seed || ':' || name)`` where ``H`` is blake2b. Draw uniform
phases :math:`\phi_k \sim \mathrm{Uniform}(0,2\pi)` for the non-redundant
rFFT bins; set :math:`H_k = e^{i\phi_k}` and force DC (and Nyquist when
present) to be real (1.0). The resulting spectrum has :math:`|H_k|=1`. The
time-domain role ``r = irfft_norm(H)`` is renormalized with
``normalize_array(..., mode='robust')`` to guarantee unit L2.

Practical notes
---------------

- API: ``compute_tiny_floor(D, dtype=np.float32, scale=1.0, strategy='sqrt')``
  returns the amplitude tiny (float). Convert to a spectral floor by squaring
  and dividing by ``D``.

- Default normalization ``mode`` is ``'robust'``.

- Use the provided unitary FFT wrappers ``rfft_norm`` and ``irfft_norm`` for
  consistent energy bookkeeping.

Reference implementation
------------------------

The canonical code is ``somabrain/numerics.py``; consult the source for exact
API signatures and backward-compatibility notes.

.. code-block:: none

    # Reference: somabrain/numerics.py

=========================

This page documents the canonical numeric contract implemented in
``somabrain/numerics.py``. The text below is a concise, auditable translation of
the code into mathematics and short usage notes. When the code exposes a
choice (``strategy`` or ``mode``) the documented default matches the
implementation.

Core definitions
----------------

- Dimension: let :math:`D` be the real vector dimension (positive integer).
- Machine epsilon: for a dtype ``dtype``, :math:`\varepsilon(dtype)=\mathrm{np.finfo(dtype).eps}`.
- Amplitude tiny (L2 units): :math:`\mathrm{tiny\_amp}(D, dtype, scale, strategy)` is computed as

  - If :math:`\mathrm{strategy} = \text{"linear"}`::

      :math:`\mathrm{tiny\_amp} = \max\big(\mathrm{tiny\_min}(dtype),\,\varepsilon(dtype)\cdot\mathrm{scale}\cdot D\big)`
Math reference — Numerics
=========================

This page documents the canonical numeric contract implemented in
``somabrain/numerics.py``. The text below is a concise, auditable translation of
the code into mathematics and short usage notes. When the code exposes a
choice (``strategy`` or ``mode``) the documented default matches the
implementation.

Core definitions
----------------

- Dimension: let :math:`D` be the real vector dimension (positive integer).
- Machine epsilon: for a dtype ``dtype``, :math:`\varepsilon(dtype)=\mathrm{np.finfo(dtype).eps}`.
- Amplitude tiny (L2 units): :math:`\mathrm{tiny\_amp}(D, dtype, scale, strategy)` is computed as

  - If :math:`\mathrm{strategy} = \"linear\"`::

      :math:`\mathrm{tiny\_amp} = \max\big(\mathrm{tiny\_min}(dtype),\,\varepsilon(dtype)\cdot\mathrm{scale}\cdot D\big)`

  - Otherwise (default, ``"sqrt"``)::

      :math:`\mathrm{tiny\_amp} = \max\big(\mathrm{tiny\_min}(dtype),\,\varepsilon(dtype)\cdot\mathrm{scale}\cdot\sqrt{D}\big)`

  where :math:`\mathrm{tiny\_min}(dtype)` is a small dtype-dependent floor used to avoid
  underflow (implementation: 1e-6 for float32, 1e-12 for float64).

- Spectral (per-FFT-bin) power floor: when operating in the frequency domain the
  canonical power-per-bin floor is

    :math:`\mathrm{power\_floor\_per\_bin} = \dfrac{\mathrm{tiny\_amp}^2}{D}`

Unitary FFTs
------------

We use unitary real-FFT wrappers::

  X = rfft_norm(x) := rfft(x, norm="ortho")
  x = irfft_norm(X) := irfft(X, norm="ortho", n=D)

which enforce (up to rounding error) the L2 isometry :math:`\|x\|_2 = \|X\|_2` (with
the complex norm on :math:`X`). This property simplifies analytic reasoning about
binding (multiplication in the spectral domain) and circular correlation.

Math reference  Numerics
===========================

This page documents the canonical numeric contract implemented in
``somabrain/numerics.py``. The text below is a concise, auditable translation of
the code into mathematics and short usage notes. When the code exposes a
choice (``strategy`` or ``mode``) the documented default matches the
implementation.

Core definitions
----------------

- Dimension: let :math:`D` be the real vector dimension (positive integer).
- Machine epsilon: for a dtype ``dtype``, :math:`\varepsilon(dtype)=\mathrm{np.finfo(dtype).eps}`.
- Amplitude tiny (L2 units): :math:`\mathrm{tiny\_amp}(D, dtype, scale, strategy)` is computed as

  - If :math:`\mathrm{strategy} = "linear"`::

      :math:`\mathrm{tiny\_amp} = \max\big(\mathrm{tiny\_min}(dtype),\,\varepsilon(dtype)\cdot\mathrm{scale}\cdot D\big)`

  - Otherwise (default, ``"sqrt"``)::

      :math:`\mathrm{tiny\_amp} = \max\big(\mathrm{tiny\_min}(dtype),\,\varepsilon(dtype)\cdot\mathrm{scale}\cdot\sqrt{D}\big)`

  where :math:`\mathrm{tiny\_min}(dtype)` is a small dtype-dependent floor used to avoid
  underflow (implementation: 1e-6 for float32, 1e-12 for float64).

- Spectral (per-FFT-bin) power floor: when operating in the frequency domain the
  canonical power-per-bin floor is

    :math:`\mathrm{power\_floor\_per\_bin} = \dfrac{\mathrm{tiny\_amp}^2}{D}`

Unitary FFTs
------------

We use unitary real-FFT wrappers::

  X = rfft_norm(x) := rfft(x, norm="ortho")
  x = irfft_norm(X) := irfft(X, norm="ortho", n=D)

which enforce (up to rounding error) the L2 isometry :math:`\|x\|_2 = \|X\|_2` (with
the complex norm on :math:`X`). This property simplifies analytic reasoning about
binding (multiplication in the spectral domain) and circular correlation.

Normalization contract
----------------------

Given a real slice :math:`x` (shape (...) + (D,)) define the slice energy

:math:`E=\sum |x|^2`  (computed in float64).

The canonical normalization computes::

  denom := sqrt(E + tiny_amp**2)
  x_hat := x / denom

and applies a per-slice fallback when :math:`E < \mathrm{tiny\_amp}^2` depending on
the selected mode (code default is ``'robust'``):

- ``legacy_zero``: replace the subtiny slice with the zero-vector.
- ``robust`` (default): replace the subtiny slice with the deterministic baseline
  :math:`b=\mathbf{1}_D/\sqrt{D}` (unit L2 norm).
- ``strict``: raise ``ValueError`` when any slice is subtiny.

After fallback the implementation applies a final L2 renormalization (float64
intermediates) to ensure each output slice is unit norm and replaces any
non-finite entries with the deterministic baseline.

Spectral denominators and deconvolution
======================================

When unbinding by division in the spectral domain the code uses power-units for
denominators. For a role spectrum :math:`R` (complex) the canonical mixing uses::

  denom_k := |R_k|^2 + lambda_k

where :math:`\lambda_k` is a per-bin power floor (at minimum
:math:`\mathrm{power\_floor\_per\_bin}`) and may be adjusted by SNR
heuristics (Wiener/Tikhonov regularization). Using power units keeps spectral
units consistent and makes small-denominator behavior auditable.

Deterministic role spectra and unitary roles
===========================================

Role spectra are built deterministically from a keyed seed. Let
``seed = H(global_seed || ':' || name)`` where ``H`` is blake2b. Draw uniform
phases :math:`\phi_k \sim \mathrm{Uniform}(0,2\pi)` for the non-redundant
rFFT bins; set :math:`H_k = e^{i\phi_k}` and force DC (and Nyquist when
present) to be real (1.0). The resulting spectrum has :math:`|H_k|=1`. The
time-domain role ``r = irfft_norm(H)`` is renormalized with
``normalize_array(..., mode='robust')`` to guarantee unit L2.

Practical notes
---------------

- API: ``compute_tiny_floor(D, dtype=np.float32, scale=1.0, strategy='sqrt')``
  returns the amplitude tiny (float). Convert to a spectral floor by squaring
  and dividing by ``D``.

- Default normalization ``mode`` is ``'robust'``.

- Use the provided unitary FFT wrappers ``rfft_norm`` and ``irfft_norm`` for
  consistent energy bookkeeping.

Reference implementation
------------------------

The canonical code is ``somabrain/numerics.py``; consult the source for exact
API signatures and backward-compatibility notes.

.. code-block:: none

    # Reference: somabrain/numerics.py
