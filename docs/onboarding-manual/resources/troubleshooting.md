# Troubleshooting

**Purpose**: Comprehensive troubleshooting guide for common issues encountered during SomaBrain development, deployment, and usage.

**Audience**: Developers, system administrators, and users experiencing technical difficulties with SomaBrain.

**Prerequisites**: Basic understanding of [Environment Setup](../environment-setup.md) and [Codebase Walkthrough](../codebase-walkthrough.md).

---

## Development Environment Issues

### Python Environment Problems

**Issue: ModuleNotFoundError: No module named 'somabrain'**

**Symptoms**:
```bash
$ python -c "import somabrain"
ModuleNotFoundError: No module named 'somabrain'
```

**Diagnosis**:
```bash
# Check if virtual environment is activated
which python
# Should point to venv/bin/python

# Check installed packages
pip list | grep somabrain

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"
```

**Solutions**:
```bash
# Solution 1: Activate virtual environment
source venv/bin/activate

# Solution 2: Install in editable mode
pip install -e .

# Solution 3: Reinstall dependencies
pip install -r requirements-dev.txt
pip install -e .

# Solution 4: Check Python version consistency
python --version  # Should be 3.11.x
```

**Issue: ImportError: attempted relative import with no known parent package**

**Symptoms**:
```python
# In test files or scripts
from ..core.memory_manager import MemoryManager
# ImportError: attempted relative import with no known parent package
```

**Solutions**:
```bash
# Solution 1: Run as module
python -m pytest tests/
python -m somabrain.api.main

# Solution 2: Use absolute imports
from somabrain.core.memory_manager import MemoryManager

# Solution 3: Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Database Connection Issues

**Issue: psycopg2.OperationalError: could not connect to server**

**Symptoms**:
```
psycopg2.OperationalError: could not connect to server: Connection refused
    Is the server running on host "localhost" and accepting
    TCP/IP connections on port 5432?
```

**Diagnosis**:
```bash
# Check if PostgreSQL is running
ps aux | grep postgres

# Check if port 5432 is in use
sudo netstat -tulpn | grep :5432

# Test connection manually
psql postgresql://somabrain:password@localhost/somabrain_dev

# Check Docker containers
docker compose --env-file .env.local -f docker-compose.yml ps
```

**Solutions**:
```bash
# Solution 1: Start PostgreSQL service
# On macOS with Homebrew:
brew services start postgresql@15

# On Ubuntu/Debian:
sudo systemctl start postgresql

# Solution 2: Start Docker development environment
docker compose --env-file .env.local -f docker-compose.yml up -d somabrain_postgres somabrain_redis

# Solution 3: Check environment variables
echo $SOMABRAIN_DATABASE_URL

# Solution 4: Verify database exists
createdb somabrain_dev
```

**Issue: relation "memories" does not exist**

**Symptoms**:
```
psycopg2.errors.UndefinedTable: relation "memories" does not exist
```

**Solutions**:
```bash
# Run database migrations
alembic upgrade head

# Check migration status
alembic current
alembic history

# Reset database (development only)
dropdb somabrain_dev
createdb somabrain_dev
alembic upgrade head
```

### Vector Operations Issues

**Issue: Vector encoding is very slow**

**Symptoms**:
- Memory storage taking >5 seconds per item
- High CPU usage during encoding
- Memory usage growing continuously

**Diagnosis**:
```bash
# Monitor resource usage
htop

# Profile Python process
py-spy top --pid <python_process_id>

# Check model loading
python -c "
from sentence_transformers import SentenceTransformer
import time
start = time.time()
model = SentenceTransformer('all-MiniLM-L6-v2')
print(f'Model load time: {time.time() - start:.2f}s')
"
```

**Solutions**:
```bash
# Solution 1: Use GPU acceleration
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Solution 2: Use smaller model for development
export SOMABRAIN_VECTOR_MODEL=all-MiniLM-L6-v2

# Solution 3: Batch encoding
# Process multiple texts together instead of one by one

# Solution 4: Model caching
# Ensure model is loaded once and reused
```

**Issue: Vector similarity results are poor**

**Symptoms**:
- Unrelated memories appearing in search results
- Low similarity scores for obviously related content
- Inconsistent search behavior

**Diagnosis**:
```python
# Check vector normalization
import numpy as np
vector = model.encode("test text")
print(f"Vector norm: {np.linalg.norm(vector)}")
print(f"Vector shape: {vector.shape}")
print(f"Vector type: {vector.dtype}")

# Test similarity calculation
v1 = model.encode("Python programming")
v2 = model.encode("Programming in Python")
similarity = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
print(f"Expected high similarity: {similarity}")
```

**Solutions**:
```python
# Solution 1: Ensure vector normalization
def normalize_vector(vector):
    return vector / np.linalg.norm(vector)

# Solution 2: Check text preprocessing
def preprocess_text(text):
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    # Handle encoding issues
    text = text.encode('utf-8', errors='ignore').decode('utf-8')
    return text

# Solution 3: Use appropriate similarity threshold
# Typical thresholds: 0.3-0.7 depending on use case
```

---

## API and Server Issues

### FastAPI Server Problems

**Issue: Server fails to start**

**Symptoms**:
```bash
$ uvicorn somabrain.api.main:app --reload
ERROR: Error loading ASGI app. Could not import module "somabrain.api.main".
```

**Diagnosis**:
```bash
# Check if main module exists
ls somabrain/api/main.py

# Test import directly
python -c "from somabrain.api.main import app"

# Check for syntax errors
python -m py_compile somabrain/api/main.py
```

**Solutions**:
```bash
# Solution 1: Install in editable mode
pip install -e .

# Solution 2: Run from correct directory
cd /path/to/somabrain
uvicorn somabrain.api.main:app --reload

# Solution 3: Use full module path
uvicorn somabrain.api.main:app --reload --pythonpath .

# Solution 4: Check dependencies
pip install -r requirements-dev.txt
```

**Issue: 500 Internal Server Error**

**Symptoms**:
- API endpoints returning 500 errors
- No helpful error message to client

**Diagnosis**:
```bash
# Check server logs
uvicorn somabrain.api.main:app --log-level debug

# Check application logs
tail -f logs/somabrain.log

# Test with minimal request
curl -X GET http://localhost:9696/health
```

**Solutions**:
```python
# Solution 1: Add proper error handling
from fastapi import HTTPException
from somabrain.exceptions import SomaBrainError

@app.exception_handler(SomaBrainError)
async def somabrain_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": str(exc)}
    )

# Solution 2: Enable debug mode
app = FastAPI(debug=True)

# Solution 3: Add logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Authentication Issues

**Issue: 401 Unauthorized errors**

**Symptoms**:
```bash
$ curl -X POST http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -d '{"content": "test"}'
{"detail": "Missing API key"}
```

**Solutions**:
```bash
# Add required headers
curl -X POST http://localhost:9696/remember \
  -H "X-API-Key: your-api-key" \
  -H "X-Tenant-ID: your-tenant" \
  -H "Content-Type: application/json" \
  -d '{"content": "test memory"}'

# Check environment configuration
echo $SOMABRAIN_API_KEY

# Verify tenant exists in database
psql $SOMABRAIN_DATABASE_URL -c "SELECT * FROM tenants;"
```

### Rate Limiting Issues

**Issue: 429 Too Many Requests**

**Symptoms**:
```json
{
  "error": "Rate limit exceeded: 101/100 per minute",
  "retry_after": 45
}
```

**Solutions**:
```python
# Solution 1: Implement exponential backoff
import time
import random

async def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await func()
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            delay = min(2 ** attempt + random.uniform(0, 1), 60)
            await asyncio.sleep(delay)

# Solution 2: Batch requests
# Process multiple items in single API call

# Solution 3: Increase rate limits (development)
export SOMABRAIN_RATE_LIMIT_REQUESTS=10000
```

---

## Testing Issues

### Test Execution Problems

**Issue: Tests fail with database connection errors**

**Symptoms**:
```
tests/test_memory.py::test_store_memory FAILED
E   psycopg2.OperationalError: FATAL: database "test_somabrain" does not exist
```

**Solutions**:
```bash
# Solution 1: Create test database
createdb test_somabrain

# Solution 2: Use test database URL
export SOMABRAIN_TEST_DATABASE_URL=postgresql://localhost/test_somabrain

# Solution 3: Use pytest fixtures
# Ensure test database setup/teardown

# Solution 4: Run with Docker
docker-compose -f docker-compose.test.yml up -d
pytest tests/
```

**Issue: Tests pass individually but fail when run together**

**Symptoms**:
- `pytest tests/unit/test_memory.py::test_store` - PASS
- `pytest tests/unit/` - FAIL (same test)

**Diagnosis**:
```python
# Check for shared state
pytest tests/ -v --tb=short

# Run with random order
pytest tests/ --random-order

# Check for database state pollution
pytest tests/ --create-db
```

**Solutions**:
```python
# Solution 1: Proper test isolation
@pytest.fixture(autouse=True)
async def cleanup_database():
    yield
    # Clean up after each test
    await database.execute("TRUNCATE TABLE memories CASCADE")

# Solution 2: Use separate test tenant per test
@pytest.fixture
def test_tenant():
    return f"test_tenant_{uuid.uuid4().hex[:8]}"

# Solution 3: Mock external dependencies
@pytest.fixture(autouse=True)
def mock_redis():
    with patch('somabrain.cache.redis_client') as mock:
        yield mock
```

### Performance Test Issues

**Issue: Benchmarks are inconsistent**

**Symptoms**:
- Same test shows very different execution times
- Memory usage varies significantly between runs

**Solutions**:
```python
# Solution 1: Warm up before benchmarking
def warmup_phase():
    # Run operations once to warm up caches
    for _ in range(10):
        model.encode("warmup text")

# Solution 2: Use multiple iterations
@pytest.mark.benchmark
def test_encoding_performance(benchmark):
    result = benchmark.pedantic(
        encode_text,
        args=("test content",),
        iterations=100,
        rounds=5
    )

# Solution 3: Control environment
# - Close other applications
# - Use dedicated test machine
# - Monitor system resources
```

---

## Deployment Issues

### Docker Problems

**Issue: Docker build fails**

**Symptoms**:
```bash
$ docker build -t somabrain .
Step 5/10 : RUN pip install -r requirements.txt
ERROR: Could not find a version that satisfies the requirement torch==1.13.0
```

**Solutions**:
```dockerfile
# Solution 1: Use multi-stage build
FROM python:3.11-slim as builder
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

FROM python:3.11-slim
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*

# Solution 2: Update requirements
pip-compile requirements.in

# Solution 3: Use platform-specific requirements
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

**Issue: Container runs but API is not accessible**

**Symptoms**:
- Container starts successfully
- Health check inside container works
- External requests fail to connect

**Diagnosis**:
```bash
# Check container status
docker ps

# Check port mapping
docker port somabrain_api

# Test internal connectivity
docker exec -it somabrain_api curl http://localhost:9696/health

# Check host networking
netstat -tulpn | grep :9696
```

**Solutions**:
```bash
# Solution 1: Fix port mapping
docker run -p 9696:9696 somabrain

# Solution 2: Use correct bind address
uvicorn app:main --host 0.0.0.0 --port 9696

# Solution 3: Check firewall settings
sudo ufw allow 9696
```

### Environment Configuration

**Issue: Environment variables not loading**

**Symptoms**:
- Application uses default values instead of configured ones
- Configuration errors at startup

**Diagnosis**:
```bash
# Check if .env file exists
ls -la .env

# Check environment variables in container
docker exec -it somabrain_api printenv | grep SOMABRAIN

# Test configuration loading
python -c "
from somabrain.config import AppConfig
config = AppConfig()
print(config.database_url)
"
```

**Solutions**:
```bash
# Solution 1: Mount .env file
docker run -v $(pwd)/.env:/app/.env somabrain

# Solution 2: Pass environment variables
docker run -e SOMABRAIN_DATABASE_URL=postgresql://... somabrain

# Solution 3: Use docker-compose with env_file
# docker-compose.yml
services:
  api:
    env_file: .env
```

---

## Performance Issues

### Memory Usage Problems

**Issue: High memory consumption**

**Symptoms**:
- Python process using >8GB RAM
- Out of memory errors
- Slow performance

**Diagnosis**:
```bash
# Monitor memory usage
ps aux | grep python
htop

# Profile memory usage
pip install memory_profiler
python -m memory_profiler your_script.py

# Check for memory leaks
py-spy dump --pid <python_process_id>
```

**Solutions**:
```python
# Solution 1: Batch processing
def process_in_batches(items, batch_size=100):
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        process_batch(batch)
        # Force garbage collection after each batch
        gc.collect()

# Solution 2: Use generators
def memory_efficient_processing():
    for item in large_dataset:
        yield process_item(item)

# Solution 3: Connection pooling
async with database_pool.acquire() as conn:
    # Use connection and automatically return to pool
    pass
```

### Database Performance Issues

**Issue: Slow query performance**

**Symptoms**:
- API responses taking >5 seconds
- Database CPU usage at 100%
- Query timeouts

**Diagnosis**:
```sql
-- Check slow queries
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Analyze query plan
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM memories
WHERE tenant_id = 'test'
ORDER BY vector_encoding <=> '[1,2,3]'::vector
LIMIT 10;

-- Check index usage
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE tablename = 'memories';
```

**Solutions**:
```sql
-- Solution 1: Add missing indexes
CREATE INDEX CONCURRENTLY idx_memories_tenant_vector
ON memories (tenant_id)
INCLUDE (vector_encoding);

-- Solution 2: Update table statistics
ANALYZE memories;

-- Solution 3: Optimize query
-- Use appropriate vector index type (HNSW vs IVFFlat)
CREATE INDEX idx_memories_vector_hnsw
ON memories USING hnsw (vector_encoding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

---

## Security Issues

### Authentication Problems

**Issue: JWT token errors**

**Symptoms**:
```json
{
  "error": "Token has expired",
  "timestamp": "2024-01-15T10:30:45Z"
}
```

**Solutions**:
```python
# Solution 1: Check token expiration
import jwt
from datetime import datetime

def validate_token(token):
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        exp_time = datetime.fromtimestamp(payload['exp'])
        if datetime.utcnow() > exp_time:
            raise jwt.ExpiredSignatureError()
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")

# Solution 2: Implement token refresh
async def refresh_token(refresh_token):
    # Validate refresh token and issue new access token
    pass

# Solution 3: Increase token expiration (development only)
token_expiration_hours = 24  # Instead of 1 hour
```

### Data Security Issues

**Issue: PII detected in logs**

**Symptoms**:
- Personal information appearing in application logs
- Security audit findings

**Solutions**:
```python
# Solution 1: Sanitize log messages
import re

def sanitize_for_logging(text):
    # Remove email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    # Remove phone numbers
    text = re.sub(r'\b\d{3}-\d{3}-\d{4}\b', '[PHONE]', text)
    # Remove SSN patterns
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
    return text

# Solution 2: Use structured logging
logger.info("Memory stored", extra={
    "memory_id": memory_id,
    "content_length": len(content),
    # Don't log actual content
})

# Solution 3: Enable PII detection
from somabrain.security import detect_pii
pii_findings = detect_pii(content)
if pii_findings:
    logger.warning("PII detected in content", extra={
        "pii_types": [f.type for f in pii_findings],
        "memory_id": memory_id
    })
```

---

## Integration Issues

### SDK Problems

**Issue: Python SDK connection failures**

**Symptoms**:
```python
from somabrain import SomaBrainClient
client = SomaBrainClient(api_key="test", tenant_id="test")
# ConnectionError: HTTPSConnectionPool(host='api.somabrain.com', port=443)
```

**Solutions**:
```python
# Solution 1: Use correct base URL
client = SomaBrainClient(
    api_key="test",
    tenant_id="test",
    base_url="http://localhost:9696"  # For local development
)

# Solution 2: Configure timeout and retry
client = SomaBrainClient(
    api_key="test",
    tenant_id="test",
    timeout=30,
    max_retries=3
)

# Solution 3: Handle connection errors
import httpx
try:
    result = await client.remember("test content")
except httpx.ConnectError:
    logger.error("Failed to connect to SomaBrain API")
    # Implement fallback or retry logic
```

### Third-party Service Integration

**Issue: External API failures**

**Symptoms**:
- Intermittent service failures
- Timeout errors with external services

**Solutions**:
```python
# Solution 1: Circuit breaker pattern
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise ServiceUnavailableError("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self.reset()
            return result
        except Exception as e:
            self.record_failure()
            raise

# Solution 2: Implement fallback mechanisms
async def get_embedding_with_fallback(text):
    try:
        return await primary_embedding_service.encode(text)
    except ServiceError:
        logger.warning("Primary service failed, using fallback")
        return await fallback_embedding_service.encode(text)

# Solution 3: Add health checks
async def check_service_health():
    try:
        response = await httpx.get(service_url + "/health", timeout=5)
        return response.status_code == 200
    except:
        return False
```

---

## Monitoring and Debugging

### Logging Issues

**Issue: Missing or incomplete logs**

**Solutions**:
```python
# Solution 1: Configure proper logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('somabrain.log'),
        logging.StreamHandler()
    ]
)

# Solution 2: Add structured logging
import structlog
logger = structlog.get_logger()
logger.info("Memory operation completed",
           memory_id=memory_id,
           tenant_id=tenant_id,
           operation_time=elapsed_time)

# Solution 3: Log correlation IDs
import uuid
request_id = str(uuid.uuid4())
logger = logger.bind(request_id=request_id)
```

### Performance Monitoring

**Issue: Performance degradation detection**

**Solutions**:
```python
# Solution 1: Add performance metrics
import time
from prometheus_client import Histogram, Counter

REQUEST_TIME = Histogram('request_processing_seconds', 'Time spent processing requests')
ERROR_COUNT = Counter('errors_total', 'Total number of errors')

@REQUEST_TIME.time()
async def process_request():
    try:
        # Process request
        pass
    except Exception as e:
        ERROR_COUNT.inc()
        raise

# Solution 2: Health check endpoints
@app.get("/health")
async def health_check():
    checks = {
        "database": await check_database_health(),
        "cache": await check_cache_health(),
        "vector_service": await check_vector_service_health()
    }

    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return {"status": "healthy" if all_healthy else "unhealthy", "checks": checks}

# Solution 3: Alerting integration
async def send_alert_if_needed(metric_name, value, threshold):
    if value > threshold:
        await alert_service.send_alert(
            f"{metric_name} exceeded threshold: {value} > {threshold}"
        )
```

**Verification**: Troubleshooting guide is effective when common issues are quickly resolved using the provided solutions.

---

**Common Errors**:

| Issue | Quick Solution |
|-------|---------------|
| Import errors | Check virtual environment and `pip install -e .` |
| Database connection | Verify PostgreSQL is running and credentials are correct |
| Slow performance | Check indexes, connection pooling, and resource usage |
| Test failures | Ensure test isolation and proper cleanup |
| Docker issues | Check port mapping and environment variables |

**References**:
- [Environment Setup](../environment-setup.md) for initial configuration
- [Useful Links](useful-links.md) for additional resources
- [Setup Checklist](../checklists/setup-checklist.md) for verification steps
- [Glossary](glossary.md) for technical terminology