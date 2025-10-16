# Installation Guide

**Purpose**: Simple installation instructions for end-users wanting to use SomaBrain.

**Audience**: End-users, application developers, and system integrators.

**Prerequisites**: Docker (for containerized deployment) or Python 3.10+ (for direct installation).

---

## Quick Start (Recommended)

The fastest way to get SomaBrain running is using Docker Compose:

### 1. Download and Start
```bash
# Download the latest release
curl -sSL https://raw.githubusercontent.com/somatechlat/somabrain/main/docker-compose.yml -o docker-compose.yml

# Start all services
docker compose up -d

# Wait for services to be ready (about 60 seconds)
docker compose logs -f somabrain | grep "Application startup complete"
```

### 2. Verify Installation
```bash
# Check system health
curl http://localhost:9696/health

# Expected response:
{
  "status": "healthy",
  "components": {
    "redis": {"status": "healthy"},
    "postgres": {"status": "healthy"},
    "kafka": {"status": "healthy"}
  }
}
```

### 3. Test Basic Operations
```bash
# Store a memory
curl -X POST http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -d '{
    "content": "The capital of France is Paris",
    "metadata": {"category": "geography", "confidence": 0.95}
  }'

# Recall memories
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the capital of France?",
    "k": 5
  }'
```

**Success!** You now have SomaBrain running and can store/recall memories.

---

## Installation Methods

### Docker Compose (Recommended)

**Best for**: Most users, development, testing, and small-scale production deployments.

#### System Requirements
- Docker 20.10+ and Docker Compose 2.0+
- 4GB RAM minimum, 8GB recommended
- 10GB free disk space
- Internet connection for initial image download

#### Installation Steps
```bash
# 1. Create project directory
mkdir somabrain && cd somabrain

# 2. Download configuration files
curl -sSL https://raw.githubusercontent.com/somatechlat/somabrain/main/docker-compose.yml -o docker-compose.yml
curl -sSL https://raw.githubusercontent.com/somatechlat/somabrain/main/.env.example -o .env

```bash
# 3. Configure environment (optional)
# Edit .env file to customize ports (standard container ports), memory limits, etc.

# 4. Start services
docker compose up -d

# 5. Monitor startup
docker compose logs -f
```

#### Service Access Points
- **API**: http://localhost:9696
- **Health Check**: http://localhost:9696/health  
- **API Documentation**: http://localhost:9696/docs
- **Metrics**: http://localhost:9696/metrics

### Kubernetes Deployment

**Best for**: Production environments, auto-scaling, and enterprise deployments.

#### Prerequisites
- Kubernetes cluster (v1.24+)
- Helm 3.0+
- kubectl configured

#### Installation Steps
```bash
# 1. Add Helm repository
helm repo add somabrain https://charts.somabrain.io
helm repo update

# 2. Create namespace
kubectl create namespace somabrain

# 3. Install with default values
helm install somabrain somabrain/somabrain --namespace somabrain

# 4. Get service endpoint
kubectl get service somabrain -n somabrain
```

### Python Package Installation

**Best for**: Embedding SomaBrain into existing Python applications.

#### Prerequisites  
- Python 3.10 or higher
- pip or pipx package manager

#### Installation Steps
```bash
# 1. Install SomaBrain package
pip install somabrain

# 2. Start required services (Redis, PostgreSQL)
# Using Docker for simplicity:
```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
docker run -d --name postgres -p 5432:5432 \
  -e POSTGRES_DB=somabrain \
  -e POSTGRES_USER=somabrain \
  -e POSTGRES_PASSWORD=password \
  postgres:15
```

**Environment Configuration**:
```bash
export SOMABRAIN_REDIS_URL="redis://localhost:6379/0"
export SOMABRAIN_POSTGRES_URL="postgresql://somabrain:password@localhost:5432/somabrain"
```

# 3. Configure environment
export SOMABRAIN_REDIS_URL="redis://localhost:6379/0"
export SOMABRAIN_POSTGRES_URL="postgresql://somabrain:password@localhost/somabrain"

# 4. Start SomaBrain server
python -m somabrain.app
```

---

## Configuration

### Environment Variables

The most commonly configured settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `SOMABRAIN_PORT` | `9696` | HTTP server port (Docker/direct access) |
| `SOMABRAIN_HOST` | `0.0.0.0` | Server bind address |
| `SOMABRAIN_REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `SOMABRAIN_POSTGRES_URL` | Auto-configured | PostgreSQL connection URL |
| `SOMABRAIN_LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |
| `SOMABRAIN_AUTH_DISABLED` | `false` | Disable authentication (development only) |

### Custom Configuration File

Create a `.env` file in your project directory:

```bash
# .env file for SomaBrain configuration

# Server settings  
SOMABRAIN_PORT=8080
SOMABRAIN_LOG_LEVEL=DEBUG

# Memory configuration
SOMABRAIN_MEMORY_CACHE_SIZE=1000000
SOMABRAIN_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Performance tuning
SOMABRAIN_WORKER_THREADS=4
SOMABRAIN_MAX_CONNECTIONS=100

# Security (production only)
SOMABRAIN_JWT_SECRET=your-secret-key-here
SOMABRAIN_AUTH_DISABLED=false
```

### Resource Limits

#### Memory Requirements
| Deployment Type | RAM | Storage | CPU |
|----------------|-----|---------|-----|
| Development | 2GB | 5GB | 1 core |
| Small Production | 8GB | 50GB | 2 cores |
| Large Production | 32GB | 500GB | 8 cores |

#### Docker Resource Configuration
```yaml
# docker-compose.override.yml
version: '3.8'
services:
  somabrain:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2'
        reservations:
          memory: 2G
          cpus: '1'
  
  redis:
    command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru
```

---

## Verification & Testing

### Health Check Validation
```bash
# Basic health check
curl -f http://localhost:9696/health

# Detailed component status  
curl -s http://localhost:9696/health | jq '.components'

# Performance metrics
curl -s http://localhost:9696/metrics | grep somabrain_request_duration
```

### Functional Testing
```bash
# Memory storage test
RESPONSE=$(curl -s -X POST http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -d '{"content": "Test memory", "metadata": {"test": true}}')

echo "Storage response: $RESPONSE"

# Memory recall test  
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "k": 1}' | jq '.results[0].content'
```

### Load Testing (Optional)
```bash
# Install load testing tool
pip install httpx

# Simple load test
python -c "
import httpx
import asyncio
import json

async def test_load():
    async with httpx.AsyncClient() as client:
        for i in range(100):
            response = await client.post(
                'http://localhost:9696/recall',
                json={'query': f'test query {i}', 'k': 5}
            )
            print(f'Request {i}: {response.status_code}')

asyncio.run(test_load())
"
```

---

## Upgrading

### Docker Compose Upgrade
```bash
# 1. Stop current services
docker compose down

# 2. Pull latest images
docker compose pull

# 3. Start with new images
docker compose up -d

# 4. Verify upgrade
curl http://localhost:9696/health | jq '.version'
```

### Kubernetes Upgrade
```bash
# 1. Update Helm repository
helm repo update

# 2. Upgrade release
helm upgrade somabrain somabrain/somabrain --namespace somabrain

# 3. Monitor rollout
kubectl rollout status deployment/somabrain -n somabrain
```

### Data Migration (if required)
```bash
# Check for migration requirements
curl http://localhost:9696/health | jq '.migration_needed'

# Run migrations if needed (automated in most cases)
docker compose exec somabrain python -m somabrain.migrations
```

---

## Uninstallation

### Docker Compose Removal
```bash
# Stop and remove containers
docker compose down --remove-orphans

# Remove volumes (WARNING: deletes all data)
docker compose down --volumes

# Remove images
docker rmi $(docker images "somabrain/*" -q)
```

### Kubernetes Removal
```bash
# Uninstall Helm release
helm uninstall somabrain --namespace somabrain

# Remove namespace (WARNING: deletes all data)
kubectl delete namespace somabrain
```

---

**Verification**: SomaBrain successfully installed when health check returns HTTP 200 and basic memory operations work.

**Common Errors**:
- Port conflicts → Change SOMABRAIN_PORT in .env file
- Insufficient memory → Increase Docker memory limit or system RAM
- Connection refused → Check firewall settings and Docker daemon status
- Service startup failures → Review logs with `docker compose logs`

**References**:
- [Quick Start Tutorial](quick-start-tutorial.md) for guided usage walkthrough
- [API Integration Guide](features/api-integration.md) for development integration
- [FAQ](faq.md) for troubleshooting common issues
- [Technical Manual](../technical-manual/deployment.md) for production deployment