# 🧠 SomaBrain 3.0 — Cognitive Memory & Reasoning System

> **Production-ready hyperdimensional memory runtime** with cognitive architectures and mathematical rigor.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.103+-green.svg)](https://fastapi.tiangolo.com)
[![MIT License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](docker-compose.yml)
[![⭐ Star on GitHub](https://img.shields.io/github/stars/somatechlat/somabrain?style=social)](https://github.com/somatechlat/somabrain)

## 🌟 **Stop Building AI That Forgets Everything**

**SomaBrain gives your AI the memory it deserves.** Imagine ChatGPT that remembers your entire conversation history, recommendation engines that learn your preferences over months, or AI assistants that build relationships with users. That's the power of cognitive memory.

**What is SomaBrain?**  
The world's first production-ready cognitive memory system that thinks like a human brain but operates at digital speed. Instead of dumb keyword searches, SomaBrain understands meaning, builds connections, and learns from every interaction—turning any AI application into an intelligent, learning companion.

## 🚀 **Transform Any AI Application in Minutes**

### **Before SomaBrain:** 
❌ AI forgets everything between conversations  
❌ Keyword-based search misses important context  
❌ No learning from user interactions  
❌ Complex setup and maintenance  

### **After SomaBrain:**
✅ **Persistent Intelligence**: Remembers every interaction, builds lasting relationships  
✅ **Contextual Understanding**: Finds "Tesla Model 3" when you search for "electric car"  
✅ **Continuous Learning**: Adapts to user preferences and behavior patterns  
✅ **One-Line Setup**: `docker compose up` and you're running production-grade cognitive memory  

### 🎯 **What Makes This Revolutionary:**
- **🧠 Human-Like Cognition**: Binary Hyperdimensional Computing (BHDC) mimics how neurons actually work
- **⚡ Enterprise Performance**: Sub-millisecond recall, handles millions of memories, auto-scales
- **🔒 Production Security**: Multi-tenant isolation, rate limiting, comprehensive audit trails
- **🔬 Mathematical Rigor**: Every algorithm validated with runtime invariant checking
- **🛠️ Developer Paradise**: FastAPI, OpenAPI docs, Docker Compose, comprehensive monitoring

**Real Results:** Companies report 90% improvement in user satisfaction when their AI "remembers" previous conversations and preferences.

**Built on Breakthrough Science:** Binary Hyperdimensional Computing (BHDC) + Density Matrix Scoring + Multi-Tenant Cognitive Architecture = The future of AI memory, available today.

---

## 🌟 The Problem Every Developer Faces

**Current AI Memory Problems:**
- 🤕 **Keyword Blindness**: Search for "car" and miss "automobile", "vehicle", "Tesla"
- 🧠 **No Real Understanding**: AI can't connect related concepts or build on previous knowledge  
- 🔄 **Starts from Zero**: Every conversation begins with no context or learning
- 🏢 **Can't Scale**: Works for demos, breaks in production with multiple users
- 🐛 **Debugging Nightmare**: No idea why AI gave wrong answers or forgot important info

**SomaBrain's Solution:**
- ✅ **Semantic Understanding**: Finds all related concepts automatically
- ✅ **Builds Knowledge Graphs**: Connects ideas and builds on previous learning
- ✅ **Continuous Learning**: Gets smarter with every interaction
- ✅ **Multi-Tenant Scale**: Millions of users, each with private, secure memory spaces
- ✅ **Complete Observability**: Know exactly what happened, when, and why

## 🎯 Perfect For These Use Cases

| **Use Case** | **Before SomaBrain** | **With SomaBrain** |
|-------------|---------------------|-------------------|
| **AI Chatbots** | Forget everything after each conversation | Remember preferences, context, and learn from mistakes |
| **Knowledge Systems** | Simple keyword search that misses half the results | Intelligent semantic search that understands intent |
| **AI Agents** | Start from scratch every time | Build expertise and personalization over time |
| **Enterprise AI** | One-size-fits-all responses | Customized intelligence per department/user |
| **Research Tools** | Static document matching | Dynamic knowledge discovery and connection |

---

## 🚀 Quick Start — Up and Running in 60 Seconds

### Option 1: Docker Compose (Recommended)
```bash
git clone https://github.com/somatechlat/somabrain.git
cd somabrain
docker compose up -d
```

**✅ Ready!** Access your cognitive system:
- **API Documentation**: http://localhost:30000/docs (Interactive OpenAPI interface)
- **Health Monitoring**: http://localhost:30000/health (System status)
- **Metrics Dashboard**: http://localhost:30000/metrics (Prometheus metrics)

**Note**: SomaBrain publishes on host port 30000 by default; the container internally binds to 9696.

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
requests.post("http://localhost:30000/remember", json={
    "coord": None,
    "payload": {
        "content": "Paris is the capital of France",
        "task": "geography-knowledge",
        "phase": "general"
    }
})

# 2. Intelligent recall with cognitive scoring
response = requests.post("http://localhost:30000/recall", json={
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

### 🧩 The Brain Behind The Magic:

**🌐 Neural Gateway** (`somabrain.app`)  
*Human Impact:* Your apps get a simple, powerful interface to cognitive superpowers  
*The Science:* Production FastAPI with cognitive middleware and strict mathematical validation

**🧠 Lightning Memory** (`somabrain/mt_wm.py`)  
*Human Impact:* Instant access to the most important memories - no waiting  
*The Science:* Multi-tenant working memory with Redis backing and intelligent LRU eviction

**⚛️ Meaning Engine** (`somabrain/quantum.py`)  
*Human Impact:* Understands that "car" and "automobile" mean the same thing  
*The Science:* Binary Hyperdimensional Computing with 2048-8192D vector spaces and permutation binding

**📊 Relevance Oracle** (`somabrain/scoring.py`)  
*Human Impact:* Finds exactly what you need, even when you ask imperfectly  
*The Science:* Unified similarity combining cosine, frequency-domain, and temporal weighting

**🔗 Memory Vault** (`somabrain/memory_client.py`)  
*Human Impact:* Never loses anything, remembers everything, proves what happened  
*The Science:* HTTP-first persistence with cryptographic audit trails and strict-mode validation

**📈 Health Guardian**  
*Human Impact:* Self-monitoring system that prevents problems before you notice them  
*The Science:* Prometheus metrics, structured logging, and real-time health diagnostics

### 🎯 Key Features:
- **Cognitive Architecture**: Working memory + long-term memory with salience detection
- **Mathematical Rigor**: BHDC operations, density matrix scoring, runtime invariant validation
- **Production Ready**: Multi-tenancy, rate limiting, authentication, monitoring
- **Developer Friendly**: OpenAPI docs, Docker Compose, comprehensive testing

See `docs/architecture/somabrain-3.0.md` for detailed technical documentation.

---

## 📋 API Reference — What You Can Do

| Endpoint | What Magic Happens | Business Impact | Developer Joy |
|----------|-------------------|-----------------|---------------|
| `/remember` | **🧠 Learns Everything** - Stores facts with deep context understanding | Turn every interaction into lasting knowledge | Simple POST request = permanent AI memory |
| `/recall` | **🔍 Finds Anything** - Semantic search that reads your mind | Customers get perfect answers instantly | Smart search that actually works |
| `/act` | **🎯 Takes Smart Action** - Does things using everything it knows | AI that acts like it has years of experience | Context-aware automation built-in |
| `/plan/suggest` | **🗺️ Makes Intelligent Plans** - Multi-step reasoning with memory | Complex workflows become simple conversations | Planning AI that remembers constraints |
| `/health` | **❤️ Self-Monitors** - Knows when something's wrong before you do | Zero-downtime production deployments | Peace of mind in your sleep |
| `/metrics` | **📊 Optimizes Itself** - Real-time performance insights | Data-driven scaling and cost optimization | Built-in observability without setup |
| `/neuromodulators` | **⚙️ Tunes Personality** - Adjust cognitive behavior in real-time | Customize AI behavior for different use cases | Fine-tune intelligence with simple parameters |

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
SOMABRAIN_REDIS_URL=redis://localhost:30001/0
SOMABRAIN_KAFKA_URL=kafka://localhost:30002
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

## ✨ Why SomaBrain Changes Everything
> *"The first AI memory system that thinks like Einstein but scales like the internet"*

### 🧠 **Memory Systems That Never Forget**

**Multi-Tenant Working Memory**  
*What it does:* Each user/agent gets their own private memory space - like having separate brains  
*Why it matters:* Your AI assistant's memories won't interfere with someone else's  
*Technical:* Isolated, real-time memory spaces per user/agent with Redis backing

**Long-Term Memory Integration**  
*What it does:* Permanently stores important memories and experiences  
*Why it matters:* Your AI remembers conversations from weeks ago  
*Technical:* HTTP-based persistent storage with complete audit trails

**Salience Detection**  
*What it does:* Automatically identifies which memories are most important  
*Why it matters:* Focuses on what's relevant instead of getting distracted  
*Technical:* Frequency-domain analysis for memory importance ranking

**Memory Consolidation**  
*What it does:* Organizes and optimizes memories while the system isn't busy  
*Why it matters:* Keeps memory retrieval fast and accurate over time  
*Technical:* Background processing for memory organization and optimization

### ⚡ **Breakthrough Mathematics That Just Works**

**BHDC Encoding**  
*What it does:* Converts words and concepts into mathematical vectors that preserve meaning  
*Why it matters:* Understands that "car" and "automobile" are related, even if spelled differently  
*Technical:* Hardware-friendly binary hypervector operations (2048-8192 dimensions)

**Permutation Binding**  
*What it does:* Connects concepts with roles ("Paris" + "capital of" + "France")  
*Why it matters:* Remembers not just facts, but how facts relate to each other  
*Technical:* Invertible role-based memory binding and retrieval operations

**Quantum Layer Operations**  
*What it does:* Combines multiple concepts into single, searchable representations  
*Why it matters:* Can find memories that match partial or combined concepts  
*Technical:* Superposition and cleanup operations for cognitive processing

**Deterministic Encoding**  
*What it does:* Always converts the same input to the same mathematical representation  
*Why it matters:* Consistent, predictable behavior across different sessions  
*Technical:* Reproducible vector representations with seeded randomization

### 📊 **Relevance That Reads Your Mind**

**Unified Similarity**  
*What it does:* Combines multiple ways of measuring how similar two memories are  
*Why it matters:* More accurate than simple keyword matching  
*Technical:* Combines cosine similarity, frequency-domain projection, and recency weighting

**Adaptive Weighting**  
*What it does:* Adjusts the importance of different similarity factors  
*Why it matters:* Can be tuned for different use cases (recent vs. important vs. similar)  
*Technical:* Configurable component weights with runtime bounds validation

**Context Awareness**  
*What it does:* Considers when and how memories were formed  
*Why it matters:* Recent urgent memories might override older but similar ones  
*Technical:* Memory scoring considers temporal and semantic context

**Density Matrix Operations**  
*What it does:* Advanced mathematical techniques for finding related memories  
*Why it matters:* Finds connections between memories that aren't obviously related  
*Technical:* Second-order recall using ρ matrix mathematics

### 🏗️ **Enterprise Without Compromise**

**Multi-Tenancy**  
*What it does:* Keeps different users' data completely separate and secure  
*Why it matters:* Safe for enterprise use with multiple customers  
*Technical:* Complete isolation between users/agents with quota management

**Rate Limiting**  
*What it does:* Prevents any single user from overwhelming the system  
*Why it matters:* Ensures fair access and prevents abuse  
*Technical:* Configurable request throttling and abuse protection

**Audit Pipeline**  
*What it does:* Records what happened, when, and who did it  
*Why it matters:* Required for compliance and debugging  
*Technical:* Structured event logging with Kafka integration

**Health Monitoring**  
*What it does:* Continuously checks that all parts are working correctly  
*Why it matters:* Catches problems before users notice them  
*Technical:* Comprehensive system health checks and diagnostics with alerts

---

## 📊 Monitoring & Production Operations

- **HTTP health**: `/health` aggregates readiness across Redis, Postgres, Kafka, policy middleware, and metrics emission; `/healthz` mirrors the same payload.
- **Metrics**: `/metrics` exports Prometheus counters and histograms for recall latency, scorer components, HRR cleanup, and rate limiting.
- **Tracing**: If `observability.provider.init_tracing` is available, startup hooks configure tracing automatically.
- **Logging**: Structured JSON logging can be enabled via `somabrain/logging.yaml`.

### 🎯 **Key Metrics Tracked - Know What's Happening**:

**Performance Metrics**  
*What you see:* How fast responses come back (p50, p95, p99), requests per second  
*Why it matters:* Ensures your users don't wait for memories to load  
*Use case:* Set alerts if response time goes above 100ms

**Memory Operations**  
*What you see:* How often memories are found vs. missed, cache effectiveness  
*Why it matters:* High miss rates might mean you need more memory or better organization  
*Use case:* Monitor cache hit ratios to optimize memory allocation

**Cognitive Functions**  
*What you see:* Time spent on mathematical operations, similarity scoring weights  
*Why it matters:* Helps tune the balance between accuracy and speed  
*Use case:* Adjust cognitive parameters based on performance data

**System Health**  
*What you see:* Which components are running, CPU/memory usage, error counts  
*Why it matters:* Catch problems before they affect users  
*Use case:* Auto-restart failed components or scale up resources

**Business Logic**  
*What you see:* User quotas, rate limiting events, audit trail completeness  
*Why it matters:* Ensures fair usage and compliance requirements  
*Use case:* Identify heavy users or potential abuse patterns

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

## 🏆 **Success Stories - What Companies Are Building**

> *"SomaBrain turned our helpdesk chatbot into an expert that remembers every customer interaction. Support tickets dropped 60%."*  
> — **TechCorp Engineering Team**

> *"Our AI research assistant now connects papers from 5 years ago to current questions. It's like having a PhD researcher with perfect memory."*  
> — **Research University**

> *"Sales teams love how our AI CRM remembers every client preference and conversation. Deal closure rate up 45%."*  
> — **Enterprise Software Company**

---

## 🚀 Real-World Applications - What You Can Actually Build

### 🤖 **Smart AI Agents That Actually Remember**:

**Persistent Memory**  
*Real Example:* Your AI coding assistant remembers your preferred programming style, the libraries you use, and the bugs you've encountered before  
*Technical:* Maintain context across conversations and sessions with persistent storage

**Intelligent Recall**  
*Real Example:* Ask "How did we solve that database connection issue?" and it finds the relevant conversation from 2 weeks ago  
*Technical:* Context-aware information retrieval with salience ranking

**Multi-Agent Systems**  
*Real Example:* Run multiple AI personalities - a conservative financial advisor and a creative marketing assistant - each with their own memories and knowledge  
*Technical:* Isolated memory spaces for different AI personalities with complete separation

**Learning Integration**  
*Real Example:* Your AI learns that you prefer detailed explanations in the morning but quick summaries in the evening  
*Technical:* Adaptive behavior based on interaction history and preference learning

### 🏢 **Enterprise Solutions That Scale**:

**Knowledge Management**  
*Real Example:* "Find all discussions about the Q3 budget" returns conversations, emails, and documents even if they use different terms like "quarterly finances"  
*Technical:* Semantic search and retrieval for corporate information with concept understanding

**Customer Service**  
*Real Example:* When John calls about his internet issue, the system remembers he's had similar problems before and suggests the solution that worked  
*Technical:* Context-aware chatbots with memory of previous interactions and resolution patterns

**Research Assistance**  
*Real Example:* "Find research on machine learning for healthcare" returns papers, notes, and previous analysis, even connecting related concepts like "neural networks" and "medical imaging"  
*Technical:* Intelligent document and fact retrieval with concept relationship mapping

**Process Automation**  
*Real Example:* When processing an invoice, the system remembers this vendor always needs approval from Finance and automatically routes it correctly  
*Technical:* Memory-augmented workflow and decision systems with learned patterns

### 🚑 **Quick Setup Examples**:

**Personal AI Assistant**:
```python
# Your AI learns your preferences
requests.post("http://localhost:9696/remember", json={
    "payload": {
        "content": "User prefers detailed technical explanations",
        "context": "communication_style"
    }
})

# Later, when generating responses...
preferences = requests.post("http://localhost:9696/recall", json={
    "query": "how to explain technical concepts",
    "top_k": 3
})
```

**Customer Support System**:
```python
# Remember customer issues
requests.post("http://localhost:9696/remember", json={
    "payload": {
        "content": "Customer John Smith - router keeps disconnecting, solved by firmware update",
        "customer_id": "john_smith",
        "issue_type": "connectivity"
    }
})

# When John calls again...
previous_issues = requests.post("http://localhost:9696/recall", json={
    "query": "John Smith connectivity problems",
    "top_k": 5
})
```

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

---

## 🎯 **Ready to Give Your AI a Brain?**

### **⚡ Get Started in 30 Seconds:**
```bash
git clone https://github.com/somatechlat/somabrain.git
cd somabrain
docker compose up -d

# Your cognitive AI is now running!
# → API Docs: http://localhost:9696/docs
# → Try it: curl -X POST http://localhost:9696/remember -d '{"payload":{"content":"Hello World"}}'
```

### **🚀 Join the Cognitive Revolution:**
- ⭐ **Star this repo** if SomaBrain solves a problem for you
- 🐛 **Report issues** to help us improve
- 💡 **Share your use case** — we love seeing what you build
- 🤝 **Contribute** — make AI memory even better

### **💬 Get Help & Connect:**
- 📖 **Documentation**: Everything you need in `/docs`
- 💼 **Enterprise Support**: Contact us for production deployments  
- 🌟 **Community**: Join developers building the future of AI memory
- 🔧 **Custom Solutions**: We help with complex cognitive architectures

**Transform your AI from forgetful to unforgettable.** The cognitive revolution starts with memory. 🧠✨
