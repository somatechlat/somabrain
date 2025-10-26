# Environment Setup

**Purpose**: Step-by-step guide to set up your complete SomaBrain development environment, from system requirements to running tests successfully.

**Audience**: New developers, contributors, and team members setting up their development machines.

**Prerequisites**: Basic command line knowledge and administrative access to install software.

---

## System Requirements

### Hardware Requirements

**Minimum**:
- CPU: 4 cores (Intel i5 or AMD equivalent)
- RAM: 8 GB
- Storage: 20 GB available space
- Network: Stable internet connection

**Recommended**:
- CPU: 8+ cores (Intel i7/i9 or AMD Ryzen)
- RAM: 16+ GB (for vector operations and ML models)
- Storage: SSD with 50+ GB space
- GPU: NVIDIA GPU with CUDA support (optional, for faster encoding)

### Operating Systems

**Primary Support**:
- macOS 12+ (Intel and Apple Silicon)
- Ubuntu 20.04+ / Debian 11+
- Windows 11 with WSL2

**Container Support**:
- Docker Desktop 4.0+
- Docker Compose 2.0+

---

## Core Dependencies

### 1. Python Environment

**Install Python 3.11**:

**macOS (using Homebrew)**:
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11
brew install python@3.11

# Verify installation
python3.11 --version
```

**Ubuntu/Debian**:
```bash
# Update package list
sudo apt update

# Install Python 3.11 and dev tools
sudo apt install -y python3.11 python3.11-dev python3.11-venv python3-pip

# Install build essentials for native extensions
sudo apt install -y build-essential libssl-dev libffi-dev

# Verify installation
python3.11 --version
```

```bash
# Update WSL2 Ubuntu
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-dev python3.11-venv
```

### 2. Node.js (for TypeScript SDK and tooling)

**Install Node.js 18+**:

**macOS**:
```bash
# Using Homebrew
brew install node@18

# Or using nvm (recommended for version management)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 18
nvm use 18
```

**Ubuntu/Debian**:
```bash
# Using NodeSource repository
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify installation
node --version
npm --version
```

### 3. Docker and Docker Compose

**macOS**:
```bash
# Download and install Docker Desktop from docker.com
# Or using Homebrew
brew install --cask docker

# Start Docker Desktop application
open -a Docker
```

**Ubuntu/Debian**:
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.15.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Restart to apply group changes
sudo systemctl restart docker
```

### 4. Git and Development Tools

**Install Git and essential tools**:

**macOS**:
```bash
# Git (usually pre-installed)
git --version

# If not installed
brew install git

# Additional development tools
brew install make curl wget jq
```

**Ubuntu/Debian**:
```bash
# Git and development tools
sudo apt install -y git make curl wget jq

# Additional build tools
sudo apt install -y gcc g++ make libpq-dev
```


## Database Setup

### PostgreSQL with pgvector Extension

**Option 1: Docker (Recommended for Development)**:
```bash
# Use the canonical compose file (docker-compose.yml) with the canonical .env
cp .env.example .env  # optional: customize ports/credentials
docker compose --env-file .env -f docker-compose.yml up -d somabrain_postgres somabrain_redis

# Verify databases are running
docker compose --env-file .env -f docker-compose.yml ps somabrain_postgres somabrain_redis
```

**Option 2: Native Installation**:

**macOS**:
```bash
# Install PostgreSQL
brew install postgresql@15

# Start PostgreSQL service
brew services start postgresql@15

# Install pgvector extension
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
make install

# Create development database
createdb somabrain_dev
psql somabrain_dev -c "CREATE EXTENSION vector;"
```

**Ubuntu/Debian**:
```bash
# Install PostgreSQL
sudo apt install -y postgresql-15 postgresql-server-dev-15

# Install pgvector
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create development database
sudo -u postgres createdb somabrain_dev
sudo -u postgres psql somabrain_dev -c "CREATE EXTENSION vector;"
```

### Redis Setup

**Docker (via docker-compose.yml)**:
```bash
# Redis is automatically started with PostgreSQL
# Access Redis CLI
docker exec -it somabrain_redis redis-cli
```

**Native Installation**:

**macOS**:
```bash
# Install Redis
brew install redis

# Start Redis service
brew services start redis

# Test connection
redis-cli ping
```

**Ubuntu/Debian**:
```bash
# Install Redis
sudo apt install -y redis-server

# Start Redis service
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test connection
redis-cli ping
```

---

## SomaBrain Repository Setup

### 1. Clone Repository

```bash
# Clone the repository
git clone https://github.com/somabrain/somabrain.git
cd somabrain

# Add upstream remote (if you forked)
git remote add upstream https://github.com/somabrain/somabrain.git

# Verify remotes
git remote -v
```

### 2. Python Environment Setup

```bash
# Create virtual environment with Python 3.11
python3.11 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows (WSL):
source venv/bin/activate

# Verify Python version in venv
python --version  # Should show Python 3.11.x
```

**Install Dependencies**:
```bash
# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install development dependencies
pip install -r requirements-dev.txt

# Install SomaBrain in editable mode
pip install -e .

# Verify installation
python -c "import somabrain; print(somabrain.__version__)"
```

### 3. Environment Configuration

**Create Environment File**:
```bash
# Copy example environment file
cp .env.example .env

# Edit configuration for development
cat << EOF > .env
# Database Configuration

# Vector Model Configuration
SOMABRAIN_VECTOR_MODEL=all-MiniLM-L6-v2
SOMABRAIN_VECTOR_DIMENSIONS=384

# API Configuration
SOMABRAIN_API_KEY=development-api-key
SOMABRAIN_LOG_LEVEL=DEBUG

# Development Settings
SOMABRAIN_ENVIRONMENT=development
SOMABRAIN_PROMETHEUS_METRICS=false
SOMABRAIN_TESTING_MODE=true
EOF
```

### 4. Database Migrations

**Run Database Migrations**:
```bash
# Check current migration status
alembic current

# Run all migrations to set up database schema
alembic upgrade head
# Verify tables were created
psql $SOMABRAIN_DATABASE_URL -c "\dt"
```

**Create Test Data** (Optional):
```bash
# Run development data seeding script
python scripts/seed_development_data.py

# Verify test data
python -c "
from somabrain.database.connection import get_database_manager
import asyncio

async def check_data():
    async with get_database_manager() as db:
        count = await db.count_memories('dev_tenant')
        print(f'Test memories created: {count}')

asyncio.run(check_data())
"
```

---

## Development Tools Setup

### 1. Code Quality Tools

**Pre-commit Hooks**:
```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# Test pre-commit setup
pre-commit run --all-files
```

**IDE Configuration**:

**VS Code** (`.vscode/settings.json`):
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".pytest_cache": true
    },
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"]
}
```

**PyCharm Configuration**:
- Set Python interpreter to `./venv/bin/python`
- Enable Black as code formatter
- Configure pytest as test runner
- Set up mypy as external tool

### 2. Performance Tools

**Install Performance Monitoring**:
```bash
# Install optional performance tools
pip install py-spy memory-profiler line-profiler

# Install GPU support (if available)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### 3. Documentation Tools

**Install Documentation Dependencies**:
```bash
# For building documentation locally
pip install mkdocs mkdocs-material

# Serve documentation locally
mkdocs serve

# Open browser to http://localhost:8000
```

---

## Verification Steps

### 1. Run Test Suite

**Unit Tests**:
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=somabrain --cov-report=html

# Check coverage report
open htmlcov/index.html
```

**Integration Tests**:
```bash
# Ensure databases are running
docker compose --env-file .env -f docker-compose.yml ps

# Run integration tests
pytest tests/integration/ -v

# Run specific test modules
pytest tests/integration/test_database.py -v
```

### 2. Start Development Server

**Run FastAPI Application**:
```bash
# Start development server
uvicorn somabrain.api.main:app --reload --host 0.0.0.0 --port 9696

# Server should start and show:
# INFO:     Uvicorn running on http://0.0.0.0:9696
# INFO:     Application startup complete.
```

**Test API Endpoints**:
```bash
# Health check
curl http://localhost:9696/health

# Store a test memory
curl -X POST http://localhost:9696/remember \
  -H "X-API-Key: development-api-key" \
  -H "X-Tenant-ID: dev_tenant" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "FastAPI is a modern web framework for Python",
    "metadata": {"category": "technical", "topic": "web_frameworks"}
  }'

# Search for memories
curl -X POST http://localhost:9696/recall \
  -H "X-API-Key: development-api-key" \
  -H "X-Tenant-ID: dev_tenant" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python web framework",
    "k": 5
  }'
```

### 3. Run Code Quality Checks

**Linting and Formatting**:
```bash
# Run all code quality checks
make lint

# Individual tools
black --check somabrain/ tests/
isort --check somabrain/ tests/
flake8 somabrain/ tests/
mypy somabrain/

# Auto-fix formatting issues
black somabrain/ tests/
isort somabrain/ tests/
```

### 4. Performance Verification

**Benchmark Tests**:
```bash
# Run performance benchmarks
pytest benchmarks/ -v --benchmark-only

# Profile memory usage

# Check vector encoding performance
python benchmarks/test_vector_encoding.py
```

---

## Development Workflow

### 1. Daily Development Process

```bash
# 1. Start development environment
docker compose --env-file .env -f docker-compose.yml up -d

# 2. Activate Python environment
source venv/bin/activate

# 3. Update dependencies (if needed)
pip install -r requirements-dev.txt

# 4. Run migrations (if new)
alembic upgrade head

# 5. Start development server
uvicorn somabrain.api.main:app --reload

# 6. Run tests in another terminal
pytest tests/unit/ -v --watch
```

### 2. Making Changes

```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Make code changes
# Edit files...

# 3. Run tests
pytest tests/

# 4. Check code quality
make lint

# 5. Commit changes
git add .
git commit -m "feat: add new feature"

# 6. Push and create PR
git push origin feature/my-feature
```

### 3. Debugging Setup

**Python Debugging**:
```python
# Add breakpoints in code
import pdb; pdb.set_trace()

# Or use ipdb for better experience
import ipdb; ipdb.set_trace()

# VS Code debugging - launch.json
{
    "name": "Python: FastAPI",
    "type": "python",
    "request": "launch",
    "program": "-m",
    "args": ["uvicorn", "somabrain.api.main:app", "--reload"],
    "console": "integratedTerminal",
    "envFile": "${workspaceFolder}/.env"
}
```

**Database Debugging**:
```bash
# Connect to development database
psql $SOMABRAIN_DATABASE_URL

\d memories

# Run test queries
SELECT COUNT(*) FROM memories;
SELECT tenant_id, COUNT(*) FROM memories GROUP BY tenant_id;

# Check pgvector extension
SELECT * FROM pg_extension WHERE extname = 'vector';
```

---

**1. Python Import Errors**:
```bash
# Check virtual environment is activated
which python  # Should point to venv/bin/python

# Reinstall in editable mode
pip install -e .

# Check PYTHONPATH
python -c "import sys; print('\n'.join(sys.path))"
```

**2. Database Connection Issues**:
```bash
# Check PostgreSQL is running
docker compose --env-file .env -f docker-compose.yml ps

# Test connection manually
psql postgresql://somabrain:development_password@localhost/somabrain_dev

# Check pgvector extension
psql -c "SELECT * FROM pg_available_extensions WHERE name = 'vector';"
```

**3. Vector Encoding Slow**:
```bash
# Check available memory
free -h

# Monitor CPU usage during encoding
top -p $(pgrep python)

# Use smaller model for development
export SOMABRAIN_VECTOR_MODEL=all-MiniLM-L6-v2
```

**4. Test Failures**:
```bash
# Run tests with detailed output
pytest tests/ -vvv -s

# Run specific failing test
pytest tests/unit/test_memory_manager.py::test_specific_function -vvv

# Check test database isolation
pytest tests/integration/ --create-db
```

### Getting Help

**Check Logs**:
```bash
# Application logs
tail -f logs/somabrain.log

# Docker logs
docker compose --env-file .env -f docker-compose.yml logs -f

# Database logs
docker compose --env-file .env -f docker-compose.yml logs postgres
```

**Performance Monitoring**:
```bash
# Check system resources
htop

# Monitor database connections
psql -c "SELECT count(*) FROM pg_stat_activity;"

# Check Redis memory usage
redis-cli info memory
```

**Verification**: Environment setup is complete when all tests pass, the development server starts successfully, and you can store and retrieve memories via the API.

---

**Common Errors**:

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'somabrain'` | Run `pip install -e .` in activated venv |
| `psycopg2.OperationalError: could not connect` | Check PostgreSQL is running and credentials are correct |
| `redis.exceptions.ConnectionError` | Verify Redis is running on port 6379 |
| `alembic.util.exc.CommandError` | Check database URL and run `alembic upgrade head` |
| Vector encoding very slow | Use GPU acceleration or smaller model |

**References**:
- [Codebase Walkthrough](codebase-walkthrough.md) for architecture understanding
- [First Contribution](first-contribution.md) for practical development workflow
- [Setup Checklist](checklists/setup-checklist.md) for verification steps
- [Troubleshooting Guide](resources/troubleshooting.md) for additional help