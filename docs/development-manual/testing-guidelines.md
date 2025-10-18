# Testing Guidelines

**Purpose**: Comprehensive testing standards and practices for SomaBrain development, covering unit testing, integration testing, and quality assurance.

**Audience**: Software developers, QA engineers, and DevOps teams working on SomaBrain testing infrastructure.

**Prerequisites**: Understanding of [Coding Standards](coding-standards.md) and [Local Setup](local-setup.md).

---

## Testing Philosophy

### Testing Principles

**Test-Driven Development (TDD)**: Write tests before implementation code where practical
**Comprehensive Coverage**: Aim for high test coverage while focusing on critical paths
**Fast Feedback**: Tests should run quickly to enable rapid development iteration
**Deterministic**: Tests must produce consistent results across environments
**Maintainable**: Test code should follow the same quality standards as production code

### Testing Pyramid

```
    E2E Tests (Few)
    ================
   Integration Tests (Some) 
   ========================
  Unit Tests (Many)
  ====================
```

**Unit Tests (70%)**: Fast, isolated tests for individual functions and classes
**Integration Tests (20%)**: Test interactions between components and services
**End-to-End Tests (10%)**: Full system tests simulating user workflows

---

## Unit Testing Standards

### Python Unit Testing with pytest

```python
# tests/conftest.py - Shared test configuration
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from typing import Generator, AsyncGenerator
import numpy as np

from somabrain.core.memory_manager import MemoryManager
from somabrain.models.memory import Memory, MemoryMetadata
from somabrain.database.connection import DatabaseManager
from somabrain.config import TestConfig

# Pytest configuration
def pytest_configure(config):
    """Configure pytest settings."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test") 
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_config() -> TestConfig:
    """Provide test configuration."""
    return TestConfig(
        database_url="sqlite:///:memory:",
        redis_url="redis://localhost:6379/1",
        vector_dimensions=384,  # Smaller for faster tests
        similarity_threshold=0.3
    )

@pytest.fixture
def mock_memory() -> Memory:
    """Create a mock memory for testing."""
    return Memory(
        id="test_memory_001",
        content="This is test content for unit testing",
        metadata=MemoryMetadata(
            category="test",
            topic="unit_testing",
            confidence=0.9,
            tags=["test", "mock"]
        ),
        vector_encoding=np.random.rand(384).astype(np.float32),
        created_at=datetime.now(),
        tenant_id="test_tenant"
    )

@pytest.fixture
def memory_manager(test_config: TestConfig) -> MemoryManager:
    """Create MemoryManager instance for testing."""
    return MemoryManager(
        config=test_config,
        database_manager=Mock(spec=DatabaseManager),
        vector_encoder=Mock()
    )

# Example unit tests
# tests/unit/test_memory_manager.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
import numpy as np
from datetime import datetime

from somabrain.core.memory_manager import MemoryManager
from somabrain.models.memory import Memory, MemoryMetadata
from somabrain.exceptions import MemoryNotFoundError, EncodingError

@pytest.mark.unit
class TestMemoryManager:
    """Unit tests for MemoryManager class."""

    def test_init_with_valid_config(self, test_config):
        """Test MemoryManager initialization with valid configuration."""
        manager = MemoryManager(config=test_config)
        
        assert manager.vector_dimensions == test_config.vector_dimensions
        assert manager.similarity_threshold == test_config.similarity_threshold
        assert manager.config == test_config

    def test_init_with_invalid_dimensions(self, test_config):
        """Test MemoryManager initialization fails with invalid dimensions."""
        test_config.vector_dimensions = -1
        
        with pytest.raises(ValueError, match="vector_dimensions must be positive"):
            MemoryManager(config=test_config)

    @pytest.mark.asyncio
    async def test_store_memory_success(self, memory_manager, mock_memory):
        """Test successful memory storage."""
        # Arrange
        expected_id = "generated_id_123"
        memory_manager.database_manager.store_memory = AsyncMock(return_value=expected_id)
        memory_manager.vector_encoder.encode = Mock(return_value=mock_memory.vector_encoding)
        
        # Act
        result = await memory_manager.store_memory(
            content=mock_memory.content,
            metadata=mock_memory.metadata.dict(),
            tenant_id=mock_memory.tenant_id
        )
        
        # Assert
        assert result == expected_id
        memory_manager.vector_encoder.encode.assert_called_once_with(mock_memory.content)
        memory_manager.database_manager.store_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_memory_empty_content(self, memory_manager):
        """Test memory storage fails with empty content."""
        with pytest.raises(ValueError, match="Memory content cannot be empty"):
            await memory_manager.store_memory(
                content="",
                metadata={},
                tenant_id="test_tenant"
            )

    @pytest.mark.asyncio
    async def test_store_memory_encoding_failure(self, memory_manager):
        """Test memory storage handles encoding failures."""
        # Arrange
        memory_manager.vector_encoder.encode = Mock(
            side_effect=Exception("Encoding model not available")
        )
        
        # Act & Assert
        with pytest.raises(EncodingError, match="Failed to encode content"):
            await memory_manager.store_memory(
                content="Test content",
                metadata={},
                tenant_id="test_tenant"
            )

    @pytest.mark.asyncio
    async def test_recall_memories_success(self, memory_manager, mock_memory):
        """Test successful memory recall."""
        # Arrange
        expected_memories = [mock_memory]
        memory_manager.database_manager.search_memories = AsyncMock(
            return_value=expected_memories
        )
        memory_manager.vector_encoder.encode = Mock(
            return_value=np.random.rand(384).astype(np.float32)
        )
        
        # Act
        results = await memory_manager.recall_memories(
            query="test query",
            k=5,
            tenant_id="test_tenant"
        )
        
        # Assert
        assert len(results) == 1
        assert results[0].id == mock_memory.id
        memory_manager.vector_encoder.encode.assert_called_once_with("test query")

    @pytest.mark.asyncio
    async def test_recall_memories_no_results(self, memory_manager):
        """Test memory recall with no matching results."""
        # Arrange
        memory_manager.database_manager.search_memories = AsyncMock(return_value=[])
        memory_manager.vector_encoder.encode = Mock(
            return_value=np.random.rand(384).astype(np.float32)
        )
        
        # Act
        results = await memory_manager.recall_memories(
            query="nonexistent query",
            k=5,
            tenant_id="test_tenant"
        )
        
        # Assert
        assert len(results) == 0

    @pytest.mark.parametrize("k,expected_limit", [
        (1, 1),
        (10, 10),
        (100, 100),
        (1000, 500)  # Should be capped at maximum
    ])
    @pytest.mark.asyncio
    async def test_recall_memories_k_parameter(self, memory_manager, k, expected_limit):
        """Test memory recall respects k parameter limits."""
        # Arrange
        memory_manager.database_manager.search_memories = AsyncMock(return_value=[])
        memory_manager.vector_encoder.encode = Mock(
            return_value=np.random.rand(384).astype(np.float32)
        )
        
        # Act
        await memory_manager.recall_memories(
            query="test query",
            k=k,
            tenant_id="test_tenant"
        )
        
        # Assert
        call_args = memory_manager.database_manager.search_memories.call_args
        actual_limit = call_args[1]['limit'] if 'limit' in call_args[1] else call_args[0][2]
        assert actual_limit == min(k, expected_limit)

    def test_compute_similarity(self, memory_manager):
        """Test similarity computation between vectors."""
        # Arrange
        vector1 = np.array([1, 0, 0], dtype=np.float32)
        vector2 = np.array([0, 1, 0], dtype=np.float32)  # Orthogonal
        vector3 = np.array([1, 0, 0], dtype=np.float32)  # Identical
        
        # Act
        similarity_orthogonal = memory_manager._compute_similarity(vector1, vector2)
        similarity_identical = memory_manager._compute_similarity(vector1, vector3)
        
        # Assert
        assert abs(similarity_orthogonal - 0.0) < 1e-6  # Should be ~0
        assert abs(similarity_identical - 1.0) < 1e-6   # Should be ~1

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_store_and_recall_integration(self, memory_manager):
        """Integration test for store and recall workflow."""
        # This test would use real database in integration test suite
        pass
```

### JavaScript/TypeScript Unit Testing

```typescript
// jest.config.js - Jest configuration
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src', '<rootDir>/tests'],
  testMatch: [
    '**/__tests__/**/*.+(ts|tsx|js)',
    '**/*.(test|spec).+(ts|tsx|js)'
  ],
  transform: {
    '^.+\\.(ts|tsx)$': 'ts-jest'
  },
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.test.{ts,tsx}'
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  },
  setupFilesAfterEnv: ['<rootDir>/tests/setup.ts']
};

// tests/setup.ts - Test setup
import 'jest-extended';
import { server } from './mocks/server';

// Establish API mocking before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));

// Reset any request handlers that we may add during the tests,
// so they don't affect other tests
afterEach(() => server.resetHandlers());

// Clean up after the tests are finished
afterAll(() => server.close());

// Mock console methods to avoid noise in tests
global.console = {
  ...console,
  warn: jest.fn(),
  error: jest.fn(),
};

// tests/unit/SomaBrainClient.test.ts - TypeScript unit tests
import { SomaBrainClient, SomaBrainError, SomaBrainErrorType } from '../../src/SomaBrainClient';
import { server } from '../mocks/server';
import { rest } from 'msw';

describe('SomaBrainClient', () => {
  let client: SomaBrainClient;

  beforeEach(() => {
    client = new SomaBrainClient({
      baseUrl: 'http://localhost:9696',
      apiKey: 'test-api-key',
      tenantId: 'test-tenant',
      timeout: 5000
    });
  });

  describe('constructor', () => {
    it('should initialize with correct configuration', () => {
      expect(client).toBeInstanceOf(SomaBrainClient);
      // Private properties would need getters for testing or use type assertion
      expect((client as any).baseUrl).toBe('http://localhost:9696');
      expect((client as any).tenantId).toBe('test-tenant');
    });

    it('should remove trailing slash from baseUrl', () => {
      const clientWithSlash = new SomaBrainClient({
        baseUrl: 'http://localhost:9696/',
        apiKey: 'test-key',
        tenantId: 'test-tenant'
      });
      
      expect((clientWithSlash as any).baseUrl).toBe('http://localhost:9696');
    });

    it('should set default timeout', () => {
      const clientWithoutTimeout = new SomaBrainClient({
        baseUrl: 'http://localhost:9696',
        apiKey: 'test-key',
        tenantId: 'test-tenant'
      });
      
      expect((clientWithoutTimeout as any).timeout).toBe(30000);
    });
  });

  describe('remember', () => {
    it('should store memory successfully', async () => {
      // Arrange
      const mockResponse = { memory_id: 'mem_123' };
      server.use(
        rest.post('http://localhost:9696/remember', (req, res, ctx) => {
          return res(ctx.json(mockResponse));
        })
      );

      // Act
      const result = await client.remember('Test content', { category: 'test' });

      // Assert
      expect(result).toBe('mem_123');
    });

    it('should throw error for empty content', async () => {
      // Act & Assert
      await expect(client.remember('')).rejects.toThrow(SomaBrainError);
      await expect(client.remember('   ')).rejects.toThrow(
        expect.objectContaining({
          errorType: SomaBrainErrorType.VALIDATION_ERROR,
          message: 'Memory content cannot be empty'
        })
      );
    });

    it('should handle API errors correctly', async () => {
      // Arrange
      server.use(
        rest.post('http://localhost:9696/remember', (req, res, ctx) => {
          return res(ctx.status(401), ctx.json({ error: 'Unauthorized' }));
        })
      );

      // Act & Assert
      await expect(client.remember('Test content')).rejects.toThrow(
        expect.objectContaining({
          errorType: SomaBrainErrorType.UNAUTHORIZED
        })
      );
    });

    it('should handle network timeouts', async () => {
      // Arrange
      const shortTimeoutClient = new SomaBrainClient({
        baseUrl: 'http://localhost:9696',
        apiKey: 'test-key',
        tenantId: 'test-tenant',
        timeout: 100 // Very short timeout
      });

      server.use(
        rest.post('http://localhost:9696/remember', (req, res, ctx) => {
          return res(ctx.delay(200)); // Delay longer than timeout
        })
      );

      // Act & Assert
      await expect(shortTimeoutClient.remember('Test content')).rejects.toThrow(
        expect.objectContaining({
          errorType: SomaBrainErrorType.RATE_LIMIT_EXCEEDED,
          message: 'Request timeout'
        })
      );
    });
  });

  describe('recall', () => {
    const mockMemories = [
      {
        memory_id: 'mem_1',
        content: 'Content 1',
        score: 0.9,
        metadata: { category: 'test' }
      },
      {
        memory_id: 'mem_2', 
        content: 'Content 2',
        score: 0.8,
        metadata: { category: 'test' }
      }
    ];

    it('should recall memories successfully', async () => {
      // Arrange
      server.use(
        rest.post('http://localhost:9696/recall', (req, res, ctx) => {
          return res(ctx.json({
            results: mockMemories,
            query_time_ms: 45
          }));
        })
      );

      // Act
      const result = await client.recall('test query');

      // Assert
      expect(result.memories).toHaveLength(2);
      expect(result.memories[0].id).toBe('mem_1');
      expect(result.memories[0].content).toBe('Content 1');
      expect(result.memories[0].similarityScore).toBe(0.9);
      expect(result.queryTime).toBe(45);
      expect(result.totalCount).toBe(2);
    });

    it('should use default options', async () => {
      // Arrange
      server.use(
        rest.post('http://localhost:9696/recall', (req, res, ctx) => {
          const body = req.body as any;
          expect(body.k).toBe(10);
          expect(body.threshold).toBe(0.2);
          expect(body.filters).toEqual({});
          expect(body.include_scores).toBe(true);
          
          return res(ctx.json({ results: [], query_time_ms: 10 }));
        })
      );

      // Act
      await client.recall('test query');
    });

    it('should use custom options', async () => {
      // Arrange
      const options = {
        k: 5,
        threshold: 0.5,
        filters: { category: 'specific' },
        includeScores: false
      };

      server.use(
        rest.post('http://localhost:9696/recall', (req, res, ctx) => {
          const body = req.body as any;
          expect(body.k).toBe(5);
          expect(body.threshold).toBe(0.5);
          expect(body.filters).toEqual({ category: 'specific' });
          expect(body.include_scores).toBe(false);
          
          return res(ctx.json({ results: [], query_time_ms: 10 }));
        })
      );

      // Act
      await client.recall('test query', options);
    });
  });
});

// tests/mocks/server.ts - MSW server setup
import { setupServer } from 'msw/node';
import { rest } from 'msw';

export const handlers = [
  // Default handlers for common endpoints
  rest.get('http://localhost:9696/health', (req, res, ctx) => {
    return res(ctx.json({ status: 'healthy' }));
  }),

  rest.post('http://localhost:9696/remember', (req, res, ctx) => {
    return res(ctx.json({ memory_id: 'default_memory_id' }));
  }),

  rest.post('http://localhost:9696/recall', (req, res, ctx) => {
    return res(ctx.json({ results: [], query_time_ms: 10 }));
  })
];

export const server = setupServer(...handlers);
```

---

## Integration Testing

### Database Integration Tests

```python
# tests/integration/test_database_integration.py
import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config
import tempfile
import os

from somabrain.database.models import Base, Memory, Tenant
from somabrain.database.connection import DatabaseManager
from somabrain.config import TestConfig

@pytest.fixture(scope="session")
async def test_database():
    """Create test database with migrations."""
    
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp()
    database_url = f"sqlite:///{db_path}"
    
    try:
        # Run migrations
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        command.upgrade(alembic_cfg, "head")
        
        # Create engine and session
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(bind=engine)
        
        yield {
            "url": database_url,
            "engine": engine,
            "session_factory": SessionLocal
        }
        
    finally:
        # Cleanup
        os.close(db_fd)
        os.unlink(db_path)

@pytest.fixture
async def database_manager(test_database):
    """Create DatabaseManager with test database."""
    config = TestConfig(database_url=test_database["url"])
    
    async with DatabaseManager(config) as db_manager:
        # Create test tenant
        await db_manager.create_tenant("test_tenant", "Test Tenant")
        yield db_manager

@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests for database operations."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_memory(self, database_manager):
        """Test complete memory storage and retrieval workflow."""
        
        # Store memory
        memory_id = await database_manager.store_memory(
            content="Integration test memory content",
            metadata={"category": "integration_test", "topic": "database"},
            vector_encoding=np.random.rand(384).astype(np.float32),
            tenant_id="test_tenant"
        )
        
        assert memory_id is not None
        
        # Retrieve memory
        retrieved_memory = await database_manager.get_memory(memory_id, "test_tenant")
        
        assert retrieved_memory is not None
        assert retrieved_memory.content == "Integration test memory content"
        assert retrieved_memory.metadata["category"] == "integration_test"
        assert retrieved_memory.tenant_id == "test_tenant"

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, database_manager):
        """Test that tenant isolation works correctly."""
        
        # Create another tenant
        await database_manager.create_tenant("other_tenant", "Other Tenant")
        
        # Store memory for first tenant
        memory_id_1 = await database_manager.store_memory(
            content="Tenant 1 memory",
            metadata={"tenant": "1"},
            vector_encoding=np.random.rand(384).astype(np.float32),
            tenant_id="test_tenant"
        )
        
        # Store memory for second tenant
        memory_id_2 = await database_manager.store_memory(
            content="Tenant 2 memory", 
            metadata={"tenant": "2"},
            vector_encoding=np.random.rand(384).astype(np.float32),
            tenant_id="other_tenant"
        )
        
        # Verify tenant 1 cannot access tenant 2's memory
        memory_cross_access = await database_manager.get_memory(memory_id_2, "test_tenant")
        assert memory_cross_access is None
        
        # Verify each tenant can access their own memory
        memory_1 = await database_manager.get_memory(memory_id_1, "test_tenant")
        memory_2 = await database_manager.get_memory(memory_id_2, "other_tenant")
        
        assert memory_1 is not None
        assert memory_2 is not None
        assert memory_1.metadata["tenant"] == "1"
        assert memory_2.metadata["tenant"] == "2"

    @pytest.mark.asyncio
    async def test_similarity_search(self, database_manager):
        """Test vector similarity search functionality."""
        
        # Create test vectors with known similarities
        base_vector = np.array([1, 0, 0, 0], dtype=np.float32)
        similar_vector = np.array([0.9, 0.1, 0, 0], dtype=np.float32)
        dissimilar_vector = np.array([0, 0, 1, 0], dtype=np.float32)
        
        # Store memories with different similarities
        similar_id = await database_manager.store_memory(
            content="Similar content",
            metadata={"type": "similar"},
            vector_encoding=similar_vector,
            tenant_id="test_tenant"
        )
        
        dissimilar_id = await database_manager.store_memory(
            content="Dissimilar content",
            metadata={"type": "dissimilar"},
            vector_encoding=dissimilar_vector,
            tenant_id="test_tenant"
        )
        
        # Search with base vector
        results = await database_manager.search_memories(
            query_vector=base_vector,
            limit=10,
            threshold=0.5,
            tenant_id="test_tenant"
        )
        
        # Should only return similar memory
        assert len(results) == 1
        assert results[0].id == similar_id
        assert results[0].metadata["type"] == "similar"

    @pytest.mark.asyncio
    async def test_memory_updates(self, database_manager):
        """Test memory update operations."""
        
        # Store initial memory
        memory_id = await database_manager.store_memory(
            content="Original content",
            metadata={"version": 1},
            vector_encoding=np.random.rand(384).astype(np.float32),
            tenant_id="test_tenant"
        )
        
        # Update memory
        success = await database_manager.update_memory(
            memory_id=memory_id,
            content="Updated content",
            metadata={"version": 2},
            tenant_id="test_tenant"
        )
        
        assert success is True
        
        # Verify update
        updated_memory = await database_manager.get_memory(memory_id, "test_tenant")
        assert updated_memory.content == "Updated content"
        assert updated_memory.metadata["version"] == 2

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, database_manager):
        """Test database operations under concurrent load."""
        
        async def store_memory_task(i):
            return await database_manager.store_memory(
                content=f"Concurrent memory {i}",
                metadata={"index": i},
                vector_encoding=np.random.rand(384).astype(np.float32),
                tenant_id="test_tenant"
            )
        
        # Store multiple memories concurrently
        tasks = [store_memory_task(i) for i in range(10)]
        memory_ids = await asyncio.gather(*tasks)
        
        # Verify all memories were stored
        assert len(memory_ids) == 10
        assert all(id is not None for id in memory_ids)
        
        # Verify memories can be retrieved
        for i, memory_id in enumerate(memory_ids):
            memory = await database_manager.get_memory(memory_id, "test_tenant")
            assert memory is not None
            assert memory.metadata["index"] == i
```

### API Integration Tests

```python
# tests/integration/test_api_integration.py
import pytest
import httpx
import asyncio
from contextlib import asynccontextmanager

from somabrain.api.main import create_app
from somabrain.config import TestConfig

@pytest.fixture(scope="session") 
async def test_app():
    """Create test FastAPI application."""
    config = TestConfig()
    app = create_app(config)
    return app

@pytest.fixture
async def client(test_app):
    """Create test HTTP client."""
    async with httpx.AsyncClient(app=test_app, base_url="http://test") as client:
        yield client

@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for API endpoints."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data

    @pytest.mark.asyncio
    async def test_remember_and_recall_workflow(self, client):
        """Test complete remember and recall workflow."""
        
        # Store a memory
        remember_response = await client.post(
            "/remember",
            json={
                "content": "FastAPI is a modern web framework for Python",
                "metadata": {
                    "category": "technical",
                    "topic": "web_frameworks",
                    "language": "python"
                }
            },
            headers={"X-Tenant-ID": "test_tenant", "X-API-Key": "test_key"}
        )
        
        assert remember_response.status_code == 200
        memory_data = remember_response.json()
        assert "memory_id" in memory_data
        memory_id = memory_data["memory_id"]
        
        # Recall memories
        recall_response = await client.post(
            "/recall",
            json={
                "query": "Python web framework",
                "k": 5,
                "threshold": 0.3
            },
            headers={"X-Tenant-ID": "test_tenant", "X-API-Key": "test_key"}
        )
        
        assert recall_response.status_code == 200
        recall_data = recall_response.json()
        assert "results" in recall_data
        assert len(recall_data["results"]) > 0
        
        # Verify the stored memory is in results
        memory_ids = [result["memory_id"] for result in recall_data["results"]]
        assert memory_id in memory_ids

    @pytest.mark.asyncio
    async def test_tenant_isolation_api(self, client):
        """Test tenant isolation through API."""
        
        # Store memory for tenant 1
        await client.post(
            "/remember",
            json={
                "content": "Tenant 1 specific information",
                "metadata": {"tenant": "1"}
            },
            headers={"X-Tenant-ID": "tenant_1", "X-API-Key": "test_key"}
        )
        
        # Store memory for tenant 2  
        await client.post(
            "/remember",
            json={
                "content": "Tenant 2 specific information", 
                "metadata": {"tenant": "2"}
            },
            headers={"X-Tenant-ID": "tenant_2", "X-API-Key": "test_key"}
        )
        
        # Search from tenant 1 - should not see tenant 2's data
        response_1 = await client.post(
            "/recall",
            json={"query": "Tenant 2 specific", "k": 10},
            headers={"X-Tenant-ID": "tenant_1", "X-API-Key": "test_key"}
        )
        
        # Search from tenant 2 - should not see tenant 1's data
        response_2 = await client.post(
            "/recall", 
            json={"query": "Tenant 1 specific", "k": 10},
            headers={"X-Tenant-ID": "tenant_2", "X-API-Key": "test_key"}
        )
        
        # Verify isolation
        results_1 = response_1.json()["results"]
        results_2 = response_2.json()["results"]
        
        # Each tenant should not see the other's specific information
        tenant_1_contents = [r["content"] for r in results_1]
        tenant_2_contents = [r["content"] for r in results_2]
        
        assert not any("Tenant 2 specific" in content for content in tenant_1_contents)
        assert not any("Tenant 1 specific" in content for content in tenant_2_contents)

    @pytest.mark.asyncio
    async def test_api_error_handling(self, client):
        """Test API error handling."""
        
        # Test missing tenant ID
        response = await client.post(
            "/remember",
            json={"content": "Test content", "metadata": {}},
            headers={"X-API-Key": "test_key"}  # Missing X-Tenant-ID
        )
        assert response.status_code == 400
        
        # Test invalid API key
        response = await client.post(
            "/remember",
            json={"content": "Test content", "metadata": {}},
            headers={"X-Tenant-ID": "test_tenant", "X-API-Key": "invalid_key"}
        )
        assert response.status_code == 401
        
        # Test empty content
        response = await client.post(
            "/remember",
            json={"content": "", "metadata": {}},
            headers={"X-Tenant-ID": "test_tenant", "X-API-Key": "test_key"}
        )
        assert response.status_code == 400

    @pytest.mark.asyncio  
    async def test_rate_limiting(self, client):
        """Test API rate limiting."""
        
        # Make requests rapidly to test rate limiting
        tasks = []
        for i in range(100):  # Assuming rate limit is lower than this
            task = client.post(
                "/recall",
                json={"query": f"test query {i}", "k": 1},
                headers={"X-Tenant-ID": "test_tenant", "X-API-Key": "test_key"}
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check that some requests were rate limited
        rate_limited_count = sum(
            1 for r in responses 
            if isinstance(r, httpx.Response) and r.status_code == 429
        )
        
        # Should have at least some rate limiting
        assert rate_limited_count > 0
```

---

## End-to-End Testing

### E2E Test Framework

```python
# tests/e2e/test_user_workflows.py
import pytest
import asyncio
import docker
import time
from pathlib import Path
from playwright.async_api import async_playwright

@pytest.fixture(scope="session")
async def somabrain_deployment():
    """Deploy SomaBrain for E2E testing."""
    
    # Start Docker Compose for E2E testing
    client = docker.from_env()
    
    # Build and start services
    project_root = Path(__file__).parent.parent.parent
    compose_file = project_root / "docker-compose.test.yml"
    
    try:
        # Run docker compose up
        client.compose.up(
            compose_file_path=str(compose_file),
            detach=True,
            build=True
        )
        
        # Wait for services to be ready
        await wait_for_service_health("http://localhost:9696/health", timeout=60)
        
        yield {
            "api_url": "http://localhost:9696",
            "web_url": "http://localhost:3000"  # If you have a web UI
        }
        
    finally:
        # Cleanup
        client.compose.down(compose_file_path=str(compose_file), volumes=True)

async def wait_for_service_health(url: str, timeout: int = 60):
    """Wait for service to become healthy."""
    import httpx
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5)
                if response.status_code == 200:
                    return
        except Exception:
            pass
        
        await asyncio.sleep(2)
    
    raise TimeoutError(f"Service at {url} did not become healthy within {timeout} seconds")

@pytest.mark.e2e
class TestUserWorkflows:
    """End-to-end tests simulating real user workflows."""

    @pytest.mark.asyncio
    async def test_knowledge_worker_workflow(self, somabrain_deployment):
        """Test complete workflow for knowledge worker using SomaBrain."""
        
        api_url = somabrain_deployment["api_url"]
        
        # Simulate a knowledge worker storing and retrieving information
        async with httpx.AsyncClient(base_url=api_url) as client:
            
            # 1. Store project documentation
            docs_to_store = [
                {
                    "content": "Our authentication system uses JWT tokens with 24-hour expiration",
                    "metadata": {"category": "authentication", "project": "user_service"}
                },
                {
                    "content": "Database migrations should be backward compatible and tested in staging",
                    "metadata": {"category": "deployment", "project": "user_service"}
                },
                {
                    "content": "API rate limiting is set to 1000 requests per minute per user",
                    "metadata": {"category": "api_limits", "project": "user_service"}
                }
            ]
            
            memory_ids = []
            for doc in docs_to_store:
                response = await client.post(
                    "/remember",
                    json=doc,
                    headers={"X-Tenant-ID": "knowledge_worker", "X-API-Key": "test_key"}
                )
                assert response.status_code == 200
                memory_ids.append(response.json()["memory_id"])
            
            # 2. Worker asks questions about the stored information
            questions = [
                "How long do JWT tokens last?",
                "What should I consider when creating database migrations?",
                "What are the API rate limits?"
            ]
            
            for question in questions:
                response = await client.post(
                    "/recall",
                    json={"query": question, "k": 3},
                    headers={"X-Tenant-ID": "knowledge_worker", "X-API-Key": "test_key"}
                )
                
                assert response.status_code == 200
                results = response.json()["results"]
                
                # Should find relevant information
                assert len(results) > 0
                
                # Check that similarity scores are reasonable
                assert all(result["score"] > 0.3 for result in results)
            
            # 3. Worker updates documentation
            update_response = await client.put(
                f"/memories/{memory_ids[0]}",
                json={
                    "content": "Our authentication system uses JWT tokens with 12-hour expiration for better security",
                    "metadata": {"category": "authentication", "project": "user_service", "updated": True}
                },
                headers={"X-Tenant-ID": "knowledge_worker", "X-API-Key": "test_key"}
            )
            
            assert update_response.status_code == 200
            
            # 4. Verify update is reflected in searches
            search_response = await client.post(
                "/recall",
                json={"query": "JWT token expiration", "k": 1},
                headers={"X-Tenant-ID": "knowledge_worker", "X-API-Key": "test_key"}
            )
            
            updated_result = search_response.json()["results"][0]
            assert "12-hour" in updated_result["content"]
            assert updated_result["metadata"]["updated"] is True

    @pytest.mark.asyncio
    async def test_multi_user_collaboration(self, somabrain_deployment):
        """Test collaboration between multiple users in the same tenant."""
        
        api_url = somabrain_deployment["api_url"]
        
        async with httpx.AsyncClient(base_url=api_url) as client:
            
            # User 1 stores initial knowledge
            response1 = await client.post(
                "/remember",
                json={
                    "content": "The user registration API endpoint accepts email, password, and optional profile data",
                    "metadata": {"author": "user1", "component": "registration"}
                },
                headers={"X-Tenant-ID": "team_alpha", "X-API-Key": "user1_key"}
            )
            assert response1.status_code == 200
            
            # User 2 adds related information
            response2 = await client.post(
                "/remember", 
                json={
                    "content": "Email validation for registration requires confirmed email address before account activation",
                    "metadata": {"author": "user2", "component": "registration", "relates_to": "email_validation"}
                },
                headers={"X-Tenant-ID": "team_alpha", "X-API-Key": "user2_key"}
            )
            assert response2.status_code == 200
            
            # User 3 searches for registration information
            search_response = await client.post(
                "/recall",
                json={"query": "user registration process", "k": 10},
                headers={"X-Tenant-ID": "team_alpha", "X-API-Key": "user3_key"}
            )
            
            assert search_response.status_code == 200
            results = search_response.json()["results"]
            
            # Should find contributions from both users
            authors = [result["metadata"].get("author") for result in results]
            assert "user1" in authors
            assert "user2" in authors

    @pytest.mark.asyncio
    async def test_data_export_import_workflow(self, somabrain_deployment):
        """Test complete data export and import workflow."""
        
        api_url = somabrain_deployment["api_url"]
        
        async with httpx.AsyncClient(base_url=api_url, timeout=30) as client:
            
            # 1. Store multiple memories
            memories_data = [
                {"content": f"Memory content {i}", "metadata": {"index": i, "category": "export_test"}}
                for i in range(20)
            ]
            
            for memory_data in memories_data:
                response = await client.post(
                    "/remember",
                    json=memory_data,
                    headers={"X-Tenant-ID": "export_tenant", "X-API-Key": "admin_key"}
                )
                assert response.status_code == 200
            
            # 2. Export all data
            export_response = await client.get(
                "/export",
                params={"format": "json"},
                headers={"X-Tenant-ID": "export_tenant", "X-API-Key": "admin_key"}
            )
            
            assert export_response.status_code == 200
            export_data = export_response.json()
            
            # Verify export contains all memories
            assert len(export_data["memories"]) == 20
            
            # 3. Create new tenant for import
            # (This would typically be done through admin API)
            
            # 4. Import data to new tenant
            import_response = await client.post(
                "/import",
                json=export_data,
                headers={"X-Tenant-ID": "import_tenant", "X-API-Key": "admin_key"}
            )
            
            assert import_response.status_code == 200
            import_result = import_response.json()
            assert import_result["imported_count"] == 20
            
            # 5. Verify imported data
            search_response = await client.post(
                "/recall",
                json={"query": "Memory content", "k": 25},
                headers={"X-Tenant-ID": "import_tenant", "X-API-Key": "admin_key"}
            )
            
            results = search_response.json()["results"]
            assert len(results) == 20
```

---

## Performance Testing

### Load Testing with Locust

```python
# tests/performance/load_test.py
from locust import HttpUser, task, between
import random
import json

class SomaBrainUser(HttpUser):
    """Simulate SomaBrain user behavior for load testing."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Set up user session."""
        self.tenant_id = f"tenant_{random.randint(1, 100)}"
        self.api_key = "load_test_key"
        self.headers = {
            "X-Tenant-ID": self.tenant_id,
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        self.memory_ids = []

    @task(3)
    def store_memory(self):
        """Store a new memory (most common operation)."""
        
        content_templates = [
            "User {user_id} reported issue with {component} showing {error_type} error",
            "Meeting notes: discussed {topic} with {team}, decided on {decision}",
            "Code review feedback: {component} needs {improvement_type} improvements",
            "Customer feedback: {feature} is {sentiment}, suggest {improvement}"
        ]
        
        content = random.choice(content_templates).format(
            user_id=random.randint(1, 1000),
            component=random.choice(["authentication", "database", "API", "UI"]),
            error_type=random.choice(["timeout", "validation", "connection"]),
            topic=random.choice(["architecture", "performance", "security"]),
            team=random.choice(["backend", "frontend", "devops"]),
            decision=random.choice(["refactor", "optimize", "migrate"]),
            feature=random.choice(["search", "export", "import", "analytics"]),
            sentiment=random.choice(["excellent", "good", "needs work"]),
            improvement=random.choice(["better UX", "more options", "faster response"])
        )
        
        payload = {
            "content": content,
            "metadata": {
                "category": random.choice(["support", "meeting", "review", "feedback"]),
                "priority": random.choice(["low", "medium", "high"]),
                "source": "load_test"
            }
        }
        
        with self.client.post("/remember", json=payload, headers=self.headers, 
                             catch_response=True) as response:
            if response.status_code == 200:
                memory_id = response.json().get("memory_id")
                if memory_id:
                    self.memory_ids.append(memory_id)
                response.success()
            else:
                response.failure(f"Store memory failed: {response.status_code}")

    @task(5)
    def search_memories(self):
        """Search for memories (most frequent read operation)."""
        
        queries = [
            "authentication error",
            "meeting notes",
            "performance improvement",
            "customer feedback",
            "code review",
            "database optimization",
            "API integration",
            "security update"
        ]
        
        payload = {
            "query": random.choice(queries),
            "k": random.randint(5, 15),
            "threshold": random.uniform(0.2, 0.5)
        }
        
        with self.client.post("/recall", json=payload, headers=self.headers,
                             catch_response=True) as response:
            if response.status_code == 200:
                results = response.json().get("results", [])
                if len(results) > 0:
                    # Simulate user looking at results
                    self.environment.events.request.fire(
                        request_type="VIEW",
                        name="search_results",
                        response_time=0,
                        response_length=len(results)
                    )
                response.success()
            else:
                response.failure(f"Search failed: {response.status_code}")

    @task(1)
    def update_memory(self):
        """Update existing memory (less frequent operation)."""
        
        if not self.memory_ids:
            return
        
        memory_id = random.choice(self.memory_ids)
        
        payload = {
            "content": f"Updated content for memory {memory_id} at load test",
            "metadata": {
                "updated": True,
                "update_reason": "load_test_update",
                "version": random.randint(1, 5)
            }
        }
        
        with self.client.put(f"/memories/{memory_id}", json=payload, 
                           headers=self.headers, catch_response=True) as response:
            if response.status_code in [200, 404]:  # 404 is ok for load testing
                response.success()
            else:
                response.failure(f"Update failed: {response.status_code}")

    @task(1)
    def health_check(self):
        """Periodic health check."""
        
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

# Run with: locust -f tests/performance/load_test.py --host=http://localhost:9696
```

### Performance Benchmarks

```python
# tests/performance/benchmarks.py
import pytest
import time
import asyncio
import numpy as np
from statistics import mean, stdev

from somabrain.core.memory_manager import MemoryManager
from somabrain.core.vector_encoder import VectorEncoder

@pytest.mark.benchmark
class TestPerformanceBenchmarks:
    """Performance benchmarks for SomaBrain components."""

    def test_vector_encoding_performance(self, benchmark):
        """Benchmark vector encoding performance."""
        
        encoder = VectorEncoder(model_name="all-MiniLM-L6-v2")
        test_content = "This is test content for vector encoding performance measurement."
        
        def encode_content():
            return encoder.encode(test_content)
        
        result = benchmark(encode_content)
        
        # Verify result
        assert isinstance(result, np.ndarray)
        assert result.shape[0] > 0
        
        # Performance assertions
        assert benchmark.stats.mean < 0.1  # Should encode in under 100ms

    def test_similarity_computation_performance(self, benchmark):
        """Benchmark similarity computation performance."""
        
        # Generate test vectors
        vector1 = np.random.rand(1024).astype(np.float32)
        vector2 = np.random.rand(1024).astype(np.float32)
        
        def compute_similarity():
            return np.dot(vector1, vector2) / (np.linalg.norm(vector1) * np.linalg.norm(vector2))
        
        result = benchmark(compute_similarity)
        
        # Verify result is reasonable
        assert -1 <= result <= 1
        
        # Performance assertion
        assert benchmark.stats.mean < 0.001  # Should compute in under 1ms

    @pytest.mark.asyncio
    async def test_memory_storage_throughput(self, database_manager):
        """Benchmark memory storage throughput."""
        
        # Prepare test data
        memories_data = [
            {
                "content": f"Performance test memory content {i}",
                "metadata": {"index": i, "category": "performance_test"},
                "vector_encoding": np.random.rand(384).astype(np.float32),
                "tenant_id": "perf_tenant"
            }
            for i in range(100)
        ]
        
        # Measure storage time
        start_time = time.time()
        
        # Store memories concurrently
        tasks = []
        for memory_data in memories_data:
            task = database_manager.store_memory(**memory_data)
            tasks.append(task)
        
        memory_ids = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Calculate throughput
        throughput = len(memories_data) / total_time
        
        # Assertions
        assert len(memory_ids) == 100
        assert all(id is not None for id in memory_ids)
        assert throughput > 10  # Should store at least 10 memories per second

    @pytest.mark.asyncio
    async def test_memory_search_latency(self, database_manager):
        """Benchmark memory search latency."""
        
        # Pre-populate with test data
        for i in range(1000):
            await database_manager.store_memory(
                content=f"Search performance test content {i} with various keywords",
                metadata={"index": i, "category": f"category_{i % 10}"},
                vector_encoding=np.random.rand(384).astype(np.float32),
                tenant_id="search_perf_tenant"
            )
        
        # Test search queries
        test_queries = [
            "performance test content",
            "search functionality",
            "various keywords",
            "specific category"
        ]
        
        latencies = []
        
        for query in test_queries:
            query_vector = np.random.rand(384).astype(np.float32)
            
            # Measure search time
            start_time = time.time()
            
            results = await database_manager.search_memories(
                query_vector=query_vector,
                limit=10,
                threshold=0.2,
                tenant_id="search_perf_tenant"
            )
            
            end_time = time.time()
            latency = end_time - start_time
            latencies.append(latency)
            
            # Verify results
            assert isinstance(results, list)
        
        # Calculate statistics
        avg_latency = mean(latencies)
        max_latency = max(latencies)
        
        # Performance assertions
        assert avg_latency < 0.5  # Average search under 500ms
        assert max_latency < 1.0   # No search over 1 second
```

---

## Testing Configuration

### pytest Configuration

```ini
# pytest.ini
[tool:pytest]
minversion = 6.0
addopts = 
    -ra
    -q 
    --strict-markers

    Golden truth samples live under `tests/data/golden/` and must reflect **real** service interactions—no mocks, no synthetic stand-ins.

    | File | Description | SHA256 |
    | --- | --- | --- |
    | `memories.jsonl` | Canonical episodic memory captures from the live memory endpoint. | `8ca145c78cc8f414674a92ded255636b732a46d1542d1771aa518d7b4da70459` |

    ### Update Procedure
    1. Run the live stack (docker-compose, Kind, or shared infra) with backend enforcement enabled and confirm the external memory endpoint is reachable.
    2. Export the dataset via `scripts/data/capture_memory_golden.py`.
    3. Overwrite the JSONL file and recompute `shasum -a 256 memories.jsonl`.
    4. Update the checksum table and commit both the data and documentation together.

    ### Usage

    Tests load these datasets via `tests/support/golden_data.py`. Keep consumption read-only and deterministic.

    --strict-config
    --cov=somabrain
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-report=xml
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
    benchmark: Performance benchmarks
filterwarnings =
    error
    ignore::UserWarning
    ignore::DeprecationWarning
asyncio_mode = auto
```

### CI/CD Testing Pipeline

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: somabrain_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-dev.txt
        pip install -e .

    - name: Run linting
      run: |
        flake8 somabrain/ tests/
        black --check somabrain/ tests/
        isort --check somabrain/ tests/
        mypy somabrain/

    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov=somabrain --cov-report=xml

    - name: Run integration tests
      run: |
        pytest tests/integration/ -v
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost/somabrain_test
        REDIS_URL: redis://localhost:6379

    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  e2e-test:
    runs-on: ubuntu-latest
    needs: test

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.11

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-dev.txt
        pip install -e .

    - name: Start SomaBrain services
      run: |
        docker compose -f docker-compose.test.yml up -d
        sleep 30  # Wait for services to start

    - name: Run E2E tests
      run: |
        pytest tests/e2e/ -v --tb=short

    - name: Cleanup
      if: always()
      run: |
        docker compose -f docker-compose.test.yml down -v
```

**Verification**: Testing standards are properly implemented when tests are comprehensive, fast, deterministic, and provide high confidence in code quality.

---

**Common Errors**: See [FAQ](../../user-manual/faq.md) for testing troubleshooting.

**References**:
- [Coding Standards](coding-standards.md) for test code quality
- [Local Setup Guide](local-setup.md) for test environment setup
- [API Reference](api-reference.md) for API testing patterns
- [Contribution Process](contribution-process.md) for testing workflow
