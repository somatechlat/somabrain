# API Reference

**Purpose**: Comprehensive technical reference for SomaBrain's REST API, WebSocket connections, and SDK methods for developers building integrations.

**Audience**: Software developers, DevOps engineers, and system integrators working with SomaBrain APIs.

**Prerequisites**: Understanding of REST APIs, HTTP authentication, and [Coding Standards](coding-standards.md).

---

## API Overview

### Endpoint Summary

| Endpoint | What Magic Happens | Business Impact | Developer Joy |
|----------|-------------------|-----------------|---------------|
| `/remember` | **🧠 Learns Everything** - Stores facts with deep context understanding | Turn every interaction into lasting knowledge | Simple POST request = permanent AI memory |
| `/recall` | **🔍 Finds Anything** - Semantic search that reads your mind | Customers get perfect answers instantly | Smart search that actually works |
| `/act` | **🎯 Takes Smart Action** - Does things using everything it knows | AI that acts like it has years of experience | Context-aware automation built-in |
| `/plan/suggest` | **🗺️ Makes Intelligent Plans** - Multi-step reasoning with memory | Complex workflows become simple conversations | Planning AI that remembers constraints |
| `/health` | **❤️ Self-Monitors** - Knows when something's wrong before you do | Zero-downtime production deployments | Peace of mind in your sleep |
| `/metrics` | **📊 Optimizes Itself** - Real-time performance insights | Data-driven scaling and cost optimization | Built-in observability without setup |
| `/neuromodulators` | **⚙️ Tunes Personality** - Adjust cognitive behavior in real-time | Customize AI behavior for different use cases | Fine-tune intelligence with simple parameters |

FastAPI lives in `somabrain/app.py`. The table below lists the stable backend-enforced endpoints.

| Method | Path | Purpose | Request Model | Response Model |
| --- | --- | --- | --- | --- |
| GET | `/health` | Readiness + dependency status | – | `schemas.HealthResponse` |
| GET | `/healthz` | Alias of `/health` for probes | – | Same as `/health` |
| POST | `/recall` | Retrieve memories ranked by scorer | `schemas.RecallRequest` | `schemas.RecallResponse` |
| POST | `/remember` | Persist memory payloads | `schemas.RememberRequest` | `schemas.RememberResponse` |
| POST | `/delete` | Delete long-term memory items | `schemas.DeleteRequest` | `schemas.DeleteResponse` |
| POST | `/recall/delete` | Delete working-memory rows | `schemas.DeleteRequest` | `schemas.DeleteResponse` |
| POST | `/plan/suggest` | Transport-aware planning query | `schemas.PlanSuggestRequest` | `schemas.PlanSuggestResponse` |
| POST | `/sleep/run` | Trigger offline consolidation | `schemas.SleepRunRequest` | `schemas.SleepRunResponse` |
| GET | `/sleep/status` | Status for current tenant | – | `schemas.SleepStatusResponse` |
| GET | `/sleep/status/all` | Status for all tenants | – | `schemas.SleepStatusAllResponse` |
| POST | `/personality` | Update personality parameters | `schemas.PersonalityState` | `schemas.PersonalityState` |
| POST | `/act` | Execute an action via policy | `schemas.ActRequest` | `schemas.ActResponse` |
| GET | `/neuromodulators` | Fetch neuromodulator state | – | `schemas.NeuromodStateModel` |
| POST | `/neuromodulators` | Adjust neuromodulator state | `schemas.NeuromodStateModel` | `schemas.NeuromodStateModel` |
| POST | `/graph/links` | Query graph edges for transport | `schemas.GraphLinksRequest` | `schemas.GraphLinksResponse` |

**Usage notes**:
- Write endpoints honour backend enforcement—requests fail if backing services are unreachable.
- Tenancy is selected via the `X-Soma-Tenant` header; defaults to the configured tenant when absent.
- Authentication is enabled except in dev mode per centralized settings.
- Regenerate OpenAPI artifacts with `./scripts/export_openapi.py`.

---

## Admin & Diagnostic Endpoints *(Not listed in the original table)*

The following admin‑level routes are implemented in `somabrain/app.py` but were omitted from the public API reference. They are intended for operators, debugging, and system maintenance. Access to these endpoints is typically restricted to privileged users or internal services.

| Method | Path | Purpose | Request Model | Response Model |
|--------|------|---------|---------------|----------------|
| GET | `/admin/services` | List all background services (e.g., integrator, planner) | – | `schemas.AdminServiceListResponse` |
| GET | `/admin/services/{name}` | Retrieve status of a specific service | – | `schemas.AdminServiceStatusResponse` |
| POST | `/admin/services/{name}/start` | Start a stopped service | – | `schemas.AdminServiceActionResponse` |
| POST | `/admin/services/{name}/stop` | Stop a running service | – | `schemas.AdminServiceActionResponse` |
| POST | `/admin/services/{name}/restart` | Restart a service | – | `schemas.AdminServiceActionResponse` |
| GET | `/admin/outbox` | List all outbox queues (per service) | – | `schemas.OutboxListResponse` |
| GET | `/admin/outbox/{name}` | Inspect a specific outbox queue | – | `schemas.OutboxStatusResponse` |
| POST | `/admin/outbox/replay` | Replay all pending outbox events globally | – | `schemas.OutboxReplayResponse` |
| POST | `/admin/outbox/replay/tenant` | Replay outbox events for a single tenant | – | `schemas.OutboxReplayResponse` |
| GET | `/admin/outbox/tenant/{tenant_id}` | View outbox queue for a tenant | – | `schemas.OutboxTenantStatusResponse` |
| GET | `/admin/outbox/summary` | Summarize outbox queue sizes and health | – | `schemas.OutboxSummaryResponse` |
| GET | `/admin/journal/stats` | Retrieve journal statistics (event count, size) | – | `schemas.JournalStatsResponse` |
| GET | `/admin/journal/events` | List recent journal events | – | `schemas.JournalEventsResponse` |
| POST | `/admin/journal/replay` | Replay all journal events | – | `schemas.JournalReplayResponse` |
| POST | `/admin/journal/cleanup` | Cleanup processed journal entries | – | `schemas.JournalCleanupResponse` |
| POST | `/admin/journal/init` | Initialise a fresh journal directory | – | `schemas.JournalInitResponse` |
| GET | `/admin/quotas` | List per‑tenant quota usage | – | `schemas.QuotasListResponse` |
| POST | `/admin/quotas/{tenant_id}/reset` | Reset a tenant’s daily write quota | – | `schemas.QuotaResetResponse` |
| POST | `/admin/quotas/{tenant_id}/adjust` | Adjust quota limits for a tenant | `schemas.QuotaAdjustRequest` | `schemas.QuotaAdjustResponse` |
| GET | `/health/memory` | Health check for the external memory HTTP service | – | `schemas.MemoryHealthResponse` |
| GET | `/diagnostics` | Detailed diagnostics for all components (including Redis, Postgres, Kafka) | – | `schemas.DiagnosticsResponse` |
| GET | `/reward/health` | Health of the reward subsystem | – | `schemas.RewardHealthResponse` |
| GET | `/learner/health` | Health of the learning/adaptation subsystem | – | `schemas.LearnerHealthResponse` |

**Note**: These admin routes are not part of the public SDKs and should be used with caution. They are protected by the same authentication mechanism as the public API, but additional role‑based checks (OPA policies) apply.

---

## Conditional Context Router

The `/context/*` endpoints are provided by the optional `context_route` module. In `somabrain/app.py` the router is imported inside a `try/except` block; if the import fails the endpoints are not registered. This behavior is intentional to allow lightweight deployments without the full context stack.

When deploying a full‑stack instance, ensure the `somabrain/api/context_route.py` module is present and importable so that the following routes become available:

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/context/evaluate` | Build a contextual prompt and retrieve weighted memories |
| POST | `/context/feedback` | Submit utility/feedback scores that drive the adaptation engine |

If you rely on these endpoints, verify the service logs for the message `"Context router not registered"` which indicates a missing module.


### Base Information

**Base URL**: `https://api.somabrain.com` (Production) / `http://localhost:9696` (Development)
**Version**: v1
**Protocol**: HTTPS (Production), HTTP (Development)
**Authentication**: API Key + Tenant ID headers
**Content Type**: `application/json`
**Rate Limiting**: 1000 requests/minute per tenant

### Authentication Headers

```http
X-API-Key: your-api-key-here
X-Tenant-ID: your-tenant-id
Content-Type: application/json
```

---

## Core Memory Operations

### Store Memory

Store a new memory with content and metadata.

**Endpoint**: `POST /remember`

**Request**:
```json
{
  "content": "FastAPI is a modern, fast web framework for building APIs with Python",
  "metadata": {
    "category": "technical",
    "topic": "web_frameworks",
    "language": "python",
    "source": "documentation",
    "tags": ["api", "python", "framework"]
  }
}
```

**Response**:
```json
{
  "memory_id": "mem_9f2a8b1e4d7c6a5b",
  "status": "stored",
  "processing_time_ms": 145,
  "vector_dimensions": 1024,
  "metadata": {
    "category": "technical",
    "topic": "web_frameworks",
    "language": "python",
    "source": "documentation",
    "tags": ["api", "python", "framework"],
    "created_at": "2024-01-15T10:30:45.123Z",
    "tenant_id": "your-tenant-id"
  }
}
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `content` | string | Yes | Memory content (1-50,000 characters) |
| `metadata` | object | No | Key-value metadata pairs |

**Status Codes**:

| Code | Description |
|------|-------------|
| 200 | Memory stored successfully |
| 400 | Invalid request (empty content, malformed JSON) |
| 401 | Authentication failed (invalid API key) |
| 403 | Authorization failed (invalid tenant) |
| 413 | Content too large (>50,000 characters) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

**Example with cURL**:
```bash
curl -X POST https://api.somabrain.com/remember \
  -H "X-API-Key: your-api-key" \
  -H "X-Tenant-ID: your-tenant-id" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Memory content here",
    "metadata": {"category": "example"}
  }'
```

### Recall Memories

Search and retrieve memories based on semantic similarity.

**Endpoint**: `POST /recall`

**Request**:
```json
{
  "query": "Python web framework performance",
  "k": 10,
  "threshold": 0.3,
  "filters": {
    "category": "technical",
    "language": "python"
  },
  "include_metadata": true,
  "include_scores": true
}
```

**Response**:
```json
{
  "results": [
    {
      "memory_id": "mem_9f2a8b1e4d7c6a5b",
      "content": "FastAPI is a modern, fast web framework for building APIs with Python",
      "similarity_score": 0.89,
      "metadata": {
        "category": "technical",
        "topic": "web_frameworks",
        "language": "python",
        "created_at": "2024-01-15T10:30:45.123Z"
      }
    },
    {
      "memory_id": "mem_7e4c2f8a9b5d1c3e",
      "content": "Django provides a comprehensive web framework with ORM and admin interface",
      "similarity_score": 0.76,
      "metadata": {
        "category": "technical",
        "topic": "web_frameworks",
        "language": "python",
        "created_at": "2024-01-14T15:22:33.456Z"
      }
    }
  ],
  "total_results": 2,
  "query_time_ms": 87,
  "query_vector_dimensions": 1024
}
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query text |
| `k` | integer | No | 10 | Maximum number of results (1-100) |
| `threshold` | number | No | 0.2 | Minimum similarity score (0.0-1.0) |
| `filters` | object | No | {} | Metadata filters |
| `include_metadata` | boolean | No | true | Include memory metadata |
| `include_scores` | boolean | No | true | Include similarity scores |

**Example with cURL**:
```bash
curl -X POST https://api.somabrain.com/recall \
  -H "X-API-Key: your-api-key" \
  -H "X-Tenant-ID: your-tenant-id" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python web frameworks",
    "k": 5,
    "threshold": 0.3
  }'
```

### Get Memory by ID

Retrieve a specific memory by its unique identifier.

**Endpoint**: `GET /memories/{memory_id}`

**Response**:
```json
{
  "memory_id": "mem_9f2a8b1e4d7c6a5b",
  "content": "FastAPI is a modern, fast web framework for building APIs with Python",
  "metadata": {
    "category": "technical",
    "topic": "web_frameworks",
    "language": "python",
    "created_at": "2024-01-15T10:30:45.123Z",
    "updated_at": "2024-01-15T10:30:45.123Z"
  },
  "vector_dimensions": 1024,
  "tenant_id": "your-tenant-id"
}
```

**Status Codes**:

| Code | Description |
|------|-------------|
| 200 | Memory retrieved successfully |
| 404 | Memory not found or access denied |
| 401 | Authentication failed |

### Update Memory

Update existing memory content and metadata.

**Endpoint**: `PUT /memories/{memory_id}`

**Request**:
```json
{
  "content": "FastAPI is a modern, high-performance web framework for building APIs with Python 3.7+",
  "metadata": {
    "category": "technical",
    "topic": "web_frameworks",
    "language": "python",
    "updated": true,
    "version": "2.0"
  }
}
```

**Response**:
```json
{
  "memory_id": "mem_9f2a8b1e4d7c6a5b",
  "status": "updated",
  "processing_time_ms": 123,
  "changes": {
    "content_updated": true,
    "metadata_updated": true,
    "vector_recomputed": true
  }
}
```

### Delete Memory

Remove a memory permanently.

**Endpoint**: `DELETE /memories/{memory_id}`

**Response**:
```json
{
  "memory_id": "mem_9f2a8b1e4d7c6a5b",
  "status": "deleted",
  "deleted_at": "2024-01-15T11:45:22.789Z"
}
```

**Status Codes**:

| Code | Description |
|------|-------------|
| 200 | Memory deleted successfully |
| 404 | Memory not found |
| 409 | Memory cannot be deleted (referenced by others) |

---

## Cognitive Reasoning

### Generate Reasoning Chain

Create a reasoning chain from multiple memories and context.

**Endpoint**: `POST /reason`

**Request**:
```json
{
  "context": "I need to choose a Python web framework for a high-performance API",
  "memory_ids": ["mem_9f2a8b1e4d7c6a5b", "mem_7e4c2f8a9b5d1c3e"],
  "reasoning_depth": "detailed",
  "include_sources": true
}
```

**Response**:
```json
{
  "reasoning_chain": [
    {
      "step": 1,
      "premise": "FastAPI provides modern async support and automatic API documentation",
      "source_memory_id": "mem_9f2a8b1e4d7c6a5b",
      "confidence": 0.92
    },
    {
      "step": 2,
      "premise": "Django is comprehensive but may have more overhead for simple APIs",
      "source_memory_id": "mem_7e4c2f8a9b5d1c3e",
      "confidence": 0.85
    },
    {
      "step": 3,
      "conclusion": "For high-performance APIs, FastAPI is recommended due to async support and lower overhead",
      "confidence": 0.89,
      "supporting_evidence": ["async_performance", "documentation_automation"]
    }
  ],
  "overall_confidence": 0.89,
  "processing_time_ms": 234,
  "sources_used": 2
}
```

### Analyze Memory Patterns

Analyze patterns and relationships in stored memories.

**Endpoint**: `POST /analyze`

**Request**:
```json
{
  "analysis_type": "topic_clustering",
  "filters": {
    "category": "technical",
    "date_range": {
      "start": "2024-01-01T00:00:00Z",
      "end": "2024-01-31T23:59:59Z"
    }
  },
  "max_clusters": 10
}
```

**Response**:
```json
{
  "analysis_results": {
    "clusters": [
      {
        "cluster_id": "cluster_1",
        "topic": "web_frameworks",
        "memory_count": 15,
        "representative_memories": [
          "mem_9f2a8b1e4d7c6a5b",
          "mem_7e4c2f8a9b5d1c3e"
        ],
        "confidence": 0.87
      }
    ],
    "total_memories_analyzed": 150,
    "processing_time_ms": 1205
  }
}
```

---

## Tenant Management

### Create Tenant

Create a new tenant space (Admin only).

**Endpoint**: `POST /tenants`

**Request**:
```json
{
  "tenant_id": "new-tenant-001",
  "name": "New Organization",
  "description": "Tenant for new organization",
  "settings": {
    "max_memories": 100000,
    "vector_dimensions": 1024,
    "retention_days": 365
  }
}
```

### Get Tenant Information

Retrieve tenant configuration and usage statistics.

**Endpoint**: `GET /tenants/{tenant_id}`

**Response**:
```json
{
  "tenant_id": "your-tenant-id",
  "name": "Your Organization",
  "created_at": "2024-01-01T00:00:00Z",
  "settings": {
    "max_memories": 100000,
    "vector_dimensions": 1024,
    "retention_days": 365
  },
  "usage": {
    "memory_count": 1543,
    "storage_used_mb": 245.7,
    "api_calls_today": 892,
    "api_calls_month": 24567
  },
  "limits": {
    "requests_per_minute": 1000,
    "max_content_length": 50000,
    "max_memories": 100000
  }
}
```

---

## Batch Operations

### Batch Store Memories

Store multiple memories in a single request.

**Endpoint**: `POST /remember/batch`

**Request**:
```json
{
  "memories": [
    {
      "content": "First memory content",
      "metadata": {"category": "batch_test", "index": 1}
    },
    {
      "content": "Second memory content",
      "metadata": {"category": "batch_test", "index": 2}
    }
  ],
  "options": {
    "fail_on_error": false,
    "return_memory_ids": true
  }
}
```

**Response**:
```json
{
  "results": [
    {
      "index": 0,
      "status": "success",
      "memory_id": "mem_abc123",
      "processing_time_ms": 145
    },
    {
      "index": 1,
      "status": "success",
      "memory_id": "mem_def456",
      "processing_time_ms": 134
    }
  ],
  "summary": {
    "total_submitted": 2,
    "successful": 2,
    "failed": 0,
    "total_processing_time_ms": 279
  }
}
```

### Export Memories

Export tenant memories for backup or migration.

**Endpoint**: `GET /export`

**Query Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `format` | string | Export format: `json`, `csv`, `jsonl` |
| `filters` | object | Metadata filters (JSON encoded) |
| `include_vectors` | boolean | Include vector encodings |

**Response**: File download with specified format

---

## Real-time Operations

### WebSocket Connection

Establish real-time connection for streaming operations.

**Endpoint**: `ws://localhost:9696/ws/{tenant_id}`

**Authentication**: Send API key in first message:
```json
{
  "type": "auth",
  "api_key": "your-api-key"
}
```

**Message Types**:

#### Memory Notifications
```json
{
  "type": "memory_stored",
  "memory_id": "mem_abc123",
  "content_preview": "First 100 characters...",
  "timestamp": "2024-01-15T10:30:45.123Z"
}
```

#### Real-time Search
```json
{
  "type": "search_request",
  "query": "Python frameworks",
  "request_id": "req_789"
}
```

#### Search Results Stream
```json
{
  "type": "search_results",
  "request_id": "req_789",
  "results": [...],
  "is_complete": false
}
```

---

## SDK Documentation

### Python SDK

**Installation**:
```bash
pip install somabrain-python
```

**Basic Usage**:
```python
from somabrain import SomaBrainClient

# Initialize client
client = SomaBrainClient(
    api_key="your-api-key",
    tenant_id="your-tenant-id",
    base_url="https://api.somabrain.com"
)

# Store memory
memory_id = await client.remember(
    content="Python is a programming language",
    metadata={"category": "programming"}
)

# Recall memories
results = await client.recall(
    query="programming language",
    k=5
)

# Process results
for memory in results.memories:
    print(f"ID: {memory.id}")
    print(f"Content: {memory.content}")
    print(f"Score: {memory.similarity_score}")
```

**Advanced Features**:
```python
# Batch operations
memories = [
    {"content": "Content 1", "metadata": {"type": "test"}},
    {"content": "Content 2", "metadata": {"type": "test"}}
]
results = await client.remember_batch(memories)

# Streaming search
async for result in client.recall_stream(query="test query"):
    print(f"Streaming result: {result.content}")

# Memory updates
await client.update_memory(
    memory_id="mem_123",
    content="Updated content",
    metadata={"updated": True}
)

# Error handling
try:
    await client.remember("")
except SomaBrainError as e:
    print(f"Error: {e.message}")
    print(f"Error type: {e.error_type}")
```

### TypeScript/JavaScript SDK

**Installation**:
```bash
npm install @somabrain/js-sdk
```

**Basic Usage**:
```typescript
import { SomaBrainClient } from '@somabrain/js-sdk';

// Initialize client
const client = new SomaBrainClient({
  apiKey: 'your-api-key',
  tenantId: 'your-tenant-id',
  baseUrl: 'https://api.somabrain.com'
});

// Store memory
const memoryId = await client.remember(
  'JavaScript is a programming language',
  { category: 'programming' }
);

// Recall memories
const results = await client.recall('programming language', {
  k: 5,
  threshold: 0.3
});

// Process results
results.memories.forEach(memory => {
  console.log(`ID: ${memory.id}`);
  console.log(`Content: ${memory.content}`);
  console.log(`Score: ${memory.similarityScore}`);
});
```

**React Hook**:
```typescript
import { useSomaBrain } from '@somabrain/react-hooks';

function MyComponent() {
  const { remember, recall, loading, error } = useSomaBrain({
    apiKey: process.env.REACT_APP_SOMABRAIN_API_KEY,
    tenantId: 'your-tenant-id'
  });

  const handleSearch = async (query: string) => {
    try {
      const results = await recall(query);
      setSearchResults(results.memories);
    } catch (err) {
      console.error('Search failed:', err);
    }
  };

  return (
    <div>
      {loading && <div>Loading...</div>}
      {error && <div>Error: {error.message}</div>}
      {/* Your UI here */}
    </div>
  );
}
```

---

## Error Handling

### Error Response Format

All API errors follow this structure:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Memory content cannot be empty",
    "details": {
      "field": "content",
      "provided_value": "",
      "expected": "non-empty string"
    },
    "request_id": "req_9f2a8b1e4d7c6a5b",
    "timestamp": "2024-01-15T10:30:45.123Z"
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request parameters |
| `AUTHENTICATION_FAILED` | 401 | Invalid or missing API key |
| `AUTHORIZATION_FAILED` | 403 | Invalid tenant or permissions |
| `RESOURCE_NOT_FOUND` | 404 | Memory or resource not found |
| `CONFLICT` | 409 | Resource conflict (duplicate ID) |
| `CONTENT_TOO_LARGE` | 413 | Content exceeds size limits |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

### Retry Logic

```python
import time
import random
from typing import Optional

async def retry_with_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
):
    """Retry function with exponential backoff."""

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except SomaBrainError as e:
            if e.error_type in ['RATE_LIMIT_EXCEEDED', 'SERVICE_UNAVAILABLE']:
                if attempt == max_retries:
                    raise

                # Calculate delay
                delay = min(base_delay * (exponential_base ** attempt), max_delay)
                if jitter:
                    delay *= (0.5 + random.random() * 0.5)  # Add jitter

                await asyncio.sleep(delay)
            else:
                raise  # Don't retry on non-transient errors

    raise Exception("Max retries exceeded")

# Usage
result = await retry_with_backoff(
    lambda: client.remember("content", {"meta": "data"})
)
```

---

## Rate Limiting

### Rate Limit Headers

API responses include rate limiting information:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 985
X-RateLimit-Reset: 1642247445
X-RateLimit-Retry-After: 60
```

### Rate Limit Types

| Operation | Limit | Window |
|-----------|-------|--------|
| General API calls | 1000 requests | per minute |
| Memory storage | 100 requests | per minute |
| Search queries | 500 requests | per minute |
| Batch operations | 10 requests | per minute |

---

## Monitoring and Observability

### Health Check

**Endpoint**: `GET /health`

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 12
    },
    "vector_service": {
      "status": "healthy",
      "response_time_ms": 45
    },
    "cache": {
      "status": "healthy",
      "hit_rate": 0.87
    }
  }
}
```

### Metrics Endpoint

**Endpoint**: `GET /metrics` (Prometheus format)

**Example Metrics**:
```
# HELP somabrain_requests_total Total number of requests
# TYPE somabrain_requests_total counter
somabrain_requests_total{method="POST",endpoint="/remember",status="200"} 1543

# HELP somabrain_response_time_seconds Response time in seconds
# TYPE somabrain_response_time_seconds histogram
somabrain_response_time_seconds_bucket{endpoint="/recall",le="0.1"} 892
somabrain_response_time_seconds_bucket{endpoint="/recall",le="0.5"} 1234

# HELP somabrain_memories_total Total number of stored memories
# TYPE somabrain_memories_total gauge
somabrain_memories_total{tenant="tenant_1"} 15432
```

**Verification**: API implementation is complete when all endpoints return correct responses with proper error handling and follow OpenAPI specification.

---

**Common Errors**:

| Issue | Solution |
|-------|----------|
| 401 Authentication Failed | Verify API key is correct and active |
| 403 Authorization Failed | Check tenant ID matches your account |
| 429 Rate Limited | Implement exponential backoff retry logic |
| 400 Validation Error | Check request format matches API specification |
| 500 Internal Error | Check service status and retry with backoff |

**References**:
- [Testing Guidelines](testing-guidelines.md) for API testing examples
- [Coding Standards](coding-standards.md) for API client implementation
- [Contribution Process](contribution-process.md) for API changes
- [API Integration](../user-manual/features/api-integration.md) for usage examples
