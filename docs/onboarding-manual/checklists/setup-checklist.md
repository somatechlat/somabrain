# Setup Verification Checklist

**Purpose**: Verify that your SomaBrain development environment is correctly configured and functional.

**Audience**: New developers, agent coders, and anyone setting up local development.

**Prerequisites**: Completed [Environment Setup](../environment-setup.md) guide.

---

## Quick Verification (5 minutes)

Run these commands to verify basic setup:

```bash
# 1. Verify Python environment
python --version                    # Should show Python 3.10+
which python                        # Should point to your venv/uv environment

# 2. Verify SomaBrain installation
python -c "import somabrain; print('✅ SomaBrain imported')"

# 3. Verify development tools
ruff --version                      # Should show ruff version
mypy --version                      # Should show mypy version
pytest --version                    # Should show pytest version

# 4. Verify Docker services
curl -f http://localhost:9696/health | jq '.status'  # Should return "healthy"
```

**Expected Result**: All commands complete without errors and show expected versions/outputs.

---

## Comprehensive Environment Checklist

### ✅ Python Environment

- [ ] **Python Version**: 3.10 or higher
  ```bash
  python --version
  # Expected: Python 3.10.x or Python 3.11.x
  ```

- [ ] **Virtual Environment**: Active and isolated
  ```bash
  which python
  # Expected: Path containing .venv or uv environment
  ```

- [ ] **SomaBrain Package**: Editable installation
  ```bash
  pip show somabrain | grep Location
  # Expected: Location pointing to your repo directory
  ```

- [ ] **Development Dependencies**: All installed
  ```bash
  pip list | grep -E "(ruff|mypy|pytest)"
  # Expected: All three packages listed with versions
  ```

### ✅ Docker Services

- [ ] **Docker Running**: Docker daemon accessible
  ```bash
  docker --version && docker compose --version
  # Expected: Docker 20.10+ and Compose 2.0+
  ```

- [ ] **Services Started**: All containers running
  ```bash
  docker compose ps
  # Expected: somabrain, redis, postgres, kafka all "Up"
  ```

- [ ] **Port Configuration**: Services accessible on expected ports
  ```bash
  cat ports.json | jq
  # Expected: JSON with port assignments for all services
  ```

- [ ] **Health Checks**: All services report healthy
  ```bash
  curl -s http://localhost:9696/health | jq '.components'
  # Expected: All components show "healthy" status
  ```

### ✅ Development Tools

- [ ] **Code Linting**: Ruff configured and working
  ```bash
  ruff check --version && ruff check . --quiet
  # Expected: Version displayed, no linting errors
  ```

- [ ] **Type Checking**: MyPy configured correctly
  ```bash
  mypy --version && mypy somabrain --quiet
  # Expected: Version displayed, no type errors
  ```

- [ ] **Testing Framework**: Pytest functional
  ```bash
  pytest --version && pytest --collect-only -q | head -5
  # Expected: Version and list of discovered tests
  ```

- [ ] **Git Configuration**: Proper git setup
  ```bash
  git config --get user.name && git config --get user.email
  # Expected: Your name and email configured
  ```

### ✅ Configuration Validation

- [ ] **Environment Variables**: Core variables set
  ```bash
  echo $SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS $SOMABRAIN_FORCE_FULL_STACK
  # Expected: "1 1" showing backend enforcement enabled
  ```

- [ ] **Configuration Loading**: Settings accessible
  ```bash
  python -c "from somabrain.config import get_config; print(get_config().redis_url)"
  # Expected: Redis URL (likely redis://localhost:6379/0)
  ```

- [ ] **Service Connectivity**: All backends reachable
  ```bash
  python -c "
  import redis
  r = redis.Redis.from_url('redis://localhost:6379/0')
  print('✅ Redis:', r.ping())
  "
  # Expected: "✅ Redis: True"
  ```

---

## Functional Testing Checklist

### ✅ Memory Operations

- [ ] **Store Memory**: Basic remember operation works
  ```bash
  curl -X POST http://localhost:9696/remember \
    -H "Content-Type: application/json" \
    -d '{"content": "Setup verification test", "metadata": {"test": true}}' \
    | jq '.success'
  # Expected: true
  ```

- [ ] **Recall Memory**: Basic recall operation works
  ```bash
  curl -X POST http://localhost:9696/recall \
    -H "Content-Type: application/json" \
    -d '{"query": "setup verification", "k": 1}' \
    | jq '.results | length'
  # Expected: 1 (found the test memory)
  ```

- [ ] **Memory Persistence**: Data survives service restart
  ```bash
  docker compose restart somabrain
  sleep 5
  curl -X POST http://localhost:9696/recall \
    -H "Content-Type: application/json" \
    -d '{"query": "setup verification", "k": 1}' \
    | jq '.results | length'
  # Expected: 1 (memory still exists)
  ```

### ✅ Development Workflow

- [ ] **Code Changes**: Hot reload works (if using --reload)
  ```bash
  # Make a small change to somabrain/app.py (add a comment)
  # Check logs for reload message
  docker compose logs somabrain | grep -i reload
  # Expected: Reload message or no errors
  ```

- [ ] **Test Execution**: Full test suite passes
  ```bash
  pytest tests/ -v --tb=short
  # Expected: All tests pass (some may be skipped)
  ```

- [ ] **Quality Gates**: All quality checks pass
  ```bash
  ruff check . && ruff format --check . && mypy somabrain
  # Expected: All commands succeed with no errors
  ```

---

## Performance Verification

### ✅ Response Times

- [ ] **Health Check Latency**: < 100ms
  ```bash
  curl -w "Response time: %{time_total}s\n" -s http://localhost:9696/health -o /dev/null
  # Expected: < 0.1s response time
  ```

- [ ] **Memory Operation Latency**: < 500ms for simple operations
  ```bash
  time curl -s -X POST http://localhost:9696/remember \
    -H "Content-Type: application/json" \
    -d '{"content": "latency test", "metadata": {"test": true}}' > /dev/null
  # Expected: real time < 0.5s
  ```

### ✅ Resource Usage

- [ ] **Memory Consumption**: Reasonable resource usage
  ```bash
  docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
  # Expected: somabrain container using < 1GB RAM, < 50% CPU
  ```

- [ ] **Storage Usage**: Database and cache sizes reasonable
  ```bash
  docker compose exec redis redis-cli info memory | grep used_memory_human
  # Expected: < 100MB for basic testing
  ```

---

## Troubleshooting Failed Checks

### Python Issues

| Check Failed | Likely Cause | Solution |
|--------------|-------------|----------|
| Python version wrong | System Python being used | Activate virtual environment: `source .venv/bin/activate` |
| Import errors | Package not installed | Run `uv pip install --editable .[dev]` |
| Tool versions missing | Dependencies not installed | Run `uv pip sync uv.lock` |

### Docker Issues

| Check Failed | Likely Cause | Solution |
|--------------|-------------|----------|
| Docker not accessible | Daemon not running | Start Docker Desktop or `sudo systemctl start docker` |
| Port conflicts | Another service using ports | Run `./scripts/assign_ports.sh` for dynamic ports |
| Service unhealthy | Configuration or startup issue | Check logs: `docker compose logs [service]` |

### Configuration Issues

| Check Failed | Likely Cause | Solution |
|--------------|-------------|----------|
| Environment vars missing | .env.local not created | Run `./scripts/dev_up.sh` to generate config |
| Service connectivity failed | Network or firewall issue | Check Docker network: `docker network ls` |
| Settings not loading | YAML syntax error | Validate YAML: `python -c "import yaml; yaml.safe_load(open('config.yaml'))"` |

---

## Success Criteria

### ✅ Development Ready
You're ready for development when:
- [ ] All checklist items above pass ✅
- [ ] You can run `ruff check . && mypy somabrain && pytest` successfully
- [ ] Memory operations work via API calls
- [ ] You can make code changes and see them reflected

### ✅ Ready for First Contribution
You're ready for your first contribution when:
- [ ] Development environment fully functional
- [ ] You understand the [Contribution Process](../first-contribution.md)
- [ ] You can create a branch and submit a PR
- [ ] All quality gates pass in your development environment

---

**Verification**: Complete this entire checklist successfully to confirm proper setup.

**Common Errors**:
- Checklist items fail → Use troubleshooting table above for specific solutions
- Services won't start → Check Docker daemon and port availability
- Tests fail → Verify environment configuration and service health

**References**:
- [Environment Setup](../environment-setup.md) for detailed setup instructions
- [Troubleshooting Guide](../resources/troubleshooting.md) for additional help
- [First Contribution](../first-contribution.md) for next steps after setup
- [Development Manual](../../development-manual/local-setup.md) for advanced configuration
