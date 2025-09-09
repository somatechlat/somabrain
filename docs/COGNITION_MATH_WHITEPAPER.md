# SOMA Brain Cognition Math Whitepaper

This document summarizes the core mathematics used in the SOMA Brain project. It's written for mathematicians and engineers who want precise, reproducible descriptions of the algorithms and numerical choices.

1. HRR binding and unbinding
- Symbol vectors live in R^D.
- Binding is circular convolution implemented via the (real) Fourier transform: bind(a, b) = irfft( rfft(a) * rfft(b) ), using unitary normalization (norm='ortho').
- Unbinding of c = bind(a,b) recovers a by computing a ≈ irfft( rfft(c) * conj(rfft(b)) / |rfft(b)|^2 ).

2. Unitarity and normalization
- We choose unitary FFT normalization (orthonormal transform) so that Parseval's theorem holds exactly and binding preserves Euclidean norms for unitary role spectra.
- Roles are constructed to have unit-magnitude spectra: for each frequency bin k, set R[k] = exp(i*theta_k), then time-domain r = irfft(R) is the role vector. This ensures |rfft(r)| has magnitude 1 and binding by r is unitary.

3. Tiny-floor and numerical stability
- To avoid division by near-zero values during unbinding, we introduce a tiny-floor per dtype and per dimension: tiny = max(eps(dtype) * sqrt(D), dtype_min), where dtype_min is a conservative lower bound (e.g., 1e-6 for float32, 1e-12 for float64).
- When a vector's L2 norm along the normalized axis is below tiny, we fallback to a deterministic baseline (e.g., ones/sqrt(D)) to preserve directionality and avoid noisy zeros.

4. Deterministic seeding
- Seeds of arbitrary type (int, str, bytes) are hashed to a uint64 using BLAKE2b(digest_size=8) and used to instantiate numpy.random.default_rng. This guarantees reproducible role and noise generation across platforms.

5. Wiener / Tikhonov fallback
- Exact spectral unbinding divides by |B(f)|^2, which amplifies noise when |B(f)| is small. We implement Wiener/Tikhonov regularization in frequency domain: X(f) = C(f) * conj(B(f)) / (|B(f)|^2 + lambda), with lambda chosen from SNR heuristics or set conservatively.

6. Batched transforms and performance
- Use batched rfft/irfft with norm='ortho' on the binding axis. Where possible, perform frequency-domain arithmetic in float64 for stability and cast back to requested dtype only for outputs.

Appendix: Recommended parameter defaults
- tiny_floor strategy: 'sqrt' (tiny = eps * sqrt(D))
- dtype_min: float32 => 1e-6, float64 => 1e-12
- default role seeds: use reproducible integer seeds or string identifiers hashed to uint64

Notes
- These choices prioritize reproducibility and numerical robustness across platforms. They are intentionally conservative; performance tuning can relax some safeguards where test coverage and benchmarking justify it.
