<div align="center">

# 🧠 SomaBrain

### Hyperdimensional memory runtime for agents

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Django 5.1+](https://img.shields.io/badge/Django-5.1+-092E20?style=for-the-badge&logo=django&logoColor=white)](https://djangoproject.com)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue?style=for-the-badge)](LICENSE)

**Persistent memory for agents**

[Features](#features) · [Architecture](#architecture) · [Quick Start](#quick-start) · [API](#api-reference) · [Documentation](#documentation)

</div>

---

## The Governed Trace Algorithm

At the heart of SomaBrain lies a mathematically elegant memory update mechanism inspired by neuroscience:

<div align="center">

```math
\LARGE \mathbf{m}_t = (1 - \eta)\mathbf{m}_{t-1} + \eta\mathbf{b}_t
```

</div>

| Symbol | Name | Description |
|:------:|------|-------------|
| $\mathbf{m}_t$ | **Memory State** | Current high-dimensional superposition vector |
| $\mathbf{b}_t$ | **Input Vector** | New sparse, orthogonal memory trace |
| $\eta$ | **Plasticity Gain** | Controls update strength (learning rate) |
| $(1-\eta)$ | **Decay Factor** | Exponential forgetting mechanism |

**Key Properties:**

```math
\mathbb{E}[\mathbf{x} \cdot \mathbf{y}] \approx 0 \quad \text{(approximate orthogonality in } \mathbb{R}^N, N \gg 1\text{)}
```

This enables high-capacity associative memory with constant-time $O(1)$ retrieval.

📖 **[Read the current mathematical notes →](docs/SomabrainGMD.md)**

---

## Features

| Area | Implemented behavior |
|------|----------------------|
| Hyperdimensional computing | HRR/BHDC hypervector encode/bind/unbind/cleanup (`QuantumLayer` name is historical — this is hyperdimensional computing, not physics). Dimension `BHDC_D = 8192` (`somabrain/math/contracts.py`). Sparse Distributed Representations in `somabrain/admin/core/sdr.py`. |
| Memory | Working memory with salience-based promotion (`somabrain/memory/wm/`, `somabrain/memory/promotion.py`), long-term store via SomaFractalMemory HTTP, consolidation (`somabrain/memory/consolidation.py`) |
| Learning | Online weight adaptation (`somabrain/learning/adaptation/`) driven by recall hit/miss, store, promote, forget, and `/context/feedback`. HRR is additive on the embed path (`SOMABRAIN_USE_HRR` default true; optional disable). |
| Runtime core | Rust crate `somabrain_rs` is the sole adaptation-math authority (DEBT-008 closed) and also hosts BHDC, Wiener, and neuromod. Missing Rust on the adaptation path refuses (`RuntimeError`) — no Python gain-law twin (`rust_core/`, `cargo test` 17/17 as of 2026-10-09). |
| Multi-tenancy | Tenant-bound requests and BrainSetting administration (`somabrain/tenant.py`, `somabrain/api/endpoints/brain_settings.py`) |
| Policy / auth | OPA client, JWT/API-token auth, audit logging (`somabrain/opa/`, `somabrain/core/security/`) |

**Not claimed:** regulatory certification (see Compliance below). Measured latency/throughput figures are not published in this README; see SLO targets in `docs/iso/SOMA-BR-VV-001.md` and `tests/proofs/category_g/test_latency_slo.py`.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              SOMABRAIN COGNITIVE CORE                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│    ┌────────────────┐     ┌────────────────┐     ┌────────────────┐             │
│    │   PREFRONTAL   │────▶│   THALAMUS     │────▶│   AMYGDALA     │             │
│    │   (Planning)   │     │   (Gating)     │     │   (Valence)    │             │
│    └───────┬────────┘     └───────┬────────┘     └───────┬────────┘             │
│            │                      │                      │                       │
│            └──────────────────────┼──────────────────────┘                       │
│                                   ▼                                              │
│    ┌──────────────────────────────────────────────────────────────────────┐     │
│    │                        WORKING MEMORY                                 │     │
│    │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │     │
│    │   │ Slot 1  │  │ Slot 2  │  │ Slot 3  │  │   ...   │  │ Slot N  │   │     │
│    │   │ s=0.92  │  │ s=0.85  │  │ s=0.71  │  │         │  │ s=0.43  │   │     │
│    │   └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘   │     │
│    └──────────────────────────────┬───────────────────────────────────────┘     │
│                                   │                                              │
│                                   ▼                                              │
│    ┌──────────────────────────────────────────────────────────────────────┐     │
│    │                     HRR / SDR ENGINE                                  │     │
│    │                                                                       │     │
│    │   encode(x) → ℝ^8192    bind(a,b) → a ⊛ b    unbind(c,a) → b        │     │
│    │                                                                       │     │
│    └──────────────────────────────┬───────────────────────────────────────┘     │
│                                   │                                              │
│                                   ▼                                              │
│    ┌──────────────────────────────────────────────────────────────────────┐     │
│    │                      HIPPOCAMPUS                                      │     │
│    │                   (Long-term Storage)                                 │     │
│    │                                                                       │     │
│    │   Vector index │ Consolidation queue │ (target ≥12M/tenant, not measured) │     │
│    │                                                                       │     │
│    └──────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
│    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│    │  DOPAMINE    │   │  SEROTONIN   │   │ NOREPINEPH.  │   │ ACETYLCHOL.  │   │
│    │    0.48      │   │    0.52      │   │    0.12      │   │    0.31      │   │
│    └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘   │
│                          NEUROMODULATOR PANEL                                    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
          ┌───────────────────────────┴───────────────────────────┐
          │                                                       │
    ┌─────▼─────┐              ┌─────▼─────┐              ┌───────▼───────┐
    │ PostgreSQL │              │   Milvus  │              │     Redis     │
    │   State    │              │  Vectors  │              │    Cache      │
    │    & ORM   │              │  (HNSW)   │              │   Sessions    │
    └───────────┘              └───────────┘              └───────────────┘
```

---

## Quick Start

### Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.11+ | Runtime |
| PostgreSQL | 15+ | State storage |
| Redis | 7+ | Caching & sessions |
| Milvus | 2.3+ | Vector similarity |

### Installation

```bash
# Clone the repository
git clone https://github.com/somatechlat/somabrain.git
cd somabrain

# Create virtual environment (Python 3.12 required)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install the package and dependencies (pyproject.toml is the source of truth)
pip install -e .
# Development tools (pytest, ruff, black, pyright):
pip install -r requirements-dev.txt

# Settings law (binding):
#   Settings = Django settings modules (somabrain/settings/) + BrainSetting DB
#              overlay (somabrain/brain_settings/models.py). Administerable.
#   Secrets  = Vault ONLY (Covenant Art 26): "Production secrets shall reside
#              exclusively in secure vault systems. Storage in code,
#              configuration files, or environment variables is prohibited."
#   Environment variables are NOT a settings or secrets channel.
#   .env.example exists only as a non-secret local bootstrap sketch.

# Initialize database
python manage.py migrate

# Start the API (default port for local Django is 9696; Docker Compose uses 30101)
python manage.py runserver 9696
```

### Docker Deployment

The canonical standalone stack is `infra/standalone/docker-compose.yml` (ports 30100–30108). Topology (Redis, Milvus, Kafka, OPA URLs) is administered via **BrainSetting / Django settings**, not by copying environment files. Secrets (DSN, tokens) are injected from **Vault** at runtime.

```bash
# See infra/standalone/DEPLOYMENT_GUIDE.md for the full stack, Vault unseal, and healthchecks.
cd infra/standalone
docker compose up -d
```

Do not put secrets in compose `environment:` blocks. Vault address/token for the deployer are supplied out-of-band and never committed.

---

## API Reference

### Remember (write)

The real write route is `POST /api/memory/remember` (alias `POST /memory/remember`).
Batch writes use `POST /api/memory/remember/batch`.

```bash
curl -X POST http://localhost:30101/memory/remember \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "text": "The mitochondria is the powerhouse of the cell",
    "tenant_id": "demo",
    "kind": "semantic",
    "salience": 0.9,
    "source": "textbook"
  }'
```

### Recall

The real recall route is `POST /api/memory/recall` (alias `POST /memory/recall`).
There is no `retrievers` field. Hits come from working memory (WM) and
long-term memory (LTM), selected by `layer` (`wm`, `ltm`, or `both`).

```bash
curl -X POST http://localhost:30101/memory/recall \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "query": "What produces energy in cells?",
    "tenant_id": "demo",
    "top_k": 5,
    "layer": "both",
    "min_score": 0.1,
    "max_age_seconds": 86400
  }'
```

```json
{
  "tenant": "demo",
  "namespace": "somabrain:demo",
  "results": [
    {
      "text": "The mitochondria is the powerhouse of the cell",
      "coord": "0.1,0.2,0.3",
      "score": 0.94,
      "store": "somafractalmemory",
      "created_at": "2026-01-03T10:30:00Z"
    }
  ],
  "wm_hits": 1,
  "ltm_hits": 1
}
```

### Memory metrics

There is no `/api/v1/memory/wm/status`. Working-memory occupancy is on
`GET /api/memory/metrics?tenant=...`.

---

## Core Modules

| Module (package path) | Purpose | Key symbols |
|--------|-------------|---------------|
| `somabrain/memory/wm/` | Working memory with salience gating | `WorkingMemory`, `WMItem` |
| `somabrain/memory/promotion.py` | WM→LTM promotion by salience threshold | `PromotionTracker` |
| `somabrain/admin/cognitive/hippocampus.py` | Long-term consolidation orchestration | `store()`, `retrieve()`, `consolidate()` |
| `somabrain/admin/cognitive/amygdala.py` | Valence tagging | `tag_valence()`, `modulate()` |
| `somabrain/admin/cognitive/prefrontal.py` | Executive planning and control | `plan()`, `inhibit()`, `switch()` |
| `somabrain/runtime/neuromodulators.py` | Neuromodulator levels | `update()`, `get_levels()` |
| `somabrain/admin/core/context_hrr.py` | Holographic Reduced Representations | `encode()`, `bind()`, `unbind()` |
| `somabrain/admin/core/sdr.py` | Sparse Distributed Representations | `encode()`, `overlap()` |
| `somabrain/admin/core/quantum.py` | HRR/BHDC hypervector layer (`QuantumLayer`) — bind/unbind/cleanup, not physics quantum | `superpose()`, `bind()`, `unbind()`, `cleanup()` |
| `somabrain/memory/consolidation.py` | NREM/REM consolidation cycles | `nrem_cycle()`, `rem_cycle()` |
| `somabrain/math/contracts.py` | Shared math constants (`BHDC_D`, gains) | `BHDC_D`, `AdaptGains` |

---

## Configuration

**Settings law (binding):** Settings come from **Django settings modules** (`somabrain/settings/`) and the **`BrainSetting` DB overlay** (`somabrain/brain_settings/models.py`) — both administerable. **Secrets come from Vault only** (Covenant Art 26). Environment variables are **not** a settings or secrets channel. Topology URLs and runtime knobs are resolved by `somabrain/settings/managed.py` (`managed_get`: BrainSetting first, then Django; never `os.environ`).

Representative `BrainSetting` keys (registry defaults in `somabrain/brain_settings/models.py`, 75 keys as of 2026-10-09):

| BrainSetting key | Default | Description |
|---------|---------|-------------|
| `embed_dim` | 768 | Embedding dimension (seam contract with SFM/agent) |
| `hrr_dim` | 8192 | Hypervector dimension (`BHDC_D`) |
| `use_hrr` | true | HRR/QuantumLayer additive embed path (optional disable) |
| `memory_decay_rate` | 0.05 | WM/LTM decay per tick (learnable) |
| `wm_prune_threshold` | 0.15 | WM prune salience threshold (learnable) |
| `ltm_prune_threshold` | 0.05 | LTM prune threshold (learnable) |
| `max_wm_items` | 128 | Working-memory capacity |
| `max_ltm_items_per_tenant` | 100000 | Per-tenant LTM cap |
| `memory_http_endpoint` | (topology) | SomaFractalMemory HTTP base URL |
| `active_brain_mode` | ANALYTIC | Active cognitive preset mode |

Runtime API for system-role UI: `GET/PUT /settings` (`somabrain/api/endpoints/brain_settings.py`) — bounded, tenant-bound writes.

📖 **Reference set:** [`docs/README.md`](docs/README.md) · **Config map (truth):** [`docs/iso/SOMA-BR-CONFIG-API-TEST-001.md`](docs/iso/SOMA-BR-CONFIG-API-TEST-001.md)

---

## Documentation

| Document | Description |
|----------|-------------|
| [Docs Index](docs/README.md) | Current documentation map |
| [Onboarding](docs/ONBOARDING.md) | Project context and orientation |
| [User Guide](docs/USER_GUIDE.md) | Usage guide |
| [Standalone Deployment](infra/standalone/DEPLOYMENT_GUIDE.md) | Current Docker standalone deployment |
| [SOMA Covenant](docs/THE-SOMA-COVENANT.md) | Governance principles |

### ISO Documentation Suite (v2.0.0)

| Document | Standard | Description |
|----------|----------|-------------|
| [SOMA-BR-ARCH-001](docs/iso/SOMA-BR-ARCH-001.md) | ISO/IEC 42010 | Architecture Document — GMD algorithm, deployment modes, architecture views, core algorithms, Rust core, service layer, integrations, multi-tenancy, observability |
| [SOMA-BR-AUDIT-001](docs/iso/SOMA-BR-AUDIT-001.md) | ISO 19011 | Audit Report — Executive scorecard, code quality analysis, strengths, weaknesses, recommendations |
| [SOMA-BR-SEC-001](docs/iso/SOMA-BR-SEC-001.md) | ISO/IEC 27001 | Security Assessment — JWT auth, OPA policies, constitution signing, TLS, Vault, per-tenant isolation |
| [SOMA-BR-RISK-001](docs/iso/SOMA-BR-RISK-001.md) | ISO 31000 | Risk Register — Complexity debt, SFM dependency, Kafka availability, Milvus scaling, calibration drift |
| [SOMA-BR-PROD-001](docs/iso/SOMA-BR-PROD-001.md) | ISO/IEC 25010 | Production Readiness — Scorecard, standalone vs Soma Platform readiness, K8s deployment, Helm charts |

---

## Research Foundations

The design draws on published work in cognitive science and vector-symbolic computation:

<table>
<tr>
<td>

**Holographic Memory**
- Plate, T.A. (2003). *Holographic Reduced Representations*
- Gayler, R.W. (2003). *Vector Symbolic Architectures*

**Sparse Coding**
- Kanerva, P. (1988). *Sparse Distributed Memory*
- Olshausen, B.A. (1996). *Sparse Coding in V1*

</td>
<td>

**Learning Systems**
- McClelland, J.L. (1995). *Complementary Learning Systems*
- O'Reilly, R.C. (2006). *Biologically Plausible Error-driven Learning*

**Predictive Coding**
- Clark, A. (2013). *Predictive Processing*
- Friston, K. (2010). *Free Energy Principle*

</td>
</tr>
</table>

---

## Security and Compliance

| Feature | Implementation |
|---------|----------------|
| Authentication | JWT and API-token auth (`somabrain/core/security/`) |
| Authorization | OPA policy client (`somabrain/opa/`), constitution signing |
| Secrets | HashiCorp Vault only (Covenant Art 26) — never code, files, `.env`, or environment |
| Audit logging | Operation history and provenance tracking |
| Isolation | Per-tenant data separation |

**Compliance status (honest):** SomaBrain provides **control mappings** toward GDPR/HIPAA/SOC2 expectations (see `docs/iso/SOMA-BR-SEC-001.md`). It is **not certified**. No formal audit, BAA, or attestation is claimed by this repository.

---

## SomaStack Ecosystem

| Project | Description | Link |
|---------|-------------|------|
| SomaAgent01 | Agent orchestration gateway | [GitHub](https://github.com/somatechlat/somaAgent01) |
| SomaFractalMemory | Distributed long-term storage | [GitHub](https://github.com/somatechlat/somafractalmemory) |

SomaStack Soma Platform admin UI lives in the sibling `somaAgent01` repository (not in this tree).

---

## Performance

No published measured latency/throughput table is claimed here. The repository defines **SLO targets** and proof tests:

| Operation | SLO target (p95) | Evidence |
|-----------|:-------------:|----------|
| Memory store | ≤ 8ms | `tests/proofs/category_g/test_latency_slo.py` |
| Vector recall | ≤ 15ms | `tests/proofs/category_g/test_latency_slo.py` |
| WM update | ≤ 2ms | `tests/proofs/category_g/test_latency_slo.py` |

These are targets under verification (`docs/iso/SOMA-BR-VV-001.md`), not marketing benchmarks. Hardware-dependent figures are not asserted without a dated measurement report.

---

## License

Licensed under the [Apache License, Version 2.0](LICENSE)

