<div align="center">

# 🧠 SomaBrain

### *Hyperdimensional Cognitive Memory System for Autonomous AI Agents*

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Django 5.0+](https://img.shields.io/badge/Django-5.0+-092E20?style=for-the-badge&logo=django&logoColor=white)](https://djangoproject.com)
[![Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue?style=for-the-badge)](LICENSE)
[![Build](https://img.shields.io/badge/Build-Passing-brightgreen?style=for-the-badge)]()

<br/>

**Persistent memory for AI agents that need to remember**

[Website](https://www.somatech.dev) · [Features](#-features) · [Architecture](#-architecture) · [Quick Start](#-quick-start) · [API](#-api-reference) · [Documentation](#-documentation)

</div>

---

## 🌌 The Governed Trace Algorithm

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

## ✨ Features

<table>
<tr>
<td width="50%">

### 🔮 Hyperdimensional Computing

- **8,192-dimensional HRR vectors** for holographic encoding
- **Sparse Distributed Representations** with 2% density
- **HRR/BHDC hypervector superposition** for parallel memory access (the `QuantumLayer` name is historical — this is hyperdimensional computing, not physics quantum)
- **O(N) similarity search** on a fixed-dimension hypervector (constant in the number of stored traces)

</td>
<td width="50%">

### 🧬 Biologically-Inspired

- **Working Memory** with salience-based gating
- **Hippocampal consolidation** during sleep cycles
- **Neuromodulator simulation** (dopamine, serotonin)
- **Amygdala** for emotional valence tagging

</td>
</tr>
<tr>
<td>

### 📊 Adaptive Learning

- **Online plasticity** with automatic gain control
- **Catastrophic forgetting resistance**
- **Drift detection** and model recalibration
- **Reward-modulated learning**

</td>
<td>

### 🔐 Enterprise-Ready

- **Multi-tenant** cryptographic isolation
- **Audit logging** (GDPR, HIPAA compliant)
- **Rate limiting** and quota management
- **OPA policy enforcement**

</td>
</tr>
</table>

---

## 🏛️ Architecture

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
│    │   📊 12M memories  │  🔍 Vector Index  │  📈 Consolidation Queue    │     │
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

## 🚀 Quick Start

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

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure settings (non-secret only)
cp .env.example .env
# .env holds topology/settings placeholders ONLY. Secrets never go in .env
# (Covenant Art 26): "Production secrets shall reside exclusively in secure
# vault systems. Storage in code, configuration files, or environment
# variables is prohibited." Secrets come from Vault at runtime.
# Settings are administered via Django + BrainSetting (agent DB).

# Initialize database
python manage.py migrate

# Start the cognitive engine
python manage.py runserver 9696
```

### 🐳 Docker Deployment

```bash
docker-compose up -d
```

```yaml
# docker-compose.yml
services:
  somabrain:
    image: somatechlat/somabrain:latest
    ports:
      - "9696:9696"
    environment:
      # Secrets are NOT environment variables. The DSN embeds the password, so
      # it is read from Vault at runtime and never set here:
      #   secret/agent/credentials/postgres_password
      # Topology only:
      - SOMABRAIN_REDIS_URL=redis://redis:6379/0
      - SOMABRAIN_MILVUS_HOST=milvus
    # VAULT_ADDR + VAULT_TOKEN are injected by the deployer, never committed.
```

---

## 📡 API Reference

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

## 🧪 Core Modules

| Module | Description | Key Functions |
|--------|-------------|---------------|
| `wm.py` | Working memory with salience gating | `add()`, `evict()`, `recall()` |
| `hippocampus.py` | Long-term consolidation | `store()`, `retrieve()`, `consolidate()` |
| `amygdala.py` | Emotional valence tagging | `tag_valence()`, `modulate()` |
| `prefrontal.py` | Executive planning & control | `plan()`, `inhibit()`, `switch()` |
| `neuromodulators.py` | Dopamine, serotonin, norepinephrine | `update()`, `get_levels()` |
| `context_hrr.py` | Holographic Reduced Representations | `encode()`, `bind()`, `unbind()` |
| `sdr.py` | Sparse Distributed Representations | `encode()`, `overlap()` |
| `quantum.py` | HRR/BHDC hypervector layer (`QuantumLayer`) — bind/unbind/cleanup, **not** physics quantum | `superpose()`, `bind()`, `unbind()`, `cleanup()` |
| `consolidation.py` | NREM/REM sleep consolidation | `nrem_cycle()`, `rem_cycle()` |
| `salience.py` | Importance scoring | `compute()`, `threshold()` |

---

## ⚙️ Configuration

SomaBrain exposes a large set of environment-driven settings. Key examples:

| Setting | Default | Description |
|---------|---------|-------------|
| `SOMABRAIN_WM_SIZE` | 64 | Working memory capacity |
| `SOMABRAIN_HRR_DIM` | 8192 | Hypervector dimensions |
| `SOMABRAIN_SDR_BITS` | 2048 | SDR active bits |
| `SOMABRAIN_EMBED_DIM` | 768 | Embedding dimensions (seam contract with SFM/agent) |
| `SOMABRAIN_ENABLE_SLEEP` | true | Enable consolidation cycles |
| `SOMABRAIN_NEURO_DOPAMINE_BASE` | 0.4 | Base dopamine level |
| `SOMABRAIN_RATE_RPS` | 1000 | Rate limit (req/sec) |

📖 **Current reference set:** [`docs/README.md`](docs/README.md)

---

## 📚 Documentation

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
| [SOMA-BR-PROD-001](docs/iso/SOMA-BR-PROD-001.md) | ISO/IEC 25010 | Production Readiness — Scorecard, standalone vs AAAS readiness, K8s deployment, Helm charts |

---

## 🔬 Research Foundations

SomaBrain synthesizes cutting-edge research from cognitive science and AI:

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

## 🛡️ Security & Compliance

| Feature | Description |
|---------|-------------|
| 🔐 **JWT Authentication** | Configurable with Keycloak, Auth0, or custom |
| 🛡️ **OPA Policy Engine** | Fine-grained authorization |
| 🔒 **Vault Integration** | Secrets management |
| 📋 **Audit Logging** | Complete operation history |
| 🔏 **Provenance Tracking** | Cryptographic memory chain |
| 🚫 **PII Masking** | Automatic in logs |

**Compliance:** GDPR, HIPAA, SOC2-ready

---

## 🤝 SomaStack Ecosystem

| Project | Description | Link |
|---------|-------------|------|
| 🤖 **SomaAgent01** | Agent orchestration gateway | [GitHub](https://github.com/somatechlat/somaAgent01) |
| 💾 **SomaFractalMemory** | Distributed long-term storage | [GitHub](https://github.com/somatechlat/somafractalmemory) |
| 🌐 **SomaStack AAAS** | Admin dashboard UI | [Docs](webui/somastack-aaas) |

---

## 📊 Performance Benchmarks

| Operation | Latency (p95) | Throughput |
|-----------|:-------------:|:----------:|
| Memory Store | 8ms | 12,000/sec |
| Vector Recall | 15ms | 5,000/sec |
| WM Update | 2ms | 50,000/sec |
| Consolidation Cycle | 30s | 10,000 memories |

*Benchmarked on 32-core, 128GB RAM, with Milvus on NVMe*

---

<div align="center">

## 📜 License

Licensed under the [Apache License, Version 2.0](LICENSE)

---

<br/>

**Built with 🧠 by the SomaTech team**

*"Teaching machines to remember, so they can truly understand."*

<br/>

[![Star](https://img.shields.io/github/stars/somatechlat/somabrain?style=social)](https://github.com/somatechlat/somabrain)

</div>
