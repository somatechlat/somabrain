# Installation Guide

**Purpose**: Simple installation instructions for end-users wanting to use SomaBrain.

**Audience**: End-users, application developers, and system integrators.

**Prerequisites**: Docker (for containerized deployment) or Python 3.10+ (for direct installation).

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