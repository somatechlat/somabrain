
PR Draft: numerics hardening

Title: numerics: harden normalize + unitary FFTs, add mode, caching, benchmarks & math spec

Summary
-------
Improve numeric robustness for HRR pipelines: float64 accumulation, tiny-floor
policy (eps * sqrt(D) by default), final renormalization to reduce rounding
drift, `normalize_array(mode=...)` with compatibility modes, and benchmarks +
math spec.

Why
---
Reduce NaN/Inf and rounding-drift failures in production HRR pipelines; make
numeric behavior explicit, auditable and testable.

Files changed
-------------
- `somabrain/numerics.py` (core changes)
- `benchmarks/*` (bench scripts / workbench)
- `docs/source/math.rst` (math reference)
- `docs/source/REPORT_NUMERICS_HARDENING.rst` (report)

Checklist for reviewers
----------------------
- [ ] Unit tests pass locally
- [ ] Benchmarks included and sample outputs attached
- [ ] CHANGELOG updated
- [ ] Math spec reviewed for correctness and clarity

Benchmarks (sample output)
--------------------------
D=2048 N=500: normalize per-call 0.0361s, batched 0.0351s; rfft per-call 0.0167s, batched 0.0039s

Migration notes
---------------
- Consumers can opt into robust fallback with `normalize_array(..., mode='robust')`.
- The implementation default is ``mode='robust'`` (deterministic baseline) and
	``strategy='sqrt'`` for tiny-floor. If preserving exact legacy behavior is
	required for a release, the PR can preserve ``legacy_zero`` as the default
	while documenting the change and providing a migration window.

Run locally
-----------
. .venv/bin/activate
python -m pytest -q
python benchmarks/numerics_bench.py
