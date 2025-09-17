PR Draft: numerics hardening

Title: numerics: harden normalize + unitary FFTs, add mode, caching, benchmarks & math spec

Summary
-------
Improve numeric robustness for HRR pipelines: float64 accumulation, tiny-floor policy (eps*sqrt(D)) with caching, final renormalization to reduce rounding drift, `normalize_array(mode=...)` with compatibility modes, and benchmarks + math spec.

Why
---
Reduce NaN/Inf and rounding-drift failures in production HRR pipelines; make numeric behavior explicit and testable.

Files changed
-------------
- `somabrain/numerics.py` (core changes)
- `benchmarks/*` (bench scripts)
- `docs/NUMERICS_MATH_SPEC.md`


Checklist for reviewers
----------------------
- [ ] Unit tests pass locally (I ran full test suite in .venv)
- [ ] Benchmarks included and sample outputs attached
- [ ] CHANGELOG updated
- [ ] Docs/NUMERICS_MATH_SPEC.md reviewed for math contracts
- [ ] Backwards compatibility verified: default `mode='legacy_zero'`

Benchmarks (sample output)
--------------------------
D=2048 N=500: normalize per-call 0.0361s, batched 0.0351s; rfft per-call 0.0167s, batched 0.0039s

Migration notes
---------------
- Consumers can opt into robust fallback with `normalize_array(..., mode='robust')`.
- Plan a follow-up to switch default to `robust` after a deprecation window.

Requested reviewers
-------------------
- core numerics owner
- performance owner
- CI owner

Run locally
-----------
. .venv/bin/activate
python -m pytest -q
python benchmarks/numerics_bench.py
