 # SomaBrain — Observable Memory & Planning for AI Agents

[![CI](https://github.com/somatechlat/somabrain/actions/workflows/ci.yml/badge.svg)](https://github.com/somatechlat/somabrain/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://somatechlat.github.io/somabrain/)
[![Tag](https://img.shields.io/github/v/tag/somatechlat/somabrain?sort=semver)](https://github.com/somatechlat/somabrain/tags)
[![Container](https://img.shields.io/badge/container-ghcr.io%2Fsomatechlat%2Fsomabrain-0A66C2?logo=docker)](https://github.com/somatechlat/somabrain/pkgs/container/somabrain)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Make agents *remember, connect, and explain* their work. SomaBrain gives you:
- **Stable, inspectable memory** (HRR-based numerics; exact & Wiener unbinding)
- **Typed links/graphs** between notes, tasks, entities
- **Multi-tenant isolation**
- **FastAPI** HTTP gateway with **OpenAPI docs** and **Prometheus** metrics

> You can see what was saved, how it was found, and why it’s suggested.

---

## 🚀 TL;DR — Run in ~10 seconds (Docker)

**Option A — Pull prebuilt image (if available):**
```bash
docker run --rm -p 8000:8000 ghcr.io/somatechlat/somabrain:latest
```

**Option B — Build locally (works anywhere Docker runs):**
```bash
git clone https://github.com/somatechlat/somabrain.git
cd somabrain
docker build -t somabrain:local .
docker run --rm -p 8000:8000 somabrain:local
```

Now open:
- API docs (Swagger): **http://localhost:8000/docs**
# SomaBrain — Cognitive Memory for Agents

This repository contains SomaBrain: an HRR-based, observable memory and recall system
for agents and automation. This repository's documentation has been pared down to a
concise, authoritative set of pages: the core README, a focused math reference, and
benchmarking docs that show the empirically measured behavior of the numerics.

The primary goals of the cleaned docs set are:
- precise, auditable descriptions of numeric choices (tiny-floor semantics, unitary FFTs, deterministic fallbacks)
- reproducible benchmark instructions and harnesses
- minimal, honest guides for running and validating the system locally

Quick links
- Documentation (local build): `docs/_build/html/index.html` (build with Sphinx)
- Math reference: `docs/source/math.rst`
- Benchmark harness: `benchmarks/bench_numerics.py`
- Core numerics code: `somabrain/numerics.py` and `somabrain/quantum.py`

Local quickstart (dev environment)
1) Create and activate a venv, install test/dev deps (example):
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```
2) Run tests:
```bash
pytest -q
```
3) Build docs (Sphinx):
```bash
python -m sphinx -M html docs/source docs/_build
```

Benchmark example
Use the included harness to compare unbinding/normalization implementations:
```bash
source .venv/bin/activate
python benchmarks/bench_numerics.py \
  --unbind-current somabrain.quantum.unbind_exact \
  --unbind-proposed somabrain.quantum.unbind_exact_unitary \
  --normalize-current somabrain.numerics.normalize_array \
  --normalize-proposed somabrain.numerics.normalize_array \
  --dtype f32 f64 --D 256 1024 4096 --trials 200 --roles unitary nonunitary --postnorm
```

Repository hygiene
- This README and the files under `docs/source/` are intended to be the
  canonical user-facing documentation. Large bench artifacts are stored under
  `benchmarks/` and selectively copied into `docs/benchmarks/` for publication.

License: MIT — see `LICENSE` for details.
