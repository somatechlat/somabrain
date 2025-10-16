# 🧠 SomaBrain 3.0 — Cognitive Memory & Reasoning System

> **Production-ready hyperdimensional memory runtime** with cognitive architectures and mathematical rigor.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.103+-green.svg)](https://fastapi.tiangolo.com)
[![MIT License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](docker-compose.yml)

SomaBrain is a hyperdimensional memory and reasoning runtime that implements Binary Hyperdimensional Computing (BHDC), density-matrix scoring, and multi-tenant cognitive architectures. This repository contains the production implementation of SomaBrain 3.0 with FastAPI, observability, and strict-mode validation.

---

## 🚀 Quick Start — Up and Running in 60 Seconds

### Option 1: Docker Compose (Recommended)
```bash
git clone https://github.com/somatechlat/somabrain.git
cd somabrain
docker compose up -d
```

**✅ Ready!** Access your cognitive system:
- **API Documentation**: http://localhost:9696/docs (Interactive OpenAPI interface)
- **Health Monitoring**: http://localhost:9696/health (System status)
- **Metrics Dashboard**: http://localhost:9696/metrics (Prometheus metrics)

### Option 2: Local Development
```bash
git clone https://github.com/somatechlat/somabrain.git
cd somabrain
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]

# Configure for local development
export SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://localhost:9595
export SOMABRAIN_DISABLE_AUTH=1

# Start the cognitive runtime
uvicorn somabrain.app:app --host 127.0.0.1 --port 9696
```

---

## 💡 Try SomaBrain in 3 Simple Steps

```python
import requests

# 1. Store a memory
requests.post("http://localhost:9696/remember", json={
    "coord": None,
    "payload": {
        "content": "Paris is the capital of France",
        "task": "geography-knowledge",
        "phase": "general"
    }
})

# 2. Intelligent recall with cognitive scoring
response = requests.post("http://localhost:9696/recall", json={
    "query": "capital of France",
    "top_k": 5
})

# 3. Get cognitive insights
print(response.json())  # Rich memory retrieval with salience scoring
```

---

## 🏗️ Architecture Overview

```mermaid
graph TD
    subgraph Client Edge
        Agents[Agents / Tooling]
    end

    Agents -->|HTTPS| API

    subgraph Runtime
        API[SomaBrain FastAPI]
        WM[Working Memory (MultiTenantWM)]
        LTM[MemoryClient + HTTP memory service]
        Scorer[UnifiedScorer + DensityMatrix]
        Quantum[QuantumLayer (BHDC HRR)]
        Control[Neuromodulators & Policy Gates]
    end

    API -->|Recall / Remember| WM
    API -->|Recall / Remember| LTM
    API -->|Scoring| Scorer
    API -->|HRR Encode| Quantum
    API -->|Safety Gates| Control

    subgraph Auxiliary Services
        SMF[SomaFractalMemory Gateway]
        GRPC[gRPC MemoryService]
    end

    LTM -->|Vector IO| SMF
    API -->|Optional Transport| GRPC
```

### 🧩 Core Components:
- **🌐 FastAPI Application** (`somabrain.app`): Production REST API with recall, remember, planning, and health endpoints
- **🧠 Multi-Tenant Working Memory** (`somabrain/mt_wm.py`): Isolated memory spaces with Redis backing and LRU eviction
- **⚛️ BHDC Quantum Layer** (`somabrain/quantum.py`): Binary hyperdimensional computing with permutation binding
- **📊 Unified Scorer** (`somabrain/scoring.py`): Combines cosine similarity, frequency-domain analysis, and recency weighting
- **🔗 Memory Client** (`somabrain/memory_client.py`): HTTP-first connector with strict-mode auditing
- **📈 Observability Stack**: Prometheus metrics, structured logging, and comprehensive health checks

### 🎯 Key Features:
- **Cognitive Architecture**: Working memory + long-term memory with salience detection
- **Mathematical Rigor**: BHDC operations, density matrix scoring, runtime invariant validation
- **Production Ready**: Multi-tenancy, rate limiting, authentication, monitoring
- **Developer Friendly**: OpenAPI docs, Docker Compose, comprehensive testing

See `docs/architecture/somabrain-3.0.md` for detailed technical documentation.

---

## 📋 API Reference — What You Can Do

| Method | Endpoint | Purpose | Example Use Case |
|--------|----------|---------|------------------|
| `POST` | `/remember` | Store memories with cognitive encoding | Save facts, experiences, learned patterns |
| `POST` | `/recall` | Intelligent memory retrieval | Query with context-aware similarity |
| `POST` | `/act` | Execute actions with memory context | Task execution with cognitive state |
| `POST` | `/plan/suggest` | Basic planning and reasoning | Simple multi-step task suggestions |
| `GET` | `/health` | System health and component status | Production monitoring |
| `GET` | `/metrics` | Prometheus observability metrics | Performance and usage analytics |
| `POST` | `/neuromodulators` | Adjust cognitive parameters | Fine-tune system behavior |

### 🧠 Advanced Cognitive Features:
```python
from somabrain.quantum import HRRConfig, QuantumLayer
from somabrain.scoring import UnifiedScorer

# Initialize cognitive components  
config = HRRConfig(dim=2048, seed=42, sparsity=0.1)
quantum_layer = QuantumLayer(config)

# Encode information with roles
memory_vector = quantum_layer.encode_text("Machine learning requires data")
role_vector = quantum_layer.make_unitary_role("knowledge::ai")
bound_memory = quantum_layer.bind_unitary(memory_vector, role_vector)

# Cognitive similarity scoring
scorer = UnifiedScorer(w_cosine=0.6, w_fd=0.3, w_recency=0.1)
query_vector = quantum_layer.encode_text("AI training data")
similarity = scorer.score(query_vector, bound_memory, recency_steps=5)
```

---

## ⚙️ Configuration & Environment

### 🔧 Essential Settings:
```bash
# Core API Configuration
SOMABRAIN_HOST=127.0.0.1
SOMABRAIN_PORT=9696
SOMABRAIN_WORKERS=1

# Memory Integration
SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://localhost:9595
SOMABRAIN_MEMORY_HTTP_TOKEN=dev-token

# Infrastructure Dependencies
SOMABRAIN_REDIS_URL=redis://localhost:6379/0
SOMABRAIN_KAFKA_URL=kafka://localhost:9092
SOMABRAIN_POSTGRES_DSN=postgresql://soma:soma_pass@localhost:5432/somabrain

# Production Controls
SOMABRAIN_STRICT_REAL=1          # Enable mathematical validation
SOMABRAIN_FORCE_FULL_STACK=1     # Require all services  
SOMABRAIN_REQUIRE_MEMORY=1       # Require memory backend
SOMABRAIN_DISABLE_AUTH=1         # Dev mode (disable for production)
```

### 🐳 Docker Infrastructure:
The `docker-compose.yml` provides a complete stack:
- **Redis**: Working memory cache and session storage
- **Kafka**: Event streaming for audit and monitoring  
- **Postgres**: System state and configuration storage
- **Prometheus**: Metrics collection and monitoring
- **OPA**: Policy engine for governance (optional)

---

## 🧪 Development & Testing

### Quality Assurance:
```bash
# Code quality and type checking
ruff check .                    # Linting
mypy somabrain                 # Type validation

# Test suite  
pytest                         # Unit and integration tests
python run_learning_test.py    # Cognitive functionality validation

# Performance benchmarking
python benchmarks/run_benchmarks.py
```

### 🔄 Development Workflow:
```bash
# Quick development setup
scripts/dev_up.sh              # Start full stack
scripts/export_openapi.py      # Generate API docs
```

---

## 🔬 Mathematical Foundations & Validation

| Invariant | Description | Enforcement |
| --- | --- | --- |
| Density matrix trace | `abs(trace(ρ) - 1) < 1e-4` | `somabrain/memory/density.py` renormalizes after each update. |
| PSD stability | Negative eigenvalues are clipped so ρ stays PSD | `DensityMatrix.project_psd()` trims the spectrum. |
| Scorer bounds | Component weights stay within configured bounds | `somabrain/scoring.py` clamps weights and exports metrics. |
| Strict-mode audit | Stub usage raises `RuntimeError` | `_audit_stub_usage` inside `somabrain/memory_client.py`. |
| Governance | Rate limits, OPA policy, neuromodulator feedback | Middleware stack inside `somabrain.app` and controls modules. |

All mathematical invariants are monitored through `/metrics` with Prometheus integration.

---

## ✨ Cognitive Features & Capabilities

### 🧠 **Memory Systems**:
- **Multi-Tenant Working Memory**: Isolated, real-time memory spaces per user/agent
- **Long-Term Memory Integration**: HTTP-based persistent storage with audit trails
- **Salience Detection**: Frequency-domain analysis for memory importance ranking
- **Memory Consolidation**: Background processing for memory organization

### ⚡ **Hyperdimensional Computing**:
- **BHDC Encoding**: Hardware-friendly binary hypervector operations (2048-8192 dimensions)
- **Permutation Binding**: Invertible role-based memory binding and retrieval
- **Quantum Layer Operations**: Superposition and cleanup for cognitive operations
- **Deterministic Encoding**: Reproducible vector representations for consistent behavior

### 📊 **Intelligent Scoring**:
- **Unified Similarity**: Combines cosine similarity, frequency-domain projection, and recency
- **Adaptive Weighting**: Configurable component weights with runtime bounds validation
- **Context Awareness**: Memory scoring considers temporal and semantic context
- **Density Matrix Operations**: Second-order recall using ρ matrix mathematics

### 🏗️ **Production Features**:
- **Multi-Tenancy**: Complete isolation between users/agents with quota management
- **Rate Limiting**: Configurable request throttling and abuse protection
- **Audit Pipeline**: Structured event logging with Kafka integration
- **Health Monitoring**: Comprehensive system health checks and diagnostics

---

## 📊 Monitoring & Production Operations

- **HTTP health**: `/health` aggregates readiness across Redis, Postgres, Kafka, policy middleware, and metrics emission; `/healthz` mirrors the same payload.
- **Metrics**: `/metrics` exports Prometheus counters and histograms for recall latency, scorer components, HRR cleanup, and rate limiting.
- **Tracing**: If `observability.provider.init_tracing` is available, startup hooks configure tracing automatically.
- **Logging**: Structured JSON logging can be enabled via `somabrain/logging.yaml`.

### 🎯 **Key Metrics Tracked**:
- **Performance**: Request latency (p50, p95, p99), throughput rates
- **Memory Operations**: Success rates, cache hit ratios, eviction patterns  
- **Cognitive Functions**: BHDC operation timing, scorer component weights
- **System Health**: Component availability, resource utilization, error rates
- **Business Logic**: Tenant quotas, rate limit triggers, audit event volumes

Operational dashboards and alert configurations available in `docs/operations/runbook.md`.

---

## 🛡️ Quality Assurance & Reliability

- **Linting**: `ruff check .`
- **Type checking**: `mypy somabrain`
- **Unit & property tests**: `pytest`

Run the full suite locally before submitting changes:

```bash
ruff check .
mypy somabrain
pytest
```

### 🧪 **Test Coverage**:
- **Unit Tests**: Individual component validation and edge cases
- **Integration Tests**: Multi-component workflows and API contracts  
- **Property Tests**: Mathematical invariants (BHDC binding, density matrix properties)
- **Cognitive Tests**: Memory recall accuracy, scoring consistency, planning logic
- **Performance Tests**: Latency benchmarks, throughput validation, memory efficiency

Continuous Integration enforces all quality gates before deployment.

---

## 📚 Documentation & Resources

- `docs/architecture/somabrain-3.0.md` — runtime topology, recall lifecycle, and invariants.
- `docs/architecture/STRICT_MODE.md` — strict-mode contract, failure modes, and audit rules.
- `docs/architecture/math/bhdc-binding.md` — BHDC binding / cleanup maths.
- `docs/architecture/math/density-matrix.md` — ρ update rule, projections, and metrics.
- `docs/api/rest.md` — REST endpoint table sourced from `somabrain.app`.
- `docs/operations/runbook.md` — deployment, monitoring, and incident procedures.
- `docs/operations/configuration.md` — environment variable reference.
- `docs/releases/changelog.md` — release log tied to commits and test evidence.

📖 **Complete documentation is maintained in this repository** — report issues or contribute improvements via GitHub.

---

## 🚀 Real-World Applications

### 🤖 **AI Agent Enhancement**:
- **Persistent Memory**: Maintain context across conversations and sessions
- **Intelligent Recall**: Context-aware information retrieval with salience ranking  
- **Multi-Agent Systems**: Isolated memory spaces for different AI personalities
- **Learning Integration**: Adaptive behavior based on interaction history

### 🏢 **Enterprise Integration**:
- **Knowledge Management**: Semantic search and retrieval for corporate information
- **Customer Service**: Context-aware chatbots with memory of previous interactions
- **Research Assistance**: Intelligent document and fact retrieval systems
- **Process Automation**: Memory-augmented workflow and decision systems

---

## 🔧 Advanced Integration Example

```python
from somabrain.quantum import HRRConfig, QuantumLayer
from somabrain.salience import FDSalienceSketch
from somabrain.scoring import UnifiedScorer

cfg = HRRConfig(dim=2048, seed=1337, sparsity=0.08)
quantum = QuantumLayer(cfg)
role = quantum.make_unitary_role("route::origin")
encoded = quantum.bind_unitary(quantum.encode_text("payload"), "route::value")

fd = FDSalienceSketch(dim=cfg.dim, rank=64, decay=0.98)
fd.observe(encoded)

scorer = UnifiedScorer(
    w_cosine=0.6,
    w_fd=0.3,
    w_recency=0.1,
    weight_min=0.0,
    weight_max=1.0,
    recency_tau=32.0,
    fd_backend=fd,
)

query_score = scorer.score(quantum.encode_text("search term"), encoded, recency_steps=5)
print(f"Cognitive similarity: {query_score:.3f}")
```

### 🔗 **Production Integration**:
```bash
# Deploy with Kubernetes
kubectl apply -f k8s/

# Or with Docker Swarm  
docker stack deploy -c docker-compose.yml somabrain

# Monitor with provided dashboards
# - Grafana dashboards in grafana/
# - Prometheus alerts in alerts.yml
# - Health check endpoints for load balancers
```

---

## 🤝 Contributing & Development

- Fork the repository and create a feature branch.
- Keep strict-mode environment variables enabled while developing.
- Run `ruff`, `mypy`, and `pytest` before opening a pull request.
- Update documentation alongside behavioral changes; docs are treated as source code.

### 🎯 **Development Principles**:
- **Mathematical Rigor**: All algorithms are test-backed with invariant validation
- **Production Quality**: Observability, monitoring, and strict-mode enforcement  
- **Cognitive Innovation**: Biologically-inspired architectures with practical implementation
- **Developer Experience**: Clear APIs, comprehensive docs, easy local development

### 📋 **Contribution Workflow**:
1. **Fork** the repository and create a feature branch
2. **Enable strict mode** during development: `export SOMABRAIN_STRICT_REAL=1`
3. **Write tests** and ensure they pass: `pytest`
4. **Quality checks**: `ruff check . && mypy somabrain`
5. **Update docs** for any behavioral changes
6. **Submit** pull request with clear description

---

## 📄 License & Support

**MIT License** — Use SomaBrain freely in commercial and open-source projects.

**Need Help?** 
- 📖 **Documentation**: Complete guides in `docs/` 
- 🐛 **Issues**: Report bugs or request features on GitHub
- 💬 **Discussions**: Technical questions and community support
- 🔧 **Enterprise**: Contact for production deployment assistance

---

**Ready to enhance your AI with cognitive memory?** 

```bash
docker compose up -d
# Visit http://localhost:9696/docs to explore the API
```
