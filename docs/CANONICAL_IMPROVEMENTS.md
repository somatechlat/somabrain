# Canonical Improvements Log

Purpose: a single place to record hardening changes that actually landed in the repo (no placeholders).

## 2025-11-23
- Enforced `ENABLE_COG_THREADS=1` by default so all cognition/learning threads stay active without gating.
- Defaulted memory backend to `http://localhost:9595` so local/full-local stacks bind to the external memory service without extra env wiring.
- Fixed constitution signer path lookup to read `SOMABRAIN_CONSTITUTION_PRIVKEY_PATH` (no indentation error).
- Fixed journal config parsing to read settings/env safely (no syntax break).
- Centralised working-memory/microcircuit/HRR config: defaults now flow from `settings` (alpha/beta/gamma, recency, tenant caps, vote temperature, planner RWR knobs) eliminating hard-coded literals.
- Adaptive neuromodulator parameters (init/min/max/lr, latency/accuracy/urgency factors) now sourced from `settings`; feedback functions use overridable scales.
- Budgeted predictor timeout now follows `settings.predictor_timeout_ms`; new invariant tests fail on stray `os.getenv` and verify defaults track settings.

## Usage
- When you add or harden a capability, append a dated bullet list here.
- Keep entries factual and tied to merged code.
