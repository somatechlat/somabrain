# Local Development Setup

**Purpose**: One-page guide to set up a local SomaBrain development environment.

**Audience**: Software engineers and contributors setting up local development.

**Prerequisites**: Python 3.10+, Docker, Git, and basic command line familiarity.

---

## Quick Setup (10 minutes)

### 1. Install Dependencies
```bash
# Install uv for fast dependency management
pipx install uv

# Or via pip if pipx not available
pip install --user uv
```

### 2. Clone and Setup Repository
```bash
# Clone the repository
git clone https://github.com/somatechlat/somabrain.git
cd somabrain

# Install Python dependencies with locked versions
uv pip install --editable .[dev]
uv pip sync uv.lock
```

### 3. Start Development Stack
```bash
# Start all services with standard container ports
./scripts/assign_ports.sh  # Creates .env with standard port mapping
docker compose up -d
# Or bootstrap everything in one shot
./scripts/dev_up.sh --rebuild

# Verify services are running
curl -fsS http://localhost:9696/health | jq
```

### 4. Verify Installation
```bash
# Run linting and type checking
ruff check .
mypy somabrain

# Run test suite
pytest
# Canonical smoke (mirrors CI backend-enforcement run)
uv run pytest -q

# Check development environment
python -c "import somabrain; print('✅ SomaBrain imported successfully')"
```

---

## Detailed Setup Instructions

### Python Environment Configuration

#### Using uv (Recommended)
```bash
# Install exact dependency versions from lockfile
uv pip install --editable .[dev]
uv pip sync uv.lock

# Update dependencies (when adding new packages)
uv pip compile pyproject.toml --extra dev --lockfile uv.lock
uv pip sync uv.lock
```

#### Using Traditional pip/venv
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -e .[dev]
```

### Docker Stack Configuration

#### Environment Variables
The Docker stack uses direct port access (standard container ports):
```bash
# Core settings for local development
SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1              # Enforce external backend usage
SOMABRAIN_FORCE_FULL_STACK=1         # Require all backing services
SOMABRAIN_REQUIRE_MEMORY=1           # Memory service must be available
SOMABRAIN_MODE=development           # Development mode identifier

# Service access (standard container ports, direct to localhost)
SOMABRAIN_HOST_PORT=9696             # SomaBrain API
REDIS_HOST_PORT=6379                 # Redis
KAFKA_HOST_PORT=9092                 # Kafka
OPA_HOST_PORT=8181                   # OPA
POSTGRES_HOST_PORT=5432              # Postgres

# Container-internal URLs (used within compose network)
SOMABRAIN_REDIS_URL=redis://somabrain_redis:6379/0
SOMABRAIN_KAFKA_URL=kafka://somabrain_kafka:9092    # Canonical app-level Kafka setting
SOMABRAIN_MEMORY_HTTP_ENDPOINT=http://host.docker.internal:9595

# Database
SOMABRAIN_POSTGRES_DSN=postgresql://soma:soma_pass@somabrain_postgres:5432/somabrain

# Dev-only auto-migrations (off by default). Prefer the one-shot job below.
SOMABRAIN_AUTO_MIGRATE=0
```

#### Manual Docker Compose
```bash
# If assign_ports.sh doesn't work, manual docker setup:
docker compose up -d somabrain_redis somabrain_postgres somabrain_kafka somabrain_opa

# Check service health
docker compose ps
docker compose logs somabrain_app
```

#### Database Migrations (Dev)
```bash
# Preferred: run one-shot Alembic migrations for dev
./scripts/migrate_db.sh           # stamps/aligns if schema already exists

# Or, run the dev migration service directly
docker compose --profile dev run --rm somabrain_db_migrate

# Optional (dev-only): enable auto-migrate on API startup
echo "SOMABRAIN_AUTO_MIGRATE=1" >> .env
docker compose up -d somabrain_app
```

### IDE Configuration

#### VS Code Setup
```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "./.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "ruff",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "tests/"
  ]
}
```

#### PyCharm Setup
1. Open project directory
2. Configure Python interpreter: `.venv/bin/python`
3. Enable ruff and mypy inspections
4. Set test runner to pytest
5. Configure run configurations for common tasks

---

## Development Workflow

### Code Quality Checks
```bash
# Before committing, run full quality pipeline:
ruff check .                    # Linting
ruff format .                   # Code formatting
mypy somabrain                 # Type checking
pytest                         # Test suite
```

### Environment Management
```bash
# Check current configuration
python -c "from somabrain.config import get_config; print(get_config())"

# Reload configuration after YAML changes
python -c "from somabrain.config import reload_config; reload_config()"

# View active ports
cat ports.json | jq
```

### Memory Environment Helper
```bash
# Generate host-friendly memory env exports (.memory.env) from .env
scripts/export_memory_env.sh

# Apply to current shell for host tools (benchmarks, curl, etc.)
source scripts/.memory.env

# Quick probe runs automatically; acceptable statuses are 200/404/422.
# If you see 401/403, set a valid SOMABRAIN_MEMORY_HTTP_TOKEN.
```

### Testing and Validation
```bash
# Run specific test categories
pytest tests/test_memory_client.py      # Memory tests
pytest tests/math/                      # Mathematical property tests
pytest -k "not slow"                    # Skip slow integration tests

# Test with backend enforcement validation
SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1 pytest tests/test_remember_batch.py

# Performance testing
python run_learning_test.py             # Canonical numerics validation
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
SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1          # Enable mathematical validation
SOMABRAIN_FORCE_FULL_STACK=1     # Require all services
SOMABRAIN_REQUIRE_MEMORY=1       # Require memory backend
SOMABRAIN_MODE=development       # Dev mode governs auth policy
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

## Troubleshooting

### Common Setup Issues

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Port conflicts | `docker compose up` fails | Run `./scripts/assign_ports.sh` to find free ports |
| Python import errors | `ImportError: No module named 'somabrain'` | Ensure `pip install -e .` completed successfully |
| Redis connection refused | Tests fail with Redis errors | Check `docker compose ps` and restart Redis |
| Permission denied | Docker commands fail | Add user to docker group: `sudo usermod -aG docker $USER` |
| Slow dependency install | `uv pip install` takes >5 minutes | Check network connection and PyPI mirror configuration |

### Service Debugging
```bash
# Check Docker service logs
docker compose logs redis
docker compose logs postgres
docker compose logs kafka

# Test service connectivity
redis-cli -h localhost -p $(jq -r '.redis.port' ports.json) ping
psql -h localhost -p $(jq -r '.postgres.port' ports.json) -U somabrain -d somabrain -c "SELECT 1;"

# Debug SomaBrain API
PYTHONPATH=$(pwd) uvicorn somabrain.app:app --host 127.0.0.1 --port 9696 --reload
```

### Development Environment Reset
```bash
# Complete environment reset
docker compose down --remove-orphans --volumes
rm -f .env ports.json
./scripts/dev_up.sh --rebuild

# Python environment reset
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
uv pip install --editable .[dev]
```

---

## Development Commands Reference

### Daily Development
```bash
# Start development session
source .venv/bin/activate        # Activate Python environment
./scripts/dev_up.sh             # Start services (if not running)

# Code quality loop
ruff check . --fix              # Auto-fix linting issues
mypy somabrain                  # Type check
pytest tests/test_specific.py   # Run relevant tests

# End of session
docker compose stop             # Stop services to save resources
```

### Dependency Management
```bash
# Add new dependency
echo "new-package" >> requirements-dev.txt
uv pip compile pyproject.toml --extra dev --lockfile uv.lock
uv pip sync uv.lock

# Update all dependencies
uv pip compile pyproject.toml --extra dev --lockfile uv.lock --upgrade
uv pip sync uv.lock
```

### Docker Operations
```bash
# View service status
docker compose ps

# Restart specific service
docker compose restart redis

# View live logs
docker compose logs -f somabrain

# Execute commands in containers
docker compose exec redis redis-cli
docker compose exec postgres psql -U somabrain
```

---

**Verification**: Run `ruff check . && mypy somabrain && pytest` successfully to confirm setup.

**Expected Output**:
- ruff: No linting errors
- mypy: Success, no issues found
- pytest: All tests pass (may skip some integration tests in CI-only mode)

**Common Errors**:
- ModuleNotFoundError → Ensure virtual environment activated and `pip install -e .` completed
- Docker connection errors → Verify Docker daemon running and user has docker group permissions
- Test failures → Check `.env` configuration and service health

**References**:
- [Coding Standards](coding-standards.md) for style guide and linting rules
- [Testing Guidelines](testing-guidelines.md) for test strategy and frameworks
- [Contribution Process](contribution-process.md) for PR workflow
- [Architecture Overview](../technical-manual/architecture.md) for system understanding

---

## Notes on Linux host.docker.internal

On some Linux hosts, `host.docker.internal` isn’t resolved automatically inside containers. If your memory service runs on the host, set `SOMABRAIN_MEMORY_HTTP_ENDPOINT` in `.env` to the host IP address explicitly (for example: `http://192.168.1.10:9595`).
