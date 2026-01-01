# Coding Standards

**Purpose**: Define coding standards, style guidelines, and best practices for SomaBrain development to ensure consistent, maintainable, and secure code.

**Audience**: Software developers, code reviewers, and technical contributors to SomaBrain.

**Prerequisites**: Familiarity with [Local Setup](local-setup.md) and development environment.

---

## General Principles

### Code Quality Standards

**Readability**: Code should be self-documenting with clear variable names and logical structure
**Maintainability**: Write code that can be easily modified and extended by other developers
**Performance**: Optimize for both development speed and runtime efficiency
**Security**: Follow secure coding practices to prevent vulnerabilities
**Testability**: Design code to be easily unit tested and integration tested

### Development Workflow

**Feature Branches**: Use feature branches for all development work
**Code Reviews**: All code changes require peer review before merging
**Testing**: Write tests alongside code development (TDD encouraged)
**Documentation**: Update documentation for user-facing changes
**Incremental Commits**: Make small, logical commits with clear messages

---

## Python Coding Standards

### Code Style and Formatting

SomaBrain follows **PEP 8** with specific modifications for cognitive memory systems:

```python
# pyproject.toml - Code formatting configuration
[tool.black]
line-length = 100
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  migrations
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | _build
  | buck-out
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true

[tool.flake8]
max-line-length = 100
extend-ignore = ["E203", "W503"]
exclude = [".git", "__pycache__", "migrations", ".venv"]
max-complexity = 10
```

**Formatting Tools**:
```bash
# Format code with black
black somabrain/ tests/

# Sort imports with isort
isort somabrain/ tests/

# Check style with flake8
flake8 somabrain/ tests/

# Type checking with mypy
mypy somabrain/
```

### Naming Conventions

```python
# Module and package names (lowercase with underscores)
import memory_operations
from cognitive_reasoning import inference_engine

# Class names (PascalCase)
class MemoryManager:
    """Manages cognitive memory storage and retrieval."""
    pass

class VectorEncoder:
    """Encodes content into high-dimensional vectors."""
    pass

# Function and variable names (snake_case)
def encode_memory_content(content: str, metadata: dict) -> np.ndarray:
    """Encode content into vector representation."""
    similarity_threshold = 0.3
    encoded_vector = _compute_embedding(content)
    return encoded_vector

# Constants (UPPER_CASE)
DEFAULT_VECTOR_DIMENSIONS = 1024
MAX_MEMORY_CONTENT_LENGTH = 10240
SIMILARITY_COMPUTATION_TIMEOUT = 30.0

# Private methods and variables (leading underscore)
def _compute_embedding(content: str) -> np.ndarray:
    """Private method for embedding computation."""
    pass

_internal_cache = {}

# Class attributes and methods
class CognitiveReasoner:
    def __init__(self, config: ReasoningConfig):
        self.config = config
        self._reasoning_cache = {}

    def reason_about_query(self, query: str) -> ReasoningResult:
        """Public method for cognitive reasoning."""
        pass

    def _build_reasoning_chain(self, context: List[Memory]) -> ReasoningChain:
        """Private method for building reasoning chains."""
        pass
```

### Type Hints and Documentation

Use comprehensive type hints and docstrings:

```python
from typing import List, Dict, Optional, Union, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import numpy as np

@dataclass
class Memory:
    """Represents a cognitive memory with content and metadata."""
    id: str
    content: str
    metadata: Dict[str, Any]
    vector_encoding: np.ndarray
    created_at: datetime
    tenant_id: str
    similarity_score: Optional[float] = None

class MemoryManager:
    """
    Manages cognitive memory operations including storage, retrieval, and reasoning.

    This class provides the core functionality for SomaBrain's memory system,
    handling vector encoding, similarity computation, and contextual retrieval.

    Attributes:
        vector_dimensions: Dimensionality of vector encodings (default: 1024)
        similarity_threshold: Minimum similarity score for retrieval (default: 0.2)
        encoding_model: Name of the sentence transformer model

    Example:
        >>> manager = MemoryManager(vector_dimensions=1024)
        >>> memory_id = manager.store_memory("Python is great", {"topic": "programming"})
        >>> results = manager.recall_memories("programming languages", k=5)
    """

    def __init__(
        self,
        vector_dimensions: int = 1024,
        similarity_threshold: float = 0.2,
        encoding_model: str = "all-MiniLM-L6-v2"
    ) -> None:
        """
        Initialize the memory manager with specified configuration.

        Args:
            vector_dimensions: Number of dimensions for vector encodings
            similarity_threshold: Minimum similarity score for retrieval
            encoding_model: Sentence transformer model name

        Raises:
            ValueError: If vector_dimensions is not positive
            ModelNotFoundError: If encoding_model cannot be loaded
        """
        if vector_dimensions <= 0:
            raise ValueError("vector_dimensions must be positive")

        self.vector_dimensions = vector_dimensions
        self.similarity_threshold = similarity_threshold
        self.encoding_model = encoding_model
        self._encoder = self._load_encoder()

    def store_memory(
        self,
        content: str,
        metadata: Dict[str, Any],
        tenant_id: str
    ) -> str:
        """
        Store a new memory with content and metadata.

        Args:
            content: The textual content of the memory
            metadata: Associated metadata as key-value pairs
            tenant_id: Tenant identifier for isolation

        Returns:
            Unique identifier for the stored memory

        Raises:
            ValueError: If content is empty or too long
            TenantNotFoundError: If tenant_id is invalid

        Example:
            >>> memory_id = manager.store_memory(
            ...     "FastAPI is a modern Python web framework",
            ...     {"category": "technical", "language": "python"},
            ...     "tenant_123"
            ... )
        """
        # Implementation here
        pass

    def recall_memories(
        self,
        query: str,
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None
    ) -> List[Memory]:
        """
        Retrieve memories similar to the query.

        Args:
            query: Search query as natural language
            k: Maximum number of memories to return
            filters: Optional metadata filters
            tenant_id: Tenant scope for search

        Returns:
            List of memories ranked by similarity score

        Raises:
            ValueError: If k is not positive
            InvalidQueryError: If query cannot be processed
        """
        # Implementation here
        pass
```

### Error Handling and Logging

Implement comprehensive error handling:

```python
import logging
from enum import Enum
from typing import Optional
from dataclasses import dataclass

class SomaBrainErrorCode(Enum):
    """Standardized error codes for SomaBrain operations."""
    MEMORY_NOT_FOUND = "MEMORY_001"
    ENCODING_FAILED = "MEMORY_002"
    SIMILARITY_TIMEOUT = "MEMORY_003"
    TENANT_ISOLATION_VIOLATION = "SECURITY_001"
    RATE_LIMIT_EXCEEDED = "API_001"
    INVALID_CONTENT_FORMAT = "VALIDATION_001"

@dataclass
class SomaBrainError(Exception):
    """Base exception class for SomaBrain operations."""
    error_code: SomaBrainErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        return f"{self.error_code.value}: {self.message}"

class MemoryNotFoundError(SomaBrainError):
    """Raised when requested memory cannot be found."""
    pass

class EncodingError(SomaBrainError):
    """Raised when vector encoding fails."""
    pass

# Set up structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('somabrain.log')
    ]
)

logger = logging.getLogger(__name__)

def store_memory_with_error_handling(content: str, metadata: Dict[str, Any]) -> str:
    """Example of proper error handling and logging."""

    logger.info(f"Storing memory with content length: {len(content)}")

    try:
        # Validate input
        if not content or len(content.strip()) == 0:
            raise SomaBrainError(
                error_code=SomaBrainErrorCode.INVALID_CONTENT_FORMAT,
                message="Memory content cannot be empty",
                details={"content_length": len(content)}
            )

        # Attempt encoding
        try:
            vector_encoding = encode_content(content)
        except Exception as e:
            logger.error(f"Vector encoding failed: {e}")
            raise EncodingError(
                error_code=SomaBrainErrorCode.ENCODING_FAILED,
                message=f"Failed to encode content: {str(e)}",
                details={"original_error": str(e), "content_sample": content[:100]}
            )

        # Store in database
        memory_id = _store_in_database(content, metadata, vector_encoding)

        logger.info(f"Successfully stored memory: {memory_id}")
        return memory_id

    except SomaBrainError:
        # Re-raise SomaBrain specific errors
        raise
    except Exception as e:
        # Catch and wrap unexpected errors
        logger.error(f"Unexpected error in store_memory: {e}", exc_info=True)
        raise SomaBrainError(
            error_code=SomaBrainErrorCode.ENCODING_FAILED,
            message="Unexpected error during memory storage",
            details={"original_error": str(e)}
        )
```

### Performance Optimization Guidelines

```python
import asyncio
import time
from functools import lru_cache, wraps
from typing import Callable, Any
import numpy as np
from concurrent.futures import ThreadPoolExecutor

# Use caching for expensive operations
@lru_cache(maxsize=1000)
def compute_similarity_cached(vector1_hash: str, vector2_hash: str) -> float:
    """Cache similarity computations for repeated queries."""
    # Reconstruct vectors from hashes (implementation specific)
    vector1 = reconstruct_vector(vector1_hash)
    vector2 = reconstruct_vector(vector2_hash)
    return np.dot(vector1, vector2) / (np.linalg.norm(vector1) * np.linalg.norm(vector2))

# Use async for I/O bound operations
async def encode_memories_batch(contents: List[str]) -> List[np.ndarray]:
    """Encode multiple memories concurrently."""

    async def encode_single(content: str) -> np.ndarray:
        # Use thread pool for CPU-intensive encoding
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(executor, encode_content, content)

    # Process in batches to avoid overwhelming resources
    batch_size = 50
    results = []

    for i in range(0, len(contents), batch_size):
        batch = contents[i:i + batch_size]
        batch_results = await asyncio.gather(*[encode_single(content) for content in batch])
        results.extend(batch_results)

    return results

# Optimize database queries
def recall_memories_optimized(
    query: str,
    k: int = 10,
    tenant_id: str = None
) -> List[Memory]:
    """Optimized memory recall with query planning."""

    # Use query vector encoding
    query_vector = encode_content(query)

    # Optimize similarity search with approximate methods for large datasets
    if get_memory_count(tenant_id) > 100000:
        # Use FAISS for approximate similarity search
        similar_indices = faiss_index.search(query_vector, k * 2)  # Get more candidates
        candidate_memories = [get_memory_by_index(idx) for idx in similar_indices]
    else:
        # Use exact search for smaller datasets
        candidate_memories = get_all_memories(tenant_id)

    # Compute exact similarities for candidates
    similarities = []
    for memory in candidate_memories:
        similarity = compute_similarity(query_vector, memory.vector_encoding)
        if similarity >= similarity_threshold:
            similarities.append((memory, similarity))

    # Sort and return top k
    similarities.sort(key=lambda x: x[1], reverse=True)
    return [mem for mem, score in similarities[:k]]

# Performance monitoring decorator
def monitor_performance(func: Callable) -> Callable:
    """Decorator to monitor function performance."""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            # Log performance metrics
            logger.info(f"{func.__name__} executed in {execution_time:.3f}s")

            # Send metrics to monitoring system
            metrics.histogram(f"somabrain.{func.__name__}.duration", execution_time)

            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    return wrapper

# Use for critical operations
@monitor_performance
def store_memory(content: str, metadata: Dict[str, Any]) -> str:
    # Implementation here
    pass
```

---

## JavaScript/TypeScript Standards

### Code Style Configuration

```typescript
// .eslintrc.js - ESLint configuration
module.exports = {
  extends: [
    '@typescript-eslint/recommended',
    'prettier/@typescript-eslint',
    'plugin:prettier/recommended'
  ],
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module',
    project: './tsconfig.json'
  },
  rules: {
    '@typescript-eslint/explicit-function-return-type': 'error',
    '@typescript-eslint/no-explicit-any': 'warn',
    '@typescript-eslint/no-unused-vars': 'error',
    '@typescript-eslint/prefer-const': 'error',
    'prefer-const': 'error',
    'no-var': 'error',
    'camelcase': 'error'
  },
  ignorePatterns: ['dist/', 'node_modules/', '*.js']
};

// prettier.config.js - Prettier configuration
module.exports = {
  semi: true,
  singleQuote: true,
  tabWidth: 2,
  trailingComma: 'es5',
  printWidth: 100,
  bracketSpacing: true,
  arrowParens: 'avoid'
};

// tsconfig.json - TypeScript configuration
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "lib": ["ES2022", "DOM"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "exactOptionalPropertyTypes": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "**/*.test.ts"]
}
```

### TypeScript Coding Guidelines

```typescript
// types/somabrain.d.ts - Type definitions
export interface Memory {
  readonly id: string;
  content: string;
  metadata: Record<string, unknown>;
  vectorEncoding?: number[];
  createdAt: Date;
  tenantId: string;
  similarityScore?: number;
}

export interface MemoryMetadata {
  category?: string;
  topic?: string;
  confidence?: number;
  tags?: string[];
  [key: string]: unknown;
}

export interface RecallOptions {
  k?: number;
  threshold?: number;
  filters?: Record<string, unknown>;
  includeScores?: boolean;
}

export interface RecallResult {
  memories: Memory[];
  totalCount: number;
  queryTime: number;
}

// Enum for error types
export enum SomaBrainErrorType {
  MEMORY_NOT_FOUND = 'MEMORY_NOT_FOUND',
  ENCODING_FAILED = 'ENCODING_FAILED',
  RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED',
  UNAUTHORIZED = 'UNAUTHORIZED',
  VALIDATION_ERROR = 'VALIDATION_ERROR'
}

// Custom error class
export class SomaBrainError extends Error {
  constructor(
    public readonly errorType: SomaBrainErrorType,
    message: string,
    public readonly details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'SomaBrainError';
  }
}

// Client implementation with proper typing
export class SomaBrainClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;
  private readonly tenantId: string;
  private readonly timeout: number;

  constructor(config: {
    baseUrl: string;
    apiKey: string;
    tenantId: string;
    timeout?: number;
  }) {
    this.baseUrl = config.baseUrl.replace(/\/$/, ''); // Remove trailing slash
    this.apiKey = config.apiKey;
    this.tenantId = config.tenantId;
    this.timeout = config.timeout ?? 30000;
  }

  /**
   * Store a new memory with content and metadata.
   */
  async remember(
    content: string,
    metadata: MemoryMetadata = {}
  ): Promise<string> {
    if (!content.trim()) {
      throw new SomaBrainError(
        SomaBrainErrorType.VALIDATION_ERROR,
        'Memory content cannot be empty'
      );
    }

    try {
      const response = await this.makeRequest<{ memory_id: string }>('POST', '/remember', {
        content,
        metadata
      });

      return response.memory_id;
    } catch (error) {
      this.handleError(error);
      throw error; // TypeScript requires this for type safety
    }
  }

  /**
   * Recall memories similar to the query.
   */
  async recall(
    query: string,
    options: RecallOptions = {}
  ): Promise<RecallResult> {
    const {
      k = 10,
      threshold = 0.2,
      filters = {},
      includeScores = true
    } = options;

    try {
      const response = await this.makeRequest<{
        results: Array<{
          memory_id: string;
          content: string;
          score: number;
          metadata: Record<string, unknown>;
        }>;
        query_time_ms: number;
      }>('POST', '/recall', {
        query,
        k,
        threshold,
        filters,
        include_scores: includeScores
      });

      const memories: Memory[] = response.results.map(result => ({
        id: result.memory_id,
        content: result.content,
        metadata: result.metadata,
        createdAt: new Date(), // Would be parsed from API response
        tenantId: this.tenantId,
        similarityScore: result.score
      }));

      return {
        memories,
        totalCount: memories.length,
        queryTime: response.query_time_ms
      };
    } catch (error) {
      this.handleError(error);
      throw error;
    }
  }

  /**
   * Make HTTP request with proper error handling.
   */
  private async makeRequest<T>(
    method: string,
    endpoint: string,
    data?: unknown
  ): Promise<T> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': this.apiKey,
          'X-Tenant-ID': this.tenantId
        },
        body: data ? JSON.stringify(data) : undefined,
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new SomaBrainError(
          this.mapHttpStatusToErrorType(response.status),
          `HTTP ${response.status}: ${response.statusText}`,
          { status: response.status, statusText: response.statusText }
        );
      }

      return await response.json() as T;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new SomaBrainError(
          SomaBrainErrorType.RATE_LIMIT_EXCEEDED,
          'Request timeout'
        );
      }
      throw error;
    }
  }

  private mapHttpStatusToErrorType(status: number): SomaBrainErrorType {
    switch (status) {
      case 401:
      case 403:
        return SomaBrainErrorType.UNAUTHORIZED;
      case 404:
        return SomaBrainErrorType.MEMORY_NOT_FOUND;
      case 429:
        return SomaBrainErrorType.RATE_LIMIT_EXCEEDED;
      case 400:
        return SomaBrainErrorType.VALIDATION_ERROR;
      default:
        return SomaBrainErrorType.ENCODING_FAILED; // Generic error
    }
  }

  private handleError(error: unknown): void {
    if (error instanceof SomaBrainError) {
      // Log structured error information
      console.error('SomaBrain API Error:', {
        type: error.errorType,
        message: error.message,
        details: error.details
      });
    } else {
      console.error('Unexpected error:', error);
    }
  }
}
```

---

## Database Schema Standards

### PostgreSQL Schema Guidelines

```sql
-- database/schemas/memory_schema.sql
-- Follow consistent naming conventions and documentation

-- Table naming: snake_case, plural nouns
-- Column naming: snake_case, descriptive names
-- Constraints: descriptive names with prefixes (pk_, fk_, ck_, uk_)
-- Indexes: descriptive names with idx_ prefix

-- Memories table with comprehensive documentation
CREATE TABLE memories (
    -- Primary key: UUIDs for distributed systems
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Core memory content
    content TEXT NOT NULL
        CONSTRAINT ck_memories_content_not_empty
        CHECK (length(trim(content)) > 0),

    -- Metadata as JSONB for flexibility and indexing
    metadata JSONB NOT NULL DEFAULT '{}',

    -- Vector encoding stored as binary
    vector_encoding BYTEA,

    -- Tenant isolation (required for all tables)
    tenant_id VARCHAR(255) NOT NULL,

    -- Timestamps with timezone
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Content length for optimization
    content_length INTEGER GENERATED ALWAYS AS (length(content)) STORED,

    -- Soft delete support
    deleted_at TIMESTAMPTZ NULL
);

-- Indexes for performance
CREATE INDEX idx_memories_tenant_id ON memories (tenant_id)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_memories_created_at ON memories (created_at DESC)
    WHERE deleted_at IS NULL;

-- GIN index for metadata queries
CREATE INDEX idx_memories_metadata ON memories USING GIN (metadata)
    WHERE deleted_at IS NULL;

-- Composite index for common queries
CREATE INDEX idx_memories_tenant_created ON memories (tenant_id, created_at DESC)
    WHERE deleted_at IS NULL;

-- Constraints and foreign keys
ALTER TABLE memories
    ADD CONSTRAINT fk_memories_tenant_id
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    ON DELETE CASCADE;

-- Row Level Security (RLS) for tenant isolation
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;

CREATE POLICY memories_tenant_isolation ON memories
    FOR ALL TO application_role
    USING (tenant_id = current_setting('app.current_tenant_id'));

-- Comments for documentation
COMMENT ON TABLE memories IS
    'Stores cognitive memories with content, metadata, and vector encodings';
COMMENT ON COLUMN memories.content IS
    'Textual content of the memory, limited to 1MB';
COMMENT ON COLUMN memories.metadata IS
    'Flexible metadata as JSONB with category, topic, tags, etc.';
COMMENT ON COLUMN memories.vector_encoding IS
    'High-dimensional vector encoding for similarity search';

-- Trigger for updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_memories_updated_at
    BEFORE UPDATE ON memories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### Migration Standards

```python
# migrations/001_create_memories_table.py
"""
Create memories table with vector support

Migration: 001
Created: 2025-10-15
Author: SomaBrain Team
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    """Apply migration changes."""

    # Create memories table
    op.create_table(
        'memories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                 server_default=sa.text('gen_random_uuid()')),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()),
                 nullable=False, server_default='{}'),
        sa.Column('vector_encoding', sa.LargeBinary(), nullable=True),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                 nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True),
                 nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),

        # Constraints
        sa.CheckConstraint('length(trim(content)) > 0', name='ck_memories_content_not_empty'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'],
                               name='fk_memories_tenant_id', ondelete='CASCADE')
    )

    # Create indexes
    op.create_index('idx_memories_tenant_id', 'memories', ['tenant_id'],
                   postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_memories_created_at', 'memories', [sa.desc('created_at')],
                   postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_memories_metadata', 'memories', ['metadata'],
                   postgresql_using='gin',
                   postgresql_where=sa.text('deleted_at IS NULL'))

    # Enable Row Level Security
    op.execute('ALTER TABLE memories ENABLE ROW LEVEL SECURITY')

    # Create RLS policy
    op.execute("""
        CREATE POLICY memories_tenant_isolation ON memories
        FOR ALL TO application_role
        USING (tenant_id = current_setting('app.current_tenant_id'))
    """)

    # Create updated_at trigger function if not exists
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql'
    """)

    # Create trigger
    op.execute("""
        CREATE TRIGGER trigger_memories_updated_at
        BEFORE UPDATE ON memories
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)

def downgrade():
    """Revert migration changes."""

    # Drop trigger and function
    op.execute('DROP TRIGGER IF EXISTS trigger_memories_updated_at ON memories')
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column()')

    # Drop RLS policy
    op.execute('DROP POLICY IF EXISTS memories_tenant_isolation ON memories')

    # Drop table (cascades indexes and constraints)
    op.drop_table('memories')
```

---

## Code Review Guidelines

### Review Checklist

```markdown
## Code Review Checklist

### Functionality
- [ ] Code implements requirements correctly
- [ ] Edge cases are handled appropriately
- [ ] Error conditions are properly managed
- [ ] Performance considerations are addressed
- [ ] Security implications are considered

### Code Quality
- [ ] Code follows established style guidelines
- [ ] Variable and function names are descriptive
- [ ] Code is properly commented and documented
- [ ] No duplicate code or logic
- [ ] Appropriate abstractions are used

### Testing
- [ ] Unit tests cover new functionality
- [ ] Integration tests verify end-to-end behavior
- [ ] Test cases include edge cases and error conditions
- [ ] Mock objects are used appropriately
- [ ] Tests are deterministic and reliable

### Security
- [ ] Input validation is implemented
- [ ] SQL injection prevention measures
- [ ] Authentication and authorization checks
- [ ] Sensitive data is not logged or exposed
- [ ] Rate limiting and DoS protection

### Database Changes
- [ ] Migrations are reversible
- [ ] Indexes are added for query performance
- [ ] Row Level Security policies are applied
- [ ] Foreign key constraints maintain referential integrity
- [ ] Backup considerations are documented
```

### Review Process

1. **Self-Review**: Author reviews own code before requesting review
2. **Automated Checks**: CI/CD pipeline runs tests and quality checks
3. **Peer Review**: At least one team member reviews the changes
4. **Security Review**: Security-sensitive changes require security team review
5. **Approval**: Code requires approval before merging to main branch

**Verification**: Coding standards are properly implemented when code is consistent, readable, well-tested, and follows security best practices.

---

**Common Errors**: See [FAQ](../user/faq.md) for development troubleshooting.

**References**:
- [Local Setup Guide](local-setup.md) for development environment
- [Testing Guidelines](testing-guidelines.md) for testing standards
- [API Reference](api-reference.md) for API development
- [Contribution Process](contribution-process.md) for development workflow