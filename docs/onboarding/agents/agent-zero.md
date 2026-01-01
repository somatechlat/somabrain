# Agent Zero: First Steps

**Purpose**: Get an AI agent up and running with SomaBrain in 5 minutes.

## Prerequisites

- Docker and Docker Compose installed
- External memory service running at `http://localhost:9595`
- 2GB RAM available

## Quick Start (Code-Verified Steps)

### 1. Clone and Start

```bash
git clone https://github.com/somatechlat/somabrain.git
cd somabrain
docker compose up -d
```

**What This Does** (from `docker-compose.yml`):
- Starts Redis on port 30100
- Starts Kafka on port 30102
- Starts OPA on port 30104
- Starts Postgres on port 30106
- Starts Prometheus on port 30105
- Starts SomaBrain API on port 9696

### 2. Verify Health

```bash
curl http://localhost:9696/health | jq .
```

**Expected Response**:

```json
{
  "ok": true,
  "ready": true,
  "components": {
    "memory": {"http": true, "ok": true},
    "api_version": 1
  },
  "predictor_ok": true,
  "memory_ok": true,
  "embedder_ok": true,
  "kafka_ok": true,
  "postgres_ok": true,
  "opa_ok": true
}
```

### 3. Store Your First Memory

```bash
curl -X POST http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "task": "The Eiffel Tower is in Paris",
      "memory_type": "episodic"
    }
  }'
```

**Response**:

```json
{
  "ok": true,
  "success": true,
  "namespace": "somabrain_ns"
}
```

### 4. Recall the Memory

```bash
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Where is the Eiffel Tower?",
    "top_k": 3
  }' | jq .
```

**Response**:

```json
{
  "wm": [
    {
      "score": 0.92,
      "payload": {
        "task": "The Eiffel Tower is in Paris",
        "memory_type": "episodic"
      }
    }
  ],
  "memory": [...],
  "namespace": "somabrain_ns"
}
```

## Understanding the Response

### Working Memory (wm)

- **Source**: In-memory cache (`mt_wm`)
- **Capacity**: 64 items per tenant (default)
- **Scoring**: UnifiedScorer (cosine + FD + recency)
- **Fast**: No external service call

### Long-Term Memory (memory)

- **Source**: External memory service
- **Capacity**: Unlimited (backend-dependent)
- **Persistence**: Survives restarts
- **Slower**: HTTP call to backend

## Configuration Basics

### Environment Variables

**Required**:

```bash
SOMABRAIN_MEMORY_HTTP_ENDPOINT="http://localhost:9595"
SOMABRAIN_MEMORY_HTTP_TOKEN="<YOUR_TOKEN_HERE>"  # Required - set your actual token
```

**Optional**:

```bash
SOMABRAIN_MODE="full-local"  # or "prod"
SOMABRAIN_PREDICTOR_PROVIDER="mahal"  # mahal|slow|llm
SOMABRAIN_EMBED_PROVIDER="tiny"  # tiny|openai|...
```

### Config File (config.yaml)

```yaml
wm_size: 64
embed_dim: 256
use_hrr: false
rate_rps: 50.0
```

**Location**: Project root

**Loading**: Automatic via `load_config()` in `somabrain/config.py`

## Common Issues

### 1. Memory Backend Not Available

**Error**:

```json
{
  "detail": {"message": "memory backend unavailable"}
}
```

**Fix**:

```bash
# Check memory service is running
curl http://localhost:9595/health

# Verify endpoint in config
echo $SOMABRAIN_MEMORY_HTTP_ENDPOINT
```

### 2. Health Check Fails

**Symptom**: `"ready": false`

**Debug**:

```bash
# Check individual components
curl http://localhost:9696/health | jq '{
  memory_ok,
  kafka_ok,
  postgres_ok,
  opa_ok,
  embedder_ok,
  predictor_ok
}'
```

**Fix**: Start missing services

```bash
docker compose up -d somabrain_kafka somabrain_postgres somabrain_opa
```

### 3. Rate Limit Exceeded

**Error**: `429 Too Many Requests`

**Fix**: Adjust rate limits

```bash
export SOMABRAIN_RATE_RPS=100
export SOMABRAIN_RATE_BURST=200
docker compose restart somabrain_app
```

## Next Steps

1. **Read [propagation-agent.md](propagation-agent.md)** - Deep dive into memory operations
2. **Read [monitoring-agent.md](monitoring-agent.md)** - Set up observability
3. **Read [security-hardening.md](security-hardening.md)** - Secure your deployment
4. **Explore API** - Try `/context/evaluate`, `/context/feedback`, `/plan/suggest`

## API Endpoints Quick Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |
| `/remember` | POST | Store memory |
| `/recall` | POST | Retrieve memory |
| `/context/evaluate` | POST | Build context |
| `/context/feedback` | POST | Update weights |
| `/plan/suggest` | POST | Generate plan |
| `/neuromodulators` | GET/POST | Get/set neuromodulator state |

## Code Entry Points

- **Main App**: `somabrain/app.py`
- **Config**: `somabrain/config.py`
- **Memory**: `somabrain/memory/`
- **Quantum/HRR**: `somabrain/quantum.py`
- **Scoring**: `somabrain/scoring.py`
- **Learning**: `somabrain/learning/adaptation.py`

## Testing Your Setup

```bash
# Run integration tests
pytest tests/integration/

# Run core tests
pytest tests/core/

# Check code quality
ruff check somabrain/
mypy somabrain/
```

## Getting Help

- **Documentation**: `docs/` directory
- **Examples**: `examples/` directory
- **Tests**: `tests/` directory (usage examples)
- **Issues**: GitHub Issues

## Success Criteria

You're ready to build when:

- ✅ Health endpoint returns `"ready": true`
- ✅ You can store and recall a memory
- ✅ Metrics endpoint returns Prometheus data
- ✅ All Docker services are healthy
- ✅ You understand the basic API flow
