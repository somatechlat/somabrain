# SomaBrain — Project Summary

SomaBrain is the cognitive intelligence layer for agent systems. It sits on top of the SomaFractalMemory layer and provides reasoning, salience‑driven recall, prediction, learning, and planning through modular components. Built for VS Code and FastAPI, it enables agents (like Agent Zero) to think, plan, reflect, and grow.

Design principle: imitate neuroscience and biochemistry where useful and precise — we encode functions (attention, neuromodulation, consolidation) as software components that faithfully imitate their roles, with clear math and observable behavior.

## Overview

- Modular cognition primitives layered over memory: working memory (WM), deterministic tiny embeddings, salience gating, prediction/error handling, and an executive loop.
- Runs as a FastAPI service with Prometheus observability and pluggable backends via Dynaconf/ENV.
- Memory client integrates with SomaFractalMemory HTTP API, with an offline stub fallback.

## Core Features (MVP)

### FastAPI Service
- Endpoints: `/act`, `/recall`, `/remember`, `/reflect`, `/personality`, `/health`, `/metrics`.
- Prometheus middleware for request count and latency; `/metrics` endpoint for scraping.

### Working Memory (WM)
- Lightweight in‑memory buffer with configurable capacity.
- Similarity‑based retrieval using cosine over tiny deterministic embeddings.
- Fast recall path for active context and recent items.

### Tiny Deterministic Embeddings
- 256‑dimensional vectors generated with seeded RNG for reproducibility.
- Used for WM keying, novelty computation, and quick similarity without heavy models.

### Salience & Gating
- Salience = f(novelty, prediction error) with configurable weights.
- Threshold‑based gates control writes to Long‑Term Memory (LTM) and action triggering.

### Prediction & Error (Cerebellum Stub)
- Simple predictor for step outcomes (stub initially, swappable later).
- Bounded prediction error via cosine similarity; feeds salience and learning signals.

### Executive Loop (`/act`)
For each sub‑step (Understand, Execute):
- Recall via WM and memory backend.
- Predict outcome and simulate actual outcome.
- Compute salience; write episodic memory via memory client if gated.
- Admit memory into WM for fast future recall.

### Memory Client with Stub Fallback
- Calls external SomaFractalMemory HTTP API when configured.
- Local stub implements compatible methods when API is unreachable.

### Observability
- Prometheus metrics: HTTP request count/latency; custom counters for WM hits/misses, salience decisions, prediction errors.
- HRR cleanup metrics (optional): `somabrain_hrr_cleanup_used_total`, `somabrain_hrr_cleanup_score`.
- Health endpoint reports readiness/liveness of components and configured backends.

### Configuration
- `config.yaml` + Dynaconf with `SOMABRAIN_` env var overrides.
- Tunables: WM size, salience weights/thresholds, memory backend, prediction provider, timeouts.
- HRR cleanup: enable `use_hrr` and `use_hrr_cleanup` to include cleanup signal in `/recall` and metrics.

## Roadmap

### Phase B (Next 2–4 weeks)
- Reflection (`/reflect`): episodic clustering + semantic summarization; reconsolidate rewritten memories.
- Graph Reasoning: connect via memory layer’s graph store; support k‑hop queries and Hebbian edge updates.
- Personality Module: store/evolve preferences, expertise, and history as semantic memory; influence planning.

### Phase C (Mid‑Term)
- LLM Integration: replace stub predictor with Ollama/OpenAI/VLLM; generate outcomes/summaries.
- Agent Zero Integration: expose SomaBrain via MCP tools; enable “think”, “reflect”, “personality”.
- Dockerization: Dockerfile + docker‑compose (SomaBrain + Memory backend) for easy launch.

### Phase D (Advanced / Cog‑Sci Inspired)
- Attention / Thalamus Layer: route sensory inputs and action gating with modulation.
- Reinforcement Signals: reward‑based gating using NE/DA‑inspired parameters.
- Meta‑learning: adaptive thresholds based on performance trends.
- Predictive Memory & Error Learning: generate semantic corrections on mismatch.

## Why It Matters

- Elevates agent frameworks from reactive scripts to cognitive systems that remember, predict, learn, and adapt.
- Modular design enables independent upgrades of components as capabilities mature.
- Lightweight MVP now, with a pathway to world‑class cognition informed by neuroscience and LLMs.

## Implementation Notes (MVP Sketch)

- WM: ring buffer + index keyed by 256‑D vectors; cosine similarity retrieval.
- Embeddings: `numpy.RandomState(seed)` to generate stable vectors per token/chunk; cache in‑process.
- Salience: `salience = w_novelty * (1 - cos(context, item)) + w_error * error`.
- Prediction: simple text/state similarity; later swap with provider interface (Ollama/OpenAI).
- Memory client: HTTP client to SomaFractalMemory API with timeouts; retry/backoff; JSONL audit hooks.
- Config: Dynaconf layers (file, env) with `SOMABRAIN_` prefix; minimal defaults for standalone use.

## Next Steps

- Implement FastAPI routes with WM and salience gating.
- Add memory client (HTTP + stub) and integrate into `/act` loop.
- Wire Prometheus middleware and custom metrics.
- Add smoke tests: `/act` happy path and WM recall correctness.
