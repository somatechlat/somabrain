# SOMA Brain — Architecture Overview

High level: the project organizes cognitive subsystems (hippocampus, prefrontal, attention, planner) which exchange vectorized symbolic representations via an HRR-style working memory. Core modules:
- `somabrain/` — cognitive modules and glue
- `somafractalmemory/` — companion memory project
- `tests/` and `benchmarks/` for validation and performance

Key engineering choices
- HRR and role-based binding as the substrate for compositional representations.
- Deterministic seeding for reproducibility.
- Numeric primitives centralized in `somabrain/numerics.py` to ensure consistent floors, normalization, and unitary FFTs.

Deployment
- CI runs `pytest` and builds Sphinx docs. Benchmarks produce CSV/PNG artifacts retained by CI.
