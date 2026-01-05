# 🧠 SomaBrain Quick Start Guide

> **Cognitive Runtime Engine** - Get SomaBrain running in 10 minutes

---

## Prerequisites

| Component | Minimum Version |
|-----------|-----------------|
| Docker | 24.0+ |
| Docker Compose | 2.20+ |
| Python | 3.11+ |
| RAM | 16GB |

---

## Step 1: Clone & Configure

```bash
# Clone the repository
git clone https://github.com/somatech/somabrain.git
cd somabrain

# Copy environment template
cp .env.example .env
```

### Required Environment Variables

```bash
# Database (use shared SOMA Stack database)
SOMA_DB_HOST=localhost
SOMA_DB_PORT=20432
SOMA_DB_NAME=somabrain
SOMA_DB_USER=postgres
SOMA_DB_PASSWORD=somastack2024

# Redis
REDIS_URL=redis://:somastack2024@localhost:20379/1

# Memory Service
SOMA_MEMORY_URL=http://localhost:9595
SOMA_MEMORY_API_TOKEN=your-token

# Milvus (Vector DB)
MILVUS_HOST=localhost
MILVUS_PORT=20530
```

---

## Step 2: Start Infrastructure

### With SomaAgent01 Stack (Recommended)

```bash
# Start from somaAgent01 directory
cd ../somaAgent01
docker compose up -d
```

### Standalone Mode

```bash
docker compose up -d
```

---

## Step 3: Verify Health

```bash
# Check API health
curl http://localhost:30101/health

# Expected response:
# {"status": "healthy", "component": "somabrain"}
```

---

## Step 4: Run Migrations

```bash
# With Tilt (automatic, from SomaAgent01)
tilt up

# Manual
python manage.py migrate --database=somabrain
```

---

## Port Namespace Reference

**SomaBrain uses port 30xxx:**

| Service | Port |
|---------|------|
| SomaBrain API | 30101 |
| gRPC (internal) | 30102 |
| Metrics | 30103 |

**Dependencies (from SomaAgent01 20xxx):**
- PostgreSQL: 20432
- Redis: 20379
- Milvus: 20530

---

## Step 5: Development Workflow

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt

# Run development server
uvicorn somabrain.asgi:application --host 0.0.0.0 --port 30101 --reload
```

---

## Key API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/agents/{id}/sessions` | POST | Create agent session |
| `/api/v1/agents/{id}/chat` | POST | Chat with agent (SSE streaming) |
| `/api/v1/health` | GET | Health check |
| `/api/v1/metrics` | GET | Prometheus metrics |

---

## Architecture Overview

```
SomaBrain Cognitive Modules
├── amygdala.py      - Emotional processing
├── hippocampus.py   - Memory formation
├── prefrontal.py    - Executive function
├── thalamus.py      - Sensory relay
├── basal_ganglia.py - Motor control
├── wm.py            - Working memory (22KB)
├── quantum.py       - Quantum operations (16KB)
└── sdr.py           - Sparse distributed representations
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot connect to Milvus" | Ensure SomaAgent01 stack is running |
| "Database does not exist" | Run `make reset-infra` from SomaAgent01 |
| "Memory service unavailable" | Start SomaFractalMemory first |

---

## Related Documentation

- [SomaAgent01 Quick Start](https://github.com/somatechlat/somaAgent01/blob/main/docs/QUICKSTART.md)
- [Deployment Guide](deployment/docker_deployment.md)
- [Coding Standards](development/coding-standards.md)

---

**Version**: 1.0.0 | **Last Updated**: 2026-01-04
