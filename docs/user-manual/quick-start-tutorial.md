# Quick Start Tutorial

**Purpose**: Guide new users through their first SomaBrain workflow to store and recall memories.

**Audience**: End-users and developers new to SomaBrain cognitive memory operations.

**Prerequisites**: SomaBrain installed and running (see [Installation Guide](installation.md)).

---

## Tutorial Overview

**Time Required**: 15 minutes

**What You'll Learn**:
- Store your first memory with semantic metadata
- Recall memories using natural language queries
- Understand cognitive similarity vs exact matching
- Use basic memory operations via REST API

## Step 1: Verify SomaBrain is Running

First, confirm your SomaBrain installation is working:

```bash
# Check service health
curl -f http://localhost:9696/health

# Expected response
{
  "status": "healthy",
  "components": {
    "redis": {"status": "healthy"},
    "postgres": {"status": "healthy"}
  }
}
```

**Verification**: You should see HTTP 200 response with all components showing "healthy" status.

## Step 2: Store Your First Memory

Let's store a simple fact about yourself:

```bash
# Store a personal memory
curl -X POST http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -d '{
    "content": "My favorite programming language is Python because it is readable and has great AI libraries",
    "metadata": {
      "category": "personal_preferences", 
      "topic": "programming",
      "confidence": 0.9,
      "timestamp": "2025-10-15T10:00:00Z"
    }
  }'

# Expected response
{
  "success": true,
  "memory_id": "mem_abc123",
  "message": "Memory stored successfully"
}
```

**Verification**: Response shows `"success": true` and returns a unique memory ID.

## Step 3: Store Related Memories

Add more memories to see how SomaBrain handles relationships:

```bash
# Store a related technical memory
curl -X POST http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -d '{
    "content": "I built a machine learning project using scikit-learn and pandas for data analysis",
    "metadata": {
      "category": "projects",
      "topic": "machine_learning", 
      "skills": ["python", "scikit-learn", "pandas"],
      "date": "2025-09-15"
    }
  }'

# Store a different domain memory  
curl -X POST http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -d '{
    "content": "The best coffee shop in downtown serves excellent Ethiopian beans with notes of blueberry",
    "metadata": {
      "category": "personal_preferences",
      "topic": "coffee",
      "location": "downtown"
    }
  }'
```

**Verification**: Both requests return successful responses with different memory IDs.

## Step 4: Recall Memories with Natural Queries

Now let's retrieve memories using semantic similarity:

```bash
# Query about programming preferences
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What programming languages do you like?",
    "k": 3
  }'

# Expected response
{
  "results": [
    {
      "content": "My favorite programming language is Python because it is readable and has great AI libraries",
      "score": 0.87,
      "metadata": {
        "category": "personal_preferences",
        "topic": "programming"
      }
    },
    {
      "content": "I built a machine learning project using scikit-learn and pandas for data analysis", 
      "score": 0.72,
      "metadata": {
        "category": "projects",
        "topic": "machine_learning"
      }
    }
  ]
}
```

**Key Observation**: SomaBrain found related memories even though your query didn't use exact words like "Python" or "favorite".

## Step 5: Try Different Query Types

Experiment with various query patterns:

```bash
# Technical skill query
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning experience",
    "k": 2
  }'

# Location-based query
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{
    "query": "good coffee recommendations",
    "k": 1
  }'

# Broad category query
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{
    "query": "personal preferences and interests", 
    "k": 5
  }'
```

**Verification**: Each query returns relevant memories ranked by semantic similarity score (0.0-1.0).

## Step 6: Understand Memory Scoring

SomaBrain ranks memories using multiple factors:

```bash
# Query with detailed results
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{
    "query": "python programming", 
    "k": 3,
    "include_scores": true
  }'
```

**Score Components**:
- **Cosine Similarity** (0.6 weight): Semantic meaning similarity
- **Recency** (0.15 weight): How recently the memory was stored/accessed
- **Frequency Directions** (0.25 weight): Diversity to avoid repetitive results

## Step 7: Memory Metadata Filtering

Use metadata to filter results:

```bash
# Filter by category
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{
    "query": "preferences",
    "k": 5,
    "filters": {
      "category": "personal_preferences"
    }
  }'

# Filter by topic and date range
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{
    "query": "recent projects",
    "k": 3,
    "filters": {
      "topic": "machine_learning",
      "date_after": "2025-09-01"
    }
  }'
```

**Verification**: Results only include memories matching both semantic similarity and metadata filters.

## Step 8: Memory Updates and Context

Store a memory that builds on previous context:

```bash
# Store a follow-up memory
curl -X POST http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -d '{
    "content": "After my Python ML project, I want to learn PyTorch for deep learning and computer vision",
    "metadata": {
      "category": "learning_goals",
      "topic": "deep_learning",
      "relates_to": "machine_learning",
      "priority": "high"
    }
  }'

# Query about future plans
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What do you want to learn next?",
    "k": 2
  }'
```

**Key Learning**: SomaBrain understands contextual relationships between memories across time.

---

## What You've Learned

✅ **Memory Storage**: Use `/remember` endpoint with content and structured metadata  
✅ **Semantic Recall**: Query with natural language using `/recall` endpoint  
✅ **Similarity Scoring**: Understand how SomaBrain ranks memory relevance  
✅ **Metadata Filtering**: Combine semantic search with structured filters  
✅ **Contextual Memory**: Build interconnected memories that reference each other  

## Key Differences from Traditional Databases

| Traditional Database | SomaBrain Cognitive Memory |
|---------------------|---------------------------|
| Exact keyword matching | Semantic similarity matching |
| Manual indexing required | Automatic semantic encoding |
| Boolean search queries | Natural language queries |
| Static relationships | Dynamic contextual relationships |
| Schema-dependent | Flexible metadata structure |

## Common Patterns You Can Use

### 1. Personal Knowledge Base
```json
{
  "content": "Learned that Redis persistence works with both RDB snapshots and AOF logs",
  "metadata": {
    "category": "technical_learning",
    "technology": "redis", 
    "source": "documentation",
    "date": "2025-10-15"
  }
}
```

### 2. Project Documentation
```json
{
  "content": "API endpoint /users/{id}/preferences handles user customization settings with JSON schema validation",
  "metadata": {
    "category": "project_docs",
    "project": "user_service",
    "component": "api",
    "status": "implemented"
  }
}
```

### 3. Decision Records
```json
{
  "content": "Chose PostgreSQL over MongoDB for user data because we need ACID transactions and complex queries",
  "metadata": {
    "category": "architectural_decisions", 
    "decision_id": "ADR-001",
    "status": "accepted",
    "date": "2025-10-01"
  }
}
```

---

## Next Steps

Now that you understand basic memory operations:

1. **Explore Advanced Features**: Read the [Memory Operations Guide](features/memory-operations.md)
2. **API Integration**: See [API Integration Guide](features/api-integration.md) for application development
3. **Multi-tenant Usage**: Learn about [tenant isolation](features/multi-tenant-usage.md) for multiple users
4. **Cognitive Reasoning**: Discover [planning capabilities](features/cognitive-reasoning.md) for complex queries

## Troubleshooting

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Connection refused | `curl` fails with connection error | Verify SomaBrain is running: `docker compose ps` |
| Empty results | Recall returns no memories | Check if memories were stored successfully, try broader queries |
| Low similarity scores | All scores < 0.3 | Use more descriptive content, add relevant metadata |
| Slow responses | Requests take >5 seconds | Check system resources, consider scaling Redis/PostgreSQL |

**Common Errors**: See [FAQ](faq.md) for additional troubleshooting help.

**References**:
- [Installation Guide](installation.md) for setup instructions
- [Memory Operations](features/memory-operations.md) for detailed API reference
- [API Integration](features/api-integration.md) for development patterns
- [Technical Architecture](../technical-manual/architecture.md) for system understanding