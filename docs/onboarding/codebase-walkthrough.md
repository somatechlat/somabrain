# Codebase Walkthrough

**Purpose**: Comprehensive tour of the SomaBrain codebase architecture, component relationships, and development patterns to help new developers understand the system quickly.

**Audience**: New developers, agent coders, and contributors joining the SomaBrain project.

**Prerequisites**: Basic understanding of Python, FastAPI, and modern web development. Completed [Local Setup](../development/local-setup.md).

---

## Repository Structure Overview

```
somabrain/
├── somabrain/           # Main application package
│   ├── api/            # FastAPI application and routes
│   ├── core/           # Business logic and cognitive operations
│   ├── database/       # Database models and connections
│   ├── models/         # Pydantic data models
│   ├── services/       # External service integrations
│   └── utils/          # Shared utilities and helpers
├── tests/              # Test suite (unit, integration, e2e)
├── migrations/         # Database schema migrations (Alembic)
├── benchmarks/         # Performance benchmarks and profiling
├── docs/              # Documentation (this manual)
├── scripts/           # Development and deployment scripts
├── config/            # Configuration templates and examples
└── docker/            # Docker configurations and compose files
```

### Key Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Python project configuration, dependencies, build settings |
| `docker-compose.yml` | Local development environment setup |
| `alembic.ini` | Database migration configuration |
| `Makefile` | Common development commands and shortcuts |
| `.github/workflows/` | CI/CD pipeline definitions |

---

## Core Application Architecture

### High-Level System Design

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │   Python SDK    │    │  TypeScript SDK │
│   (Browser)     │    │   (Library)     │    │   (Library)     │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │       FastAPI Server      │
                    │    (Port 9696)           │
                    └─────────────┬─────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
    ┌─────▼─────┐         ┌─────▼─────┐         ┌─────▼─────┐
    │ PostgreSQL│         │   Redis   │         │  Vector   │
    │ Database  │         │   Cache   │         │ Service   │
    │(Port 5432)│         │(Port 6379)│         │ (Qdrant)  │
    └───────────┘         └───────────┘         └───────────┘
```

### Application Layers

**API Layer** (`somabrain/api/`):
- HTTP endpoints and request/response handling
- Authentication and authorization middleware
- Input validation and serialization
- Error handling and logging

**Core Layer** (`somabrain/core/`):
- Business logic implementation
- Cognitive reasoning algorithms
- Memory management operations
- Vector encoding and similarity computation

**Data Layer** (`somabrain/database/`):
- Database models and schemas
- Query optimization and indexes
- Connection pooling and transactions
- Data access patterns

---

## Key Components Deep Dive

### 1. Memory Manager (`somabrain/core/memory_manager.py`)

**Purpose**: Central component for all memory operations - storage, retrieval, and reasoning.

```python
class MemoryManager:
    """
    Core memory operations manager.

    Handles the complete lifecycle of memories:
    - Encoding content to vectors using transformer models
    - Storing memories with metadata in PostgreSQL
    - Performing semantic similarity searches
    - Managing tenant isolation and security
    """

    def __init__(self, config: AppConfig):
        self.config = config
        self.vector_encoder = VectorEncoder(config.model_name)
        self.database = DatabaseManager(config.database_url)
        self.cache = CacheManager(config.redis_url)

    async def store_memory(
        self,
        content: str,
        metadata: dict,
        tenant_id: str
    ) -> str:
        """Store new memory with vector encoding."""

    async def recall_memories(
        self,
        query: str,
        k: int = 10,
        tenant_id: str
    ) -> List[Memory]:
        """Retrieve semantically similar memories."""
```

**Key Methods**:
- `store_memory()`: Encodes and stores new memories
- `recall_memories()`: Semantic similarity search
- `update_memory()`: Updates existing memory content
- `delete_memory()`: Removes memories (with audit trail)
- `analyze_patterns()`: Discovers memory patterns and relationships

### 2. Vector Encoder (`somabrain/core/vector_encoder.py`)

**Purpose**: Converts text content into high-dimensional vector representations for semantic similarity.

```python
class VectorEncoder:
    """
    Handles text-to-vector encoding using transformer models.

    Uses sentence-transformers library with models like:
    - all-MiniLM-L6-v2 (384 dimensions, fast)
    - all-mpnet-base-v2 (768 dimensions, accurate)
    """

    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)
        self.dimensions = self.model.get_sentence_embedding_dimension()

    def encode(self, text: str) -> np.ndarray:
        """Convert text to vector representation."""

    def compute_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between vectors."""
```

**Performance Considerations**:
- Model loading is expensive - singleton pattern used
- Batch encoding for multiple texts
- GPU acceleration when available
- Vector normalization for consistent similarity scores

### 3. Database Layer (`somabrain/database/`)

**Core Models** (`models.py`):
```python
class Memory(Base):
    """
    Main memory storage table.

    Stores content, metadata, vector encodings, and audit information.
    Partitioned by tenant_id for isolation and performance.
    """
    __tablename__ = "memories"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=False)
    vector_encoding = Column(ARRAY(Float), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Indexes for performance
    __table_args__ = (
        Index('ix_memories_tenant_created', 'tenant_id', 'created_at'),
        Index('ix_memories_tenant_metadata', 'tenant_id', 'metadata', postgresql_using='gin'),
    )

class Tenant(Base):
    """Tenant configuration and limits."""
    __tablename__ = "tenants"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    settings = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Database Manager** (`connection.py`):
```python
class DatabaseManager:
    """
    Handles all database operations with connection pooling.

    Features:
    - Async PostgreSQL operations using asyncpg
    - Connection pooling for performance
    - Transaction management
    - Query optimization and explain plans
    """

    async def store_memory(self, memory: Memory) -> str:
        """Store memory with vector in single transaction."""

    async def search_memories(
        self,
        query_vector: np.ndarray,
        tenant_id: str,
        limit: int = 10,
        threshold: float = 0.2
    ) -> List[Memory]:
        """Vector similarity search with pgvector."""
```

### 4. API Layer (`somabrain/api/`)

**Main Application** (`main.py`):
```python
def create_app(config: AppConfig) -> FastAPI:
    """
    FastAPI application factory.

    Sets up:
    - CORS middleware for web clients
    - Authentication middleware
    - Prometheus metrics collection
    - Request/response logging
    - Error handlers
    """
    app = FastAPI(
        title="SomaBrain API",
        description="Cognitive Memory Platform",
        version=__version__
    )

    # Middleware setup
    app.add_middleware(CORSMiddleware, ...)
    app.add_middleware(AuthenticationMiddleware, ...)
    app.add_middleware(PrometheusMiddleware, ...)

    # Router registration
    app.include_router(memory_router, prefix="/api/v1")
    app.include_router(reasoning_router, prefix="/api/v1")
    app.include_router(tenant_router, prefix="/api/v1")

    return app
```

**Route Handlers** (`routers/memory.py`):
```python
@router.post("/remember", response_model=MemoryResponse)
async def store_memory(
    request: MemoryRequest,
    memory_manager: MemoryManager = Depends(get_memory_manager),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Store a new memory.

    1. Validate request content and metadata
    2. Check tenant limits and quotas
    3. Encode content to vector representation
    4. Store in database with audit trail
    5. Return memory ID and metadata
    """

@router.post("/recall", response_model=RecallResponse)
async def recall_memories(
    request: RecallRequest,
    memory_manager: MemoryManager = Depends(get_memory_manager),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Search for semantically similar memories.

    1. Validate query and parameters
    2. Encode query to vector
    3. Perform similarity search in database
    4. Apply metadata filters
    5. Return ranked results with scores
    """
```

---

## Data Flow Patterns

### Memory Storage Flow

```mermaid
graph TD
    A[Client Request] --> B[API Validation]
    B --> C[Authentication Check]
    C --> D[Tenant Validation]
    D --> E[Content Encoding]
    E --> F[Vector Generation]
    F --> G[Database Transaction]
    G --> H[Audit Logging]
    H --> I[Cache Update]
    I --> J[Response Return]
```

**Detailed Steps**:
1. **Request Validation**: Check content length, metadata format
2. **Authentication**: Verify API key and permissions
3. **Tenant Check**: Validate tenant exists and within limits
4. **Content Processing**: Clean and prepare text for encoding
5. **Vector Encoding**: Convert text to numerical representation
6. **Database Storage**: Store in PostgreSQL with ACID guarantees
7. **Audit Trail**: Log operation for compliance and debugging
8. **Cache Operations**: Update Redis cache for performance
9. **Response**: Return memory ID and confirmation

### Memory Recall Flow

```mermaid
graph TD
    A[Search Query] --> B[Query Encoding]
    B --> C[Vector Search]
    C --> D[Similarity Scoring]
    D --> E[Metadata Filtering]
    E --> F[Ranking & Sorting]
    F --> G[Result Formatting]
    G --> H[Response Return]
```

**Performance Optimizations**:
- **Batch Vector Operations**: Process multiple queries together
- **Database Indexing**: pgvector indexes for fast similarity search
- **Result Caching**: Cache frequent queries in Redis
- **Lazy Loading**: Only fetch full content when needed

---

## Configuration Management

### Application Configuration (`somabrain/config.py`)

```python
class AppConfig(BaseSettings):
    """
    Application configuration with environment variable support.

    Supports multiple environments (dev, staging, prod) with
    appropriate defaults and validation.
    """

    # Database
    database_url: str = "postgresql://user:pass@localhost/somabrain"
    database_pool_size: int = 10

    # Vector Service
    vector_model: str = "all-MiniLM-L6-v2"
    vector_dimensions: int = 384

    # Redis Cache
    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 3600

    # API Settings
    api_key_header: str = "X-API-Key"
    tenant_id_header: str = "X-Tenant-ID"
    rate_limit_requests: int = 1000
    rate_limit_window: int = 60

    # Monitoring
    prometheus_metrics: bool = True
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_prefix = "SOMABRAIN_"
```

### Environment-Specific Configs

**Development** (`.env.development`):
```bash
SOMABRAIN_DATABASE_URL=postgresql://dev:dev@localhost/somabrain_dev
SOMABRAIN_LOG_LEVEL=DEBUG
SOMABRAIN_PROMETHEUS_METRICS=false
```

**Production** (`.env.production`):
```bash
SOMABRAIN_DATABASE_URL=postgresql://prod_user:${DB_PASSWORD}@db.prod/somabrain
SOMABRAIN_LOG_LEVEL=WARNING
SOMABRAIN_PROMETHEUS_METRICS=true
```

---

## Testing Architecture

### Test Structure

```
tests/
├── unit/               # Fast, isolated component tests
│   ├── core/          # Memory manager, encoding logic
│   ├── api/           # Route handlers, validation
│   ├── database/      # Model tests, query logic
│   └── utils/         # Helper function tests
├── integration/        # Component interaction tests
│   ├── api/           # End-to-end API workflows
│   ├── database/      # Database integration patterns
│   └── services/      # External service integration/adapters
├── e2e/               # Full system tests
│   ├── user_workflows/ # Complete user scenarios
│   ├── performance/   # Load and stress testing
│   └── deployment/    # Docker and infrastructure tests
└── fixtures/          # Shared test data and utilities
```

### Test Patterns

**Unit Test Example**:
```python
# tests/unit/core/test_memory_manager.py
@pytest.mark.asyncio
async def test_store_memory_success():
    """Test successful memory storage with all components mocked."""

    # Arrange - Mock all dependencies
    mock_encoder = Mock()
    mock_encoder.encode.return_value = np.array([1, 2, 3])

    mock_db = AsyncMock()
    mock_db.store_memory.return_value = "mem_123"

    manager = MemoryManager(encoder=mock_encoder, database=mock_db)

    # Act - Call method under test
    result = await manager.store_memory(
        content="Test content",
        metadata={"category": "test"},
        tenant_id="test_tenant"
    )

    # Assert - Verify behavior
    assert result == "mem_123"
    mock_encoder.encode.assert_called_once_with("Test content")
    mock_db.store_memory.assert_called_once()
```

**Integration Test Example**:
```python
# tests/integration/api/test_memory_endpoints.py
@pytest.mark.asyncio
async def test_store_and_recall_workflow():
    """Test complete memory storage and retrieval via API."""

    # Uses real database, real encoder, but isolated test tenant
    async with AsyncClient(app=app, base_url="http://test") as client:

        # Store memory
        store_response = await client.post("/remember", json={
            "content": "Integration test content",
            "metadata": {"type": "integration_test"}
        }, headers={"X-Tenant-ID": "test_tenant"})

        memory_id = store_response.json()["memory_id"]

        # Recall memory
        recall_response = await client.post("/recall", json={
            "query": "integration test",
            "k": 5
        }, headers={"X-Tenant-ID": "test_tenant"})

        results = recall_response.json()["results"]

        # Verify end-to-end workflow
        assert len(results) > 0
        assert any(r["memory_id"] == memory_id for r in results)
```

---

## Development Patterns

### Dependency Injection

**FastAPI Dependencies**:
```python
# somabrain/api/dependencies.py
async def get_database_manager() -> DatabaseManager:
    """Provide database manager instance."""
    return database_manager_instance

async def get_memory_manager(
    db: DatabaseManager = Depends(get_database_manager)
) -> MemoryManager:
    """Provide memory manager with injected dependencies."""
    return MemoryManager(database=db, encoder=vector_encoder)

async def get_current_tenant(
    request: Request,
    api_key: str = Header(..., alias="X-API-Key")
) -> str:
    """Extract and validate tenant from headers."""
    tenant_id = request.headers.get("X-Tenant-ID")
    if not tenant_id:
        raise HTTPException(400, "Missing tenant ID")
    return tenant_id
```

### Error Handling Patterns

**Custom Exception Hierarchy**:
```python
# somabrain/exceptions.py
class SomaBrainError(Exception):
    """Base exception for all SomaBrain errors."""
    pass

class ValidationError(SomaBrainError):
    """Request validation errors."""
    pass

class AuthenticationError(SomaBrainError):
    """Authentication and authorization errors."""
    pass

class MemoryNotFoundError(SomaBrainError):
    """Memory lookup errors."""
    pass

class EncodingError(SomaBrainError):
    """Vector encoding failures."""
    pass
```

**Error Handler Middleware**:
```python
@app.exception_handler(SomaBrainError)
async def somabrain_exception_handler(request: Request, exc: SomaBrainError):
    """Convert application errors to proper HTTP responses."""

    error_mapping = {
        ValidationError: 400,
        AuthenticationError: 401,
        MemoryNotFoundError: 404,
        EncodingError: 500
    }

    status_code = error_mapping.get(type(exc), 500)

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "type": exc.__class__.__name__,
                "message": str(exc),
                "request_id": request.state.request_id
            }
        }
    )
```

### Async Patterns

**Database Operations**:
```python
async def process_batch_memories(memories: List[Dict]) -> List[str]:
    """Process multiple memories concurrently."""

    async def process_single_memory(memory_data):
        async with database.transaction():
            # Encode vector
            vector = await encoder.encode(memory_data["content"])

            # Store in database
            memory_id = await database.store_memory(
                content=memory_data["content"],
                metadata=memory_data["metadata"],
                vector=vector
            )

            return memory_id

    # Process all memories concurrently
    tasks = [process_single_memory(mem) for mem in memories]
    return await asyncio.gather(*tasks)
```

---

## Performance Patterns

### Caching Strategy

**Multi-Level Caching**:
```python
class CacheManager:
    """
    Multi-level caching for performance optimization.

    L1: In-memory LRU cache for frequent vectors
    L2: Redis cache for computed results
    L3: Database with optimized indexes
    """

    def __init__(self):
        self.memory_cache = LRUCache(maxsize=1000)  # L1
        self.redis_client = Redis()                  # L2

    async def get_similar_memories(self, query_vector, tenant_id):
        # L1: Check in-memory cache
        cache_key = f"similar:{tenant_id}:{hash(query_vector.tobytes())}"

        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]

        # L2: Check Redis cache
        cached_result = await self.redis_client.get(cache_key)
        if cached_result:
            result = json.loads(cached_result)
            self.memory_cache[cache_key] = result
            return result

        # L3: Database query
        result = await self.database.search_memories(query_vector, tenant_id)

        # Populate caches
        await self.redis_client.setex(cache_key, 3600, json.dumps(result))
        self.memory_cache[cache_key] = result

        return result
```

### Database Optimization

**Query Patterns**:
```sql
-- Optimized similarity search with pgvector
SELECT
    id, content, metadata,
    1 - (vector_encoding <=> %s) AS similarity_score
FROM memories
WHERE
    tenant_id = %s
    AND 1 - (vector_encoding <=> %s) > %s  -- threshold filter
ORDER BY vector_encoding <=> %s  -- pgvector distance operator
LIMIT %s;

-- Metadata filtering with GIN indexes
SELECT id, content
FROM memories
WHERE
    tenant_id = %s
    AND metadata @> %s  -- JSON contains operator
ORDER BY created_at DESC;
```

**Connection Pooling**:
```python
class DatabasePool:
    """Connection pool for high-concurrency database access."""

    def __init__(self, database_url: str, pool_size: int = 20):
        self.pool = asyncpg.create_pool(
            database_url,
            min_size=5,
            max_size=pool_size,
            command_timeout=30
        )

    async def execute_query(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
```

**Verification**: Codebase understanding is complete when you can navigate the architecture, understand component relationships, and identify where to make changes for new features.

---

**Common Errors**:

| Issue | Solution |
|-------|----------|
| Import errors | Check PYTHONPATH and virtual environment |
| Database connection fails | Verify PostgreSQL is running and accessible |
| Vector encoding slow | Use GPU acceleration or smaller models |
| Tests fail intermittently | Check for async race conditions and proper cleanup |

**References**:
- [Local Setup](../development/local-setup.md) for development configuration
- [Domain Knowledge](domain-knowledge.md) for deep technical understanding
- [First Contribution](first-contribution.md) for hands-on practice
- [Development Manual](../development/index.md) for detailed technical guides