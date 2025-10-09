# SomaBrain V2.0.2 – Live‑Testing & Benchmark Roadmap

This document captures the **canonical sprint plan** for building a full‑stack, live‑testing harness that runs against the real server on port **9696**.  The plan is organized into **parallel sprints** that can be executed simultaneously.

---

## 1️⃣  Overview

| Component | Description |
|-----------|-------------|
| **Config Store** | `tests/configs/brain.yml` – defines three modes (`dev`, `strict`, `full`). |
| **Test Runner** | `scripts/run_live_tests.sh` – starts the server, runs pytest, shuts it down. |
| **Live Client** | `tests/conftest.py` – provides an `httpx.AsyncClient` pointing at `http://localhost:9696`. |
| **Benchmark DB** | JSON snapshots under `benchmarks/` + human‑readable `benchmarks/benchmark_report.md`. |
| **CI Integration** | GitHub Actions workflow `ci-live.yml` (not added here but referenced). |

The architecture is a simple pipeline:

```
Config → Live Server (uvicorn) → Test Suite (pytest + httpx) → Metrics → Benchmark JSON → Markdown Report
```

---

## 2️⃣  Sprint Plan (Parallel Work‑Streams)

| Sprint | Owner | Deliverables |
|-------|-------|--------------|
| **Sprint 0 – Foundations** | Infra / QA | `tests/configs/brain.yml`, `pytest.ini`, `scripts/run_live_tests.sh` (executable). |
| **Sprint 1 – Live‑Test Core** | Test Engineer | `tests/conftest.py` (live client fixture), basic health‑check tests for each mode (`tests/health/`). |
| **Sprint 2 – Recall‑Scoring Validation** | ML Engineer / QA Lead | Fixtures (`fixtures/truth_corpus.jsonl`, `fixtures/noise_corpus.jsonl`), recall tests (`tests/recall/`). |
| **Sprint 3 – Performance & Latency Benchmarks** | Performance Engineer | `benchmarks/run_benchmarks.py`, JSON snapshot generation. |
| **Sprint 4 – CI Integration & Regression Guard** | DevOps | GitHub Actions workflow (`ci-live.yml`), thresholds, artifact upload. |
| **Sprint 5 – Canonical Benchmark Document** | Documentation Owner | `benchmarks/benchmark_report.md` – auto‑generated summary, trend graphs. |

All sprints can start after **Sprint 0** is merged.

---

## 3️⃣  Getting Started (Local)

1. **Create the branch**
   ```bash
   git checkout -b V2.0.2
   ```
2. **Install dependencies** (using `uv` as the repo already uses it)
   ```bash
   uv pip install -e .[dev]
   ```
3. **Run the live‑test helper** for a specific mode (e.g., `dev`):
   ```bash
   BRAIN_MODE=dev scripts/run_live_tests.sh dev
   ```
   This will start `uvicorn somabrain.app:app --port 9696`, execute the pytest suite for that mode, and shut the server down.

---

## 4️⃣  Future Extensions

* Add optional **GPU‑accelerated** embedder tests.
* Expand the **benchmark report** with regression‑alert graphs.
* Hook the benchmark generation into a nightly schedule.

---

*Prepared by the AI‑assisted development team.*