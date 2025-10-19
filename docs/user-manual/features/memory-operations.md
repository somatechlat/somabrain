# Memory Operations Guide

**Purpose**: Comprehensive guide to SomaBrain's core memory storage, retrieval, and management capabilities.

**Audience**: Developers and power users working with SomaBrain's cognitive memory system.

**Prerequisites**: SomaBrain installation complete and [Quick Start Tutorial](../quick-start-tutorial.md) completed.

---

## Memory Architecture Overview

SomaBrain implements a **hyperdimensional computing** approach to memory that mimics human cognitive processes:

### Core Concepts

**Semantic Encoding**: Content is transformed into high-dimensional vectors (typically 1024+ dimensions) that capture meaning rather than just keywords.

**Contextual Storage**: Memories include both content and structured metadata that provides context for retrieval and reasoning.

**Associative Recall**: Queries find memories based on semantic similarity, not exact matching, allowing natural language interaction.

**Temporal Awareness**: Memory scoring considers recency, frequency, and contextual relevance to surface the most appropriate memories.

### Memory Structure

Each memory consists of:

```json
{
  "id": "mem_unique_identifier",
  "content": "The actual memory content as text",
  "metadata": {
    "category": "classification_label",
    "topic": "subject_area",
    "timestamp": "2025-10-15T10:00:00Z",
    "confidence": 0.85,
    "custom_fields": "flexible_additional_data"
  },
  "vector_encoding": "[hidden_internal_representation]",
  "tenant_id": "user_or_organization_scope"
}
```

---

## Memory Storage Operations

### Basic Memory Storage

Store a single memory with content and metadata:

```bash
curl -X POST http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: your_tenant" \
  -d '{
    "content": "Redis is an in-memory data structure store used as database, cache, and message broker",
    "metadata": {
      "category": "technical_knowledge",
      "topic": "databases",
      "technology": "redis",
      "source": "documentation",
      "confidence": 0.9,
      "tags": ["nosql", "cache", "performance"],
      "created_at": "2025-10-15T10:00:00Z"
    }
  }'
```

**Response**:
```json
{
  "success": true,
  "memory_id": "mem_tech_redis_001",
  "message": "Memory stored successfully",
  "encoding_time_ms": 45,
  "vector_dimensions": 1024
}
```

**Verification**: Memory ID is returned for future reference and updates.

### Batch Memory Storage

Store multiple memories in a single operation:

```bash
curl -X POST http://localhost:9696/remember/batch \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: your_tenant" \
  -d '{
    "memories": [
      {
        "content": "PostgreSQL supports ACID transactions and complex queries with JSON columns",
        "metadata": {
          "category": "technical_knowledge",
          "topic": "databases",
          "technology": "postgresql",
          "features": ["acid", "json", "sql"]
        }
      },
      {
        "content": "MongoDB is a document database with flexible schema and horizontal scaling",
        "metadata": {
          "category": "technical_knowledge",
          "topic": "databases",
          "technology": "mongodb",
          "features": ["document", "nosql", "scaling"]
        }
      }
    ]
  }'
```

**Response**:
```json
{
  "success": true,
  "stored_count": 2,
  "memory_ids": ["mem_tech_postgres_001", "mem_tech_mongo_001"],
  "failed_count": 0,
  "total_time_ms": 120
}
```

**Verification**: All memories receive unique IDs and are processed atomically.

### Memory with Relationships

Store memories that explicitly reference other memories:

```bash
curl -X POST http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: your_tenant" \
  -d '{
    "content": "For our user service, we chose PostgreSQL over MongoDB because we need ACID transactions for payment processing",
    "metadata": {
      "category": "architectural_decisions",
      "decision_id": "ADR-003",
      "project": "user_service",
      "relates_to": ["mem_tech_postgres_001", "mem_tech_mongo_001"],
      "relationship_type": "comparison",
      "decision_date": "2025-10-01",
      "status": "accepted"
    }
  }'
```

**Key Features**:
- `relates_to`: Array of memory IDs that this memory references
- `relationship_type`: Describes the nature of the relationship
- Enables contextual querying across related memories

---

## Memory Retrieval Operations

### Basic Semantic Search

Retrieve memories using natural language queries:

```bash
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: your_tenant" \
  -d '{
    "query": "What database should I use for transactions?",
    "k": 3,
    "threshold": 0.3
  }'
```

**Response**:
```json
{
  "results": [
    {
      "memory_id": "mem_arch_postgres_decision",
      "content": "For our user service, we chose PostgreSQL over MongoDB because we need ACID transactions...",
      "score": 0.89,
      "metadata": {
        "category": "architectural_decisions",
        "decision_id": "ADR-003"
      },
      "explanation": "High semantic match for 'transactions' and 'database choice'"
    },
    {
      "memory_id": "mem_tech_postgres_001",
      "content": "PostgreSQL supports ACID transactions and complex queries...",
      "score": 0.76,
      "metadata": {
        "technology": "postgresql",
        "features": ["acid", "transactions"]
      },
      "explanation": "Direct feature match for ACID transactions"
    }
  ],
  "query_time_ms": 23,
  "total_memories_searched": 1247
}
```

**Parameters**:
- `k`: Maximum number of results (default: 10)
- `threshold`: Minimum similarity score (default: 0.2)
- `include_explanation`: Add reasoning for why memories matched

### Advanced Filtering

Combine semantic search with metadata filters:

```bash
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: your_tenant" \
  -d '{
    "query": "recent database decisions",
    "k": 5,
    "filters": {
      "category": "architectural_decisions",
      "decision_date_after": "2025-09-01",
      "status": "accepted",
      "project": ["user_service", "payment_service"]
    },
    "sort_by": "decision_date",
    "sort_order": "desc"
  }'
```

**Filter Types**:
- **Exact Match**: `"status": "accepted"`
- **Array Contains**: `"tags": {"$contains": "performance"}`
- **Range Queries**: `"confidence": {"$gte": 0.8}`
- **Date Ranges**: `"created_after": "2025-01-01"`
- **Multiple Values**: `"category": ["technical", "business"]`

### Contextual Search with Relationships

Search memories and expand related content:

```bash
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: your_tenant" \
  -d '{
    "query": "database architecture decisions",
    "k": 3,
    "expand_relationships": true,
    "relationship_depth": 2,
    "include_related_score": true
  }'
```

**Response includes**:
- Primary matching memories
- Related memories referenced via `relates_to`
- Relationship scores and types
- Context paths showing connection reasoning

### Temporal and Frequency-Based Recall

Query memories with time-aware scoring:

```bash
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: your_tenant" \
  -d '{
    "query": "database performance optimization",
    "k": 5,
    "scoring": {
      "semantic_weight": 0.5,
      "recency_weight": 0.3,
      "frequency_weight": 0.2
    },
    "time_decay": {
      "half_life_days": 30,
      "boost_recent": true
    }
  }'
```

**Scoring Components**:
- **Semantic Weight**: Cosine similarity of content vectors
- **Recency Weight**: How recently memory was created/accessed
- **Frequency Weight**: How often memory has been retrieved
- **Time Decay**: Exponential decay function for temporal relevance

---

## Memory Management Operations

### Memory Updates

Update memory content while preserving history:

```bash
curl -X PUT http://localhost:9696/memories/mem_tech_redis_001 \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: your_tenant" \
  -d '{
    "content": "Redis 7.0 is an in-memory data structure store with improved functions and better memory efficiency",
    "metadata": {
      "category": "technical_knowledge",
      "topic": "databases",
      "technology": "redis",
      "version": "7.0",
      "update_reason": "version_upgrade",
      "previous_version": "mem_tech_redis_001_v1"
    }
  }'
```

**Behavior**:
- Creates new vector encoding for updated content
- Preserves previous version as historical record
- Updates similarity relationships automatically
- Maintains memory ID for consistency

### Memory Deletion

Remove memories individually or in bulk:

```bash
# Delete single memory
curl -X DELETE http://localhost:9696/memories/mem_tech_redis_001 \
  -H "X-Tenant-ID: your_tenant"

# Delete multiple memories
curl -X DELETE http://localhost:9696/memories \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: your_tenant" \
  -d '{
    "memory_ids": ["mem_old_001", "mem_old_002"],
    "confirm": true
  }'

# Delete by metadata filter
curl -X DELETE http://localhost:9696/memories \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: your_tenant" \
  -d '{
    "filters": {
      "category": "temp_notes",
      "created_before": "2025-01-01"
    },
    "dry_run": false
  }'
```

**Safety Features**:
- `dry_run`: Preview deletion without executing
- `confirm`: Required for bulk operations
- Cascade handling for related memories

### Memory Metadata Updates

Update only metadata without re-encoding content:

```bash
curl -X PATCH http://localhost:9696/memories/mem_tech_redis_001/metadata \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: your_tenant" \
  -d '{
    "metadata": {
      "tags": ["nosql", "cache", "performance", "production"],
      "priority": "high",
      "last_reviewed": "2025-10-15",
      "review_status": "current"
    }
  }'
```

**Advantages**:
- Faster than full memory update
- Preserves existing vector encoding
- Enables metadata-only operations like tagging

---

## Advanced Memory Operations

### Memory Clustering and Analysis

Analyze memory patterns and find clusters:

```bash
# Find memory clusters by similarity
curl -X POST http://localhost:9696/analyze/clusters \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: your_tenant" \
  -d '{
    "filters": {
      "category": "technical_knowledge"
    },
    "cluster_method": "kmeans",
    "num_clusters": 5,
    "include_samples": true
  }'
```

**Response**:
```json
{
  "clusters": [
    {
      "cluster_id": 0,
      "topic": "databases",
      "memory_count": 23,
      "centroid_keywords": ["database", "sql", "nosql", "performance"],
      "sample_memories": ["mem_tech_postgres_001", "mem_tech_mongo_001"]
    }
  ]
}
```

### Memory Similarity Networks

Find related memories through similarity networks:

```bash
curl -X GET http://localhost:9696/memories/mem_tech_redis_001/network \
  -H "X-Tenant-ID: your_tenant" \
  -d '{
    "similarity_threshold": 0.6,
    "max_depth": 3,
    "include_paths": true
  }'
```

**Use Cases**:
- Discover implicit relationships between memories
- Build knowledge graphs from memory content
- Find gaps in knowledge coverage

### Bulk Memory Operations

Process large numbers of memories efficiently:

```bash
# Bulk similarity scoring
curl -X POST http://localhost:9696/bulk/similarity \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: your_tenant" \
  -d '{
    "source_memory_id": "mem_reference_001",
    "target_filters": {
      "category": "technical_knowledge"
    },
    "batch_size": 1000,
    "include_scores": true
  }'

# Bulk metadata updates
curl -X PATCH http://localhost:9696/bulk/metadata \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: your_tenant" \
  -d '{
    "filters": {
      "category": "old_format"
    },
    "updates": {
      "category": "technical_knowledge",
      "migrated": true,
      "migration_date": "2025-10-15"
    }
  }'
```

---

## Memory Performance Optimization

### Vector Encoding Optimization

Configure encoding parameters for different content types:

```bash
# Optimize for technical content
curl -X POST http://localhost:9696/configure/encoding \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: your_tenant" \
  -d '{
    "content_type": "technical",
    "vector_dimensions": 1024,
    "encoding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "preprocessing": {
      "normalize_code": true,
      "expand_acronyms": true,
      "preserve_structure": true
    }
  }'
```

### Similarity Search Optimization

Tune search parameters for different query patterns:

```bash
# Fast approximate search
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: your_tenant" \
  -d '{
    "query": "database optimization techniques",
    "k": 10,
    "search_mode": "approximate",
    "index_type": "ivf",
    "probe_count": 16,
    "max_search_time_ms": 100
  }'
```

**Search Modes**:
- `exact`: Exhaustive search (slower, perfect recall)
- `approximate`: FAISS-based approximation (faster, good recall)
- `hybrid`: Combines both approaches

### Memory Indexing Strategies

Configure indexing for different access patterns:

```yaml
# config/memory_indexing.yaml
indexes:
  semantic:
    type: "ivf_flat"
    nlist: 1024
    dimensions: 1024

  metadata:
    fields: ["category", "topic", "created_at"]
    compound_indexes:
      - ["category", "created_at"]
      - ["topic", "confidence"]

  hybrid:
    semantic_weight: 0.7
    metadata_weight: 0.3
```

---

## Memory Quality and Validation

### Content Quality Assessment

Evaluate memory content quality automatically:

```bash
curl -X POST http://localhost:9696/validate/quality \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: your_tenant" \
  -d '{
    "content": "Redis is fast",
    "metadata": {"category": "technical"},
    "quality_checks": [
      "content_length",
      "semantic_richness",
      "metadata_completeness",
      "uniqueness"
    ]
  }'
```

**Response**:
```json
{
  "quality_score": 0.65,
  "issues": [
    {
      "type": "content_length",
      "severity": "warning",
      "message": "Content is very brief (13 chars). Consider adding more detail.",
      "suggestion": "Include specific Redis features, use cases, or technical details"
    }
  ],
  "recommendations": [
    "Add technical details about Redis performance characteristics",
    "Include usage examples or configuration details",
    "Consider adding version information or context"
  ]
}
```

### Duplicate Detection

Identify and manage duplicate or near-duplicate memories:

```bash
curl -X POST http://localhost:9696/analyze/duplicates \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: your_tenant" \
  -d '{
    "similarity_threshold": 0.95,
    "include_near_duplicates": true,
    "grouping_method": "content_hash",
    "suggested_actions": true
  }'
```

---

## Error Handling and Troubleshooting

### Common Memory Operation Errors

| Error Code | Description | Solution |
|------------|-------------|----------|
| `MEM_001` | Content encoding failed | Check content UTF-8 encoding and length limits |
| `MEM_002` | Metadata validation failed | Verify JSON schema compliance |
| `MEM_003` | Memory not found | Confirm memory ID and tenant scope |
| `MEM_004` | Similarity computation timeout | Reduce search scope or increase timeout |
| `MEM_005` | Vector dimension mismatch | Consistent encoding model across operations |
| `MEM_006` | Tenant isolation violation | Check X-Tenant-ID header |
| `MEM_007` | Rate limit exceeded | Implement backoff or increase limits |
| `MEM_008` | Storage capacity exceeded | Clean up old memories or increase storage |

### Memory Operation Diagnostics

Debug memory operations with detailed logging:

```bash
# Enable memory operation tracing
curl -X POST http://localhost:9696/debug/trace \
  -H "X-Tenant-ID: your_tenant" \
  -d '{
    "trace_memory_operations": true,
    "trace_similarity_computation": true,
    "trace_metadata_filtering": true,
    "output_format": "json"
  }'

# Run operation with tracing enabled
curl -X POST http://localhost:9696/recall?trace=true \
  -H "X-Tenant-ID: your_tenant" \
  -d '{"query": "database performance"}'
```

**Verification**: Check logs for detailed operation timing and decision paths.

---

## Integration Examples

### Python SDK Usage

```python
from somabrain import MemoryClient

client = MemoryClient(
    base_url="http://localhost:9696",
    tenant_id="your_tenant",
    api_key="your_api_key"
)

# Store memory
memory_id = client.remember(
    content="FastAPI is a modern Python web framework with automatic API documentation",
    metadata={
        "category": "technical_knowledge",
        "technology": "fastapi",
        "language": "python"
    }
)

# Recall memories
results = client.recall(
    query="Python web frameworks with good documentation",
    k=5,
    filters={"language": "python"}
)

for result in results:
    print(f"Score: {result.score:.3f}")
    print(f"Content: {result.content}")
    print(f"Metadata: {result.metadata}")
    print("---")
```

### JavaScript Integration

```javascript
import { SomaBrainClient } from '@somabrain/client';

const client = new SomaBrainClient({
  baseUrl: 'http://localhost:9696',
  tenantId: 'your_tenant',
  apiKey: 'your_api_key'
});

// Store memory
const { memoryId } = await client.remember({
  content: 'React hooks allow state management in functional components',
  metadata: {
    category: 'technical_knowledge',
    technology: 'react',
    language: 'javascript'
  }
});

// Recall memories
const results = await client.recall({
  query: 'React state management patterns',
  k: 3,
  filters: { technology: 'react' }
});

results.forEach(result => {
  console.log(`Score: ${result.score.toFixed(3)}`);
  console.log(`Content: ${result.content}`);
  console.log(`Metadata:`, result.metadata);
  console.log('---');
});
```

---

**Common Errors**: See [FAQ](../faq.md) for troubleshooting specific memory operation issues.

**References**:
- [Quick Start Tutorial](../quick-start-tutorial.md) for basic memory operations
- [API Integration Guide](api-integration.md) for development examples
- [Cognitive Reasoning Guide](cognitive-reasoning.md) for advanced memory usage
- [Technical Architecture](../../technical-manual/architecture.md) for system design details