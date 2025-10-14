# BHDC Binding Cheat Sheet

This appendix captures the math implemented in `somabrain/quantum.py` so developers can validate behaviour quickly.

## 1. Hypervector Construction
- Dimension: `HRRConfig.dim` (default 2048) set in `QuantumLayer`.
- Seeded RNG: `QuantumLayer` seeds `numpy.random.Generator` with `HRRConfig.seed` for deterministic runs.
- Sparsity: Binary hypervectors contain exactly `round(dim * sparsity)` ones; the rest are -1.

## 2. Role Generation
Given a role string `r`, `QuantumLayer.make_unitary_role(r)`:
1. Hashes `r` with SHA-256.
2. Uses the digest to seed a temporary RNG.
3. Produces a binary permutation vector that is its own inverse.

## 3. Binding & Unbinding
- **Bind:** `QuantumLayer.bind_unitary(vec, role)` performs circular convolution (`fft` / `ifft`) between the value vector and the role vector.
- **Unbind:** `QuantumLayer.unbind_unitary(bound, role)` applies the conjugate of the role and reconvolves, reversing the operation.
- Associativity holds because convolution is associative; inverses hold because unitary roles satisfy `role * role⁻¹ = identity`.

## 4. Superposition & Cleanup
- Superposition: `QuantumLayer.superpose` averages multiple bound vectors and renormalizes to ±1.
- Cleanup: `QuantumLayer.cleanup(candidate, memory)` selects the stored vector with maximum cosine similarity.
- The cleanup loop is deterministic; ties break by stable ordering of the input memory list.

## 5. Tests & Guarantees
- `tests/test_bhdc_binding.py` asserts `unbind(bind(v, r), r) == v` for deterministic samples.
- Numerical stability validated via `pytest -k quantum` and benchmarks in `benchmarks/numerics_bench.py`.

Use this appendix whenever extending `QuantumLayer`; update it in the same commit as code changes.
