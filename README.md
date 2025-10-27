# SomaBrain

**A FastAPI-based cognitive AI system with working memory, long-term memory, and brain-inspired processing.**

## What Actually Exists

Based on the actual code in `somabrain/somabrain/app.py`:

### Core Components
- **FastAPI app** with cognitive middleware and error handling
- **Multi-tenant working memory** (MT-WM) with embedding-based recall
- **Memory service integration** for long-term storage
- **Quantum layer** with HRR (Holographic Reduced Representations) support
- **Neuromodulators** (dopamine, serotonin, noradrenaline, acetylcholine)
- **Salience computation** based on novelty and prediction error
- **Rate limiting and quotas** per tenant
- **Reflection system** for clustering and summarizing memories

### API Endpoints

**Core Memory Operations:**
- `GET /health` - System health check
- `POST /remember` - Store a memory
- `POST /recall` - Retrieve memories with working memory + long-term memory
- `POST /act` - Execute actions with salience-based gating
- `POST /reflect` - Cluster episodic memories and create summaries

**Brain Systems:**
- `GET /brain/stats` - Get brain component statistics
- `POST /brain/hippocampus/replay` - Trigger memory replay
- `GET /brain/hippocampus/memories` - Get consolidated memories
- `POST /brain/prefrontal/decide` - Make decisions using prefrontal cortex
- `POST /brain/prefrontal/plan` - Create plans
- `GET /brain/prefrontal/working-memory` - Get working memory contents

**Neuromodulators:**
- `GET /neuromodulators` - Get current neuromodulator state
- `POST /neuromodulators` - Set neuromodulator levels

**Advanced Systems:**
- `POST /fnom/encode` - Fourier-Neural Oscillation Memory encoding
- `POST /fnom/retrieve` - FNOM retrieval
- `POST /fractal/encode` - Fractal memory system encoding
- `POST /fractal/retrieve` - Fractal memory retrieval
- `POST /brain/encode` - Unified brain encoding (FNOM + Fractal)
- `POST /brain/transcendence` - Mathematical transcendence processing
- `POST /brain/consciousness` - Fractal consciousness processing
- `POST /brain/quantum` - Quantum cognition processing

**Graph Operations:**
- `POST /link` - Create links between memories
- `POST /graph/links` - Get links from a memory

**Utilities:**
- `POST /sleep/run` - Run NREM/REM consolidation
- `POST /migrate/export` - Export memories and working memory
- `POST /migrate/import` - Import memories and working memory
- `GET /personality` - Get personality state
- `POST /personality` - Set personality traits

### Configuration

Environment variables (prefix `SOMABRAIN_`):

**Core Settings:**
- `WM_SIZE` - Working memory capacity (default: 64)
- `EMBED_DIM` - Embedding dimension (default: 256)
- `EMBED_PROVIDER` - Embedding provider: tiny|transformer|hrr (default: tiny)
- `USE_HRR` - Enable HRR quantum layer (default: false)
- `USE_HRR_CLEANUP` - Enable HRR cleanup (default: false)

**Memory:**
- `MEMORY_MODE` - Memory backend: local|http|stub (default: local)
- `MEMORY_HTTP_ENDPOINT` - HTTP memory service endpoint
- `MEMORY_HTTP_TOKEN` - HTTP memory service token

**Rate Limiting:**
- `RATE_RPS` - Requests per second limit (default: 50.0)
- `RATE_BURST` - Burst capacity (default: 100)
- `WRITE_DAILY_LIMIT` - Daily write quota (default: 10000)

**Salience:**
- `SALIENCE_W_NOVELTY` - Novelty weight (default: 0.6)
- `SALIENCE_W_ERROR` - Error weight (default: 0.4)
- `SALIENCE_THRESHOLD_STORE` - Store threshold (default: 0.5)
- `SALIENCE_THRESHOLD_ACT` - Action threshold (default: 0.7)

**Features:**
- `USE_MICROCIRCUITS` - Enable multi-column working memory (default: false)
- `USE_SOFT_SALIENCE` - Enable soft salience (default: false)
- `USE_EXEC_CONTROLLER` - Enable executive controller (default: false)
- `USE_PLANNER` - Enable planning (default: false)
- `CONSOLIDATION_ENABLED` - Enable sleep consolidation (default: false)

### Quick Start

```bash
# Install dependencies
pip install fastapi uvicorn numpy

# Run the API
uvicorn somabrain.somabrain.app:app --reload --port 8000

# Test basic functionality
curl -X POST "http://localhost:8000/remember" \
  -H "Content-Type: application/json" \
  -d '{"payload": {"task": "test memory", "content": "This is a test"}}'

curl -X POST "http://localhost:8000/recall" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 5}'
```

### Multi-Tenancy

Use `X-Tenant-ID` header to isolate data per tenant:

```bash
curl -X POST "http://localhost:8000/remember" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: user123" \
  -d '{"payload": {"task": "user memory"}}'
```

### Authentication

Set `SOMABRAIN_API_TOKEN` and use Bearer authentication:

```bash
curl -X POST "http://localhost:8000/remember" \
  -H "Authorization: Bearer your-token-here" \
  -H "Content-Type: application/json" \
  -d '{"payload": {"task": "secure memory"}}'
```

## Architecture

The system implements a brain-inspired cognitive architecture:

1. **Thalamus Router** - Input filtering and attention
2. **Working Memory** - Fast embedding-based recall
3. **Long-term Memory** - Persistent storage via memory service
4. **Salience System** - Importance scoring based on novelty and error
5. **Neuromodulators** - Chemical-inspired state modulation
6. **Executive Control** - High-level decision making
7. **Consolidation** - Sleep-like memory processing

### Processing Flow

1. Input arrives at Thalamus for normalization
2. Working memory provides fast recall of recent items
3. Long-term memory provides persistent recall
4. Salience system scores importance based on novelty and prediction error
5. Basal ganglia makes store/act decisions based on salience
6. Executive controller can override decisions
7. Memories are stored in both working memory and long-term memory

## Development

The codebase is organized as:
- `somabrain/somabrain/app.py` - Main FastAPI application
- `somabrain/somabrain/config.py` - Configuration management
- `somabrain/somabrain/` - Core modules (quantum, memory, salience, etc.)

This README reflects the actual implemented functionality as of the current codebase.