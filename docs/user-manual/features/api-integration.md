# API Integration Guide

**Purpose**: Comprehensive guide for developers integrating SomaBrain cognitive memory capabilities into applications and services.

**Audience**: Software developers, system integrators, and technical architects building applications with SomaBrain.

**Prerequisites**: Basic understanding of REST APIs and [Memory Operations](memory-operations.md).

---

## API Overview

SomaBrain provides a RESTful API that enables cognitive memory operations through standard HTTP requests:

### Base Configuration

**Base URL**: `http://localhost:9696` (default development)
**API Version**: `v1` (current stable)
**Content Type**: `application/json`
**Authentication**: API Key or JWT tokens

### Core Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Service health check |
| `/remember` | POST | Store new memories |
| `/recall` | POST | Retrieve memories by query |
| `/reason` | POST | Cognitive reasoning operations |
| `/memories/{id}` | GET/PUT/DELETE | Memory management |
| `/export` | GET | Data export operations |
| `/metrics` | GET | Performance metrics |

### Authentication Setup

Configure authentication for production use:

```bash
# API Key Authentication (Recommended)
curl -H "X-API-Key: your-api-key-here" \
     -H "X-Tenant-ID: your-tenant-id" \
     http://localhost:9696/health

# JWT Token Authentication
curl -H "Authorization: Bearer your-jwt-token" \
     -H "X-Tenant-ID: your-tenant-id" \
     http://localhost:9696/health
```

**Environment Configuration**:
```bash
# Set in docker-compose.yml or environment
export SOMABRAIN_API_KEY="your-secure-api-key"
export SOMABRAIN_AUTH_MODE="api_key"  # or "jwt"
export SOMABRAIN_TENANT_MODE="multi"  # or "single"
```

---

## Python Integration

### Official Python SDK

Install the official SomaBrain Python client:

```bash
pip install somabrain-client
```

### Basic Python Usage

```python
from somabrain import SomaBrainClient, MemoryMetadata
import asyncio

# Initialize client
client = SomaBrainClient(
    base_url="http://localhost:9696",
    tenant_id="your_tenant",
    api_key="your_api_key",
    timeout=30
)

async def main():
    # Store a memory
    memory_id = await client.remember(
        content="FastAPI provides automatic OpenAPI documentation generation",
        metadata=MemoryMetadata(
            category="technical_knowledge",
            topic="web_frameworks",
            technology="fastapi",
            confidence=0.95,
            tags=["python", "api", "documentation"]
        )
    )

    print(f"Stored memory: {memory_id}")

    # Recall memories
    results = await client.recall(
        query="How to generate API documentation?",
        k=5,
        filters={"technology": "fastapi"},
        threshold=0.3
    )

    for result in results:
        print(f"Score: {result.score:.3f}")
        print(f"Content: {result.content}")
        print(f"Metadata: {result.metadata}")
        print("---")

# Run async operations
asyncio.run(main())
```

### Advanced Python Patterns

#### Batch Operations with Error Handling

```python
import asyncio
from typing import List, Dict, Any
from somabrain import SomaBrainClient, BatchMemoryRequest

class MemoryManager:
    def __init__(self, client: SomaBrainClient):
        self.client = client

    async def store_knowledge_base(self, knowledge_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store multiple knowledge items with error handling"""

        batch_requests = []
        for item in knowledge_items:
            batch_requests.append(
                BatchMemoryRequest(
                    content=item["content"],
                    metadata=item["metadata"]
                )
            )

        try:
            # Store in batches of 50 for optimal performance
            batch_size = 50
            results = {"success": [], "failed": []}

            for i in range(0, len(batch_requests), batch_size):
                batch = batch_requests[i:i+batch_size]

                try:
                    batch_result = await self.client.remember_batch(batch)
                    results["success"].extend(batch_result.memory_ids)

                except Exception as e:
                    # Handle individual failures
                    for req in batch:
                        results["failed"].append({
                            "content": req.content[:50] + "...",
                            "error": str(e)
                        })

            return results

        except Exception as e:
            raise Exception(f"Batch storage failed: {e}")

    async def semantic_search_with_fallback(self, query: str, **kwargs) -> List[Any]:
        """Semantic search with automatic fallback strategies"""

        # Try primary search
        try:
            results = await self.client.recall(query, **kwargs)
            if results:
                return results
        except Exception as e:
            print(f"Primary search failed: {e}")

        # Fallback 1: Broader search with lower threshold
        try:
            fallback_kwargs = {**kwargs, "threshold": 0.1, "k": kwargs.get("k", 10) * 2}
            results = await self.client.recall(query, **fallback_kwargs)
            if results:
                return results[:kwargs.get("k", 10)]
        except Exception as e:
            print(f"Fallback search failed: {e}")

        # Fallback 2: Keyword-based search
        try:
            keywords = query.split()[:3]  # Use first 3 words
            for keyword in keywords:
                results = await self.client.recall(keyword, **kwargs)
                if results:
                    return results
        except Exception as e:
            print(f"Keyword fallback failed: {e}")

        return []
```

#### Context-Aware Memory Operations

```python
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

class ContextualMemorySession:
    def __init__(self, client: SomaBrainClient, session_id: str):
        self.client = client
        self.session_id = session_id
        self.context_memories = []

    @asynccontextmanager
    async def conversation_context(self):
        """Manage conversational context across multiple operations"""
        try:
            yield self
        finally:
            # Clean up session context
            await self._cleanup_session()

    async def remember_with_context(self, content: str, metadata: dict = None):
        """Store memory with current conversation context"""

        # Enhance metadata with context
        enhanced_metadata = {
            **(metadata or {}),
            "session_id": self.session_id,
            "context_memories": [m.id for m in self.context_memories[-5:]],  # Last 5
            "conversation_turn": len(self.context_memories) + 1,
            "timestamp": datetime.now().isoformat()
        }

        memory_id = await self.client.remember(content, enhanced_metadata)

        # Add to context tracking
        self.context_memories.append(
            type('Memory', (), {'id': memory_id, 'content': content})()
        )

        return memory_id

    async def recall_with_context(self, query: str, **kwargs):
        """Recall memories considering current conversation context"""

        # Build context-aware query
        if self.context_memories:
            recent_context = " ".join([
                m.content for m in self.context_memories[-3:]  # Last 3 memories
            ])
            contextual_query = f"{query}. Recent context: {recent_context}"
        else:
            contextual_query = query

        # Add session filtering
        filters = kwargs.get("filters", {})
        filters["session_id"] = self.session_id

        return await self.client.recall(
            contextual_query,
            filters=filters,
            **{k: v for k, v in kwargs.items() if k != "filters"}
        )

# Usage example
async def conversational_ai_example():
    client = SomaBrainClient(base_url="http://localhost:9696", tenant_id="ai_bot")

    async with ContextualMemorySession(client, "conv_123").conversation_context() as session:
        # Store conversation memories with context
        await session.remember_with_context(
            "User asked about database performance optimization",
            {"intent": "technical_question", "domain": "databases"}
        )

        # Later in conversation - context-aware recall
        results = await session.recall_with_context(
            "What did we discuss about optimization?"
        )
```

---

## JavaScript/Node.js Integration

### Official JavaScript SDK

```bash
npm install @somabrain/client
```

### TypeScript Interface Definitions

```typescript
// types/somabrain.d.ts
export interface MemoryMetadata {
  category?: string;
  topic?: string;
  confidence?: number;
  tags?: string[];
  [key: string]: any;
}

export interface Memory {
  id: string;
  content: string;
  metadata: MemoryMetadata;
  created_at: string;
  updated_at: string;
}

export interface RecallResult {
  memory_id: string;
  content: string;
  score: number;
  metadata: MemoryMetadata;
  explanation?: string;
}

export interface ReasoningResult {
  conclusion: string;
  confidence: number;
  reasoning_path: ReasoningStep[];
  supporting_memories: string[];
}

export interface ReasoningStep {
  step: number;
  type: string;
  observation: string;
  supporting_memories: string[];
}
```

### JavaScript/Node.js Usage

```javascript
import { SomaBrainClient } from '@somabrain/client';

class KnowledgeBot {
  constructor(config) {
    this.client = new SomaBrainClient({
      baseUrl: config.baseUrl || 'http://localhost:9696',
      tenantId: config.tenantId,
      apiKey: config.apiKey,
      timeout: config.timeout || 30000
    });
  }

  // Store user interactions as memories
  async recordInteraction(userId, message, metadata = {}) {
    try {
      const memoryId = await this.client.remember({
        content: message,
        metadata: {
          ...metadata,
          user_id: userId,
          interaction_type: 'user_message',
          timestamp: new Date().toISOString()
        }
      });

      console.log(`Recorded interaction: ${memoryId}`);
      return memoryId;

    } catch (error) {
      console.error('Failed to record interaction:', error);
      throw error;
    }
  }

  // Generate contextual responses
  async generateResponse(userId, query) {
    try {
      // First, recall relevant memories
      const memories = await this.client.recall({
        query: query,
        k: 5,
        filters: {
          user_id: userId
        },
        threshold: 0.4
      });

      if (memories.length === 0) {
        return {
          response: "I don't have relevant information about that topic.",
          confidence: 0.1
        };
      }

      // Use cognitive reasoning for complex queries
      if (query.includes('how') || query.includes('why') || query.includes('what if')) {
        const reasoning = await this.client.reason({
          query: query,
          reasoning_mode: 'contextual_inference',
          context_memories: memories.map(m => m.memory_id)
        });

        return {
          response: reasoning.conclusion,
          confidence: reasoning.confidence,
          reasoning_path: reasoning.reasoning_path
        };
      }

      // Simple response from top memory
      const topResult = memories[0];
      return {
        response: topResult.content,
        confidence: topResult.score,
        source_memory: topResult.memory_id
      };

    } catch (error) {
      console.error('Failed to generate response:', error);
      return {
        response: "I encountered an error processing your request.",
        confidence: 0.0,
        error: error.message
      };
    }
  }

  // Batch learning from documents
  async learnFromDocuments(documents) {
    const batchSize = 25;
    const results = { success: 0, failed: 0, errors: [] };

    for (let i = 0; i < documents.length; i += batchSize) {
      const batch = documents.slice(i, i + batchSize);

      try {
        const batchResult = await this.client.rememberBatch(
          batch.map(doc => ({
            content: doc.content,
            metadata: {
              ...doc.metadata,
              source: 'document_batch',
              batch_id: Math.floor(i / batchSize),
              learned_at: new Date().toISOString()
            }
          }))
        );

        results.success += batchResult.stored_count;

      } catch (error) {
        results.failed += batch.length;
        results.errors.push({
          batch: Math.floor(i / batchSize),
          error: error.message
        });
      }
    }

    return results;
  }

  // Real-time memory streaming
  async *streamMemories(query, options = {}) {
    const pageSize = options.pageSize || 10;
    let offset = 0;
    let hasMore = true;

    while (hasMore) {
      try {
        const results = await this.client.recall({
          query: query,
          k: pageSize,
          offset: offset,
          ...options
        });

        for (const result of results) {
          yield result;
        }

        hasMore = results.length === pageSize;
        offset += pageSize;

      } catch (error) {
        console.error('Stream error:', error);
        break;
      }
    }
  }
}

// Usage example
const bot = new KnowledgeBot({
  baseUrl: 'http://localhost:9696',
  tenantId: 'chatbot_v1',
  apiKey: process.env.SOMABRAIN_API_KEY
});

// Example: Chat bot with memory
async function handleUserMessage(userId, message) {
  // Record the user's message
  await bot.recordInteraction(userId, message, {
    intent: 'user_query',
    channel: 'web_chat'
  });

  // Generate and return response
  const response = await bot.generateResponse(userId, message);

  // Record the bot's response
  await bot.recordInteraction('bot', response.response, {
    intent: 'bot_response',
    confidence: response.confidence,
    channel: 'web_chat'
  });

  return response;
}
```

### Express.js API Integration

```javascript
import express from 'express';
import { SomaBrainClient } from '@somabrain/client';

const app = express();
app.use(express.json());

const somabrain = new SomaBrainClient({
  baseUrl: process.env.SOMABRAIN_URL,
  tenantId: process.env.TENANT_ID,
  apiKey: process.env.SOMABRAIN_API_KEY
});

// Memory storage endpoint
app.post('/api/memories', async (req, res) => {
  try {
    const { content, metadata } = req.body;

    // Validate request
    if (!content || content.length < 5) {
      return res.status(400).json({
        error: 'Content must be at least 5 characters long'
      });
    }

    // Store memory
    const memoryId = await somabrain.remember({
      content,
      metadata: {
        ...metadata,
        api_source: true,
        created_via: 'rest_api',
        user_agent: req.get('User-Agent')
      }
    });

    res.status(201).json({
      success: true,
      memory_id: memoryId,
      message: 'Memory stored successfully'
    });

  } catch (error) {
    console.error('Memory storage error:', error);
    res.status(500).json({
      error: 'Failed to store memory',
      details: error.message
    });
  }
});

// Memory search endpoint
app.post('/api/search', async (req, res) => {
  try {
    const { query, filters = {}, k = 10 } = req.body;

    if (!query) {
      return res.status(400).json({
        error: 'Query parameter is required'
      });
    }

    const results = await somabrain.recall({
      query,
      filters,
      k: Math.min(k, 50), // Limit to prevent abuse
      threshold: 0.2
    });

    res.json({
      success: true,
      results: results.map(result => ({
        content: result.content,
        score: result.score,
        metadata: result.metadata,
        memory_id: result.memory_id
      })),
      count: results.length
    });

  } catch (error) {
    console.error('Search error:', error);
    res.status(500).json({
      error: 'Search failed',
      details: error.message
    });
  }
});

// Reasoning endpoint
app.post('/api/reason', async (req, res) => {
  try {
    const { query, reasoning_mode = 'contextual_inference' } = req.body;

    const reasoning = await somabrain.reason({
      query,
      reasoning_mode,
      include_reasoning_path: true
    });

    res.json({
      success: true,
      conclusion: reasoning.conclusion,
      confidence: reasoning.confidence,
      reasoning_path: reasoning.reasoning_path
    });

  } catch (error) {
    console.error('Reasoning error:', error);
    res.status(500).json({
      error: 'Reasoning failed',
      details: error.message
    });
  }
});

app.listen(3000, () => {
  console.log('API server running on port 3000');
});
```

---

## Java Integration

### Maven Dependencies

```xml
<!-- pom.xml -->
<dependency>
    <groupId>com.somabrain</groupId>
    <artifactId>somabrain-client</artifactId>
    <version>1.0.0</version>
</dependency>

<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
    <version>2.15.2</version>
</dependency>
```

### Java Client Implementation

```java
package com.example.somabrain;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.URI;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

public class SomaBrainClient {
    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    private final String baseUrl;
    private final String tenantId;
    private final String apiKey;

    public SomaBrainClient(String baseUrl, String tenantId, String apiKey) {
        this.httpClient = HttpClient.newHttpClient();
        this.objectMapper = new ObjectMapper();
        this.baseUrl = baseUrl;
        this.tenantId = tenantId;
        this.apiKey = apiKey;
    }

    public CompletableFuture<String> remember(String content, Map<String, Object> metadata) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                Map<String, Object> requestBody = Map.of(
                    "content", content,
                    "metadata", metadata
                );

                String requestBodyJson = objectMapper.writeValueAsString(requestBody);

                HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + "/remember"))
                    .header("Content-Type", "application/json")
                    .header("X-Tenant-ID", tenantId)
                    .header("X-API-Key", apiKey)
                    .POST(HttpRequest.BodyPublishers.ofString(requestBodyJson))
                    .build();

                HttpResponse<String> response = httpClient.send(request,
                    HttpResponse.BodyHandlers.ofString());

                if (response.statusCode() != 200) {
                    throw new RuntimeException("Failed to store memory: " + response.body());
                }

                Map<String, Object> responseMap = objectMapper.readValue(
                    response.body(), Map.class);
                return (String) responseMap.get("memory_id");

            } catch (Exception e) {
                throw new RuntimeException("Error storing memory", e);
            }
        });
    }

    public CompletableFuture<List<RecallResult>> recall(String query,
                                                       Map<String, Object> filters,
                                                       int k) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                Map<String, Object> requestBody = Map.of(
                    "query", query,
                    "filters", filters,
                    "k", k
                );

                String requestBodyJson = objectMapper.writeValueAsString(requestBody);

                HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + "/recall"))
                    .header("Content-Type", "application/json")
                    .header("X-Tenant-ID", tenantId)
                    .header("X-API-Key", apiKey)
                    .POST(HttpRequest.BodyPublishers.ofString(requestBodyJson))
                    .build();

                HttpResponse<String> response = httpClient.send(request,
                    HttpResponse.BodyHandlers.ofString());

                if (response.statusCode() != 200) {
                    throw new RuntimeException("Failed to recall memories: " + response.body());
                }

                Map<String, Object> responseMap = objectMapper.readValue(
                    response.body(), Map.class);
                List<Map<String, Object>> results = (List<Map<String, Object>>)
                    responseMap.get("results");

                return results.stream()
                    .map(result -> new RecallResult(
                        (String) result.get("memory_id"),
                        (String) result.get("content"),
                        ((Number) result.get("score")).doubleValue(),
                        (Map<String, Object>) result.get("metadata")
                    ))
                    .toList();

            } catch (Exception e) {
                throw new RuntimeException("Error recalling memories", e);
            }
        });
    }

    public static class RecallResult {
        public final String memoryId;
        public final String content;
        public final double score;
        public final Map<String, Object> metadata;

        public RecallResult(String memoryId, String content, double score,
                          Map<String, Object> metadata) {
            this.memoryId = memoryId;
            this.content = content;
            this.score = score;
            this.metadata = metadata;
        }
    }
}
```

### Spring Boot Integration

```java
@Service
public class KnowledgeService {

    private final SomaBrainClient somaBrainClient;

    public KnowledgeService(@Value("${somabrain.url}") String url,
                          @Value("${somabrain.tenant}") String tenant,
                          @Value("${somabrain.api-key}") String apiKey) {
        this.somaBrainClient = new SomaBrainClient(url, tenant, apiKey);
    }

    @Async
    public CompletableFuture<Void> indexDocument(Document document) {
        Map<String, Object> metadata = Map.of(
            "document_type", document.getType(),
            "source", document.getSource(),
            "created_at", document.getCreatedAt().toString(),
            "tags", document.getTags()
        );

        return somaBrainClient.remember(document.getContent(), metadata)
            .thenRun(() -> log.info("Indexed document: {}", document.getId()));
    }

    public CompletableFuture<SearchResponse> searchKnowledge(SearchRequest request) {
        Map<String, Object> filters = Map.of(
            "document_type", request.getDocumentTypes(),
            "tags", request.getTags()
        );

        return somaBrainClient.recall(request.getQuery(), filters, request.getLimit())
            .thenApply(results -> new SearchResponse(
                results.stream()
                    .map(r -> new SearchResult(r.content, r.score, r.metadata))
                    .collect(Collectors.toList())
            ));
    }
}

@RestController
@RequestMapping("/api/knowledge")
public class KnowledgeController {

    private final KnowledgeService knowledgeService;

    @PostMapping("/search")
    public CompletableFuture<ResponseEntity<SearchResponse>> search(
            @RequestBody SearchRequest request) {

        return knowledgeService.searchKnowledge(request)
            .thenApply(ResponseEntity::ok)
            .exceptionally(ex -> ResponseEntity.status(500)
                .body(SearchResponse.error(ex.getMessage())));
    }
}
```

---

## Go Integration

### Go Client Implementation

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
    "time"
)

type SomaBrainClient struct {
    BaseURL    string
    TenantID   string
    APIKey     string
    HTTPClient *http.Client
}

type MemoryRequest struct {
    Content  string                 `json:"content"`
    Metadata map[string]interface{} `json:"metadata"`
}

type RecallRequest struct {
    Query     string                 `json:"query"`
    Filters   map[string]interface{} `json:"filters,omitempty"`
    K         int                    `json:"k"`
    Threshold float64               `json:"threshold,omitempty"`
}

type RecallResult struct {
    MemoryID string                 `json:"memory_id"`
    Content  string                 `json:"content"`
    Score    float64                `json:"score"`
    Metadata map[string]interface{} `json:"metadata"`
}

type RecallResponse struct {
    Results []RecallResult `json:"results"`
}

func NewSomaBrainClient(baseURL, tenantID, apiKey string) *SomaBrainClient {
    return &SomaBrainClient{
        BaseURL:  baseURL,
        TenantID: tenantID,
        APIKey:   apiKey,
        HTTPClient: &http.Client{
            Timeout: 30 * time.Second,
        },
    }
}

func (c *SomaBrainClient) Remember(content string, metadata map[string]interface{}) (string, error) {
    request := MemoryRequest{
        Content:  content,
        Metadata: metadata,
    }

    requestBody, err := json.Marshal(request)
    if err != nil {
        return "", err
    }

    req, err := http.NewRequest("POST", c.BaseURL+"/remember", bytes.NewBuffer(requestBody))
    if err != nil {
        return "", err
    }

    req.Header.Set("Content-Type", "application/json")
    req.Header.Set("X-Tenant-ID", c.TenantID)
    req.Header.Set("X-API-Key", c.APIKey)

    resp, err := c.HTTPClient.Do(req)
    if err != nil {
        return "", err
    }
    defer resp.Body.Close()

    if resp.StatusCode != http.StatusOK {
        return "", fmt.Errorf("failed to store memory: %s", resp.Status)
    }

    var response map[string]interface{}
    if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
        return "", err
    }

    memoryID, ok := response["memory_id"].(string)
    if !ok {
        return "", fmt.Errorf("invalid response format")
    }

    return memoryID, nil
}

func (c *SomaBrainClient) Recall(query string, filters map[string]interface{}, k int) ([]RecallResult, error) {
    request := RecallRequest{
        Query:   query,
        Filters: filters,
        K:       k,
    }

    requestBody, err := json.Marshal(request)
    if err != nil {
        return nil, err
    }

    req, err := http.NewRequest("POST", c.BaseURL+"/recall", bytes.NewBuffer(requestBody))
    if err != nil {
        return nil, err
    }

    req.Header.Set("Content-Type", "application/json")
    req.Header.Set("X-Tenant-ID", c.TenantID)
    req.Header.Set("X-API-Key", c.APIKey)

    resp, err := c.HTTPClient.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    if resp.StatusCode != http.StatusOK {
        return nil, fmt.Errorf("failed to recall memories: %s", resp.Status)
    }

    var response RecallResponse
    if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
        return nil, err
    }

    return response.Results, nil
}

// Example usage
func main() {
    client := NewSomaBrainClient(
        "http://localhost:9696",
        "go_app",
        "your-api-key",
    )

    // Store a memory
    memoryID, err := client.Remember(
        "Go provides excellent concurrency with goroutines and channels",
        map[string]interface{}{
            "category":   "technical_knowledge",
            "language":   "go",
            "topic":      "concurrency",
            "confidence": 0.9,
        },
    )
    if err != nil {
        panic(err)
    }

    fmt.Printf("Stored memory: %s\n", memoryID)

    // Recall memories
    results, err := client.Recall(
        "How to handle concurrent programming?",
        map[string]interface{}{
            "language": "go",
        },
        5,
    )
    if err != nil {
        panic(err)
    }

    for _, result := range results {
        fmt.Printf("Score: %.3f\n", result.Score)
        fmt.Printf("Content: %s\n", result.Content)
        fmt.Printf("---\n")
    }
}
```

---

## Error Handling Best Practices

### Comprehensive Error Handling

```python
import asyncio
import logging
from enum import Enum
from typing import Optional, Dict, Any

class SomaBrainErrorType(Enum):
    CONNECTION_ERROR = "connection_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT_ERROR = "timeout_error"
    SERVER_ERROR = "server_error"

class SomaBrainException(Exception):
    def __init__(self, error_type: SomaBrainErrorType, message: str, details: Optional[Dict] = None):
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        super().__init__(message)

class ResilientSomaBrainClient:
    def __init__(self, client: SomaBrainClient, max_retries: int = 3):
        self.client = client
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)

    async def remember_with_retry(self, content: str, metadata: Dict[str, Any]) -> str:
        """Store memory with automatic retry and error handling"""

        for attempt in range(self.max_retries + 1):
            try:
                return await self.client.remember(content, metadata)

            except ConnectionError as e:
                if attempt == self.max_retries:
                    raise SomaBrainException(
                        SomaBrainErrorType.CONNECTION_ERROR,
                        f"Failed to connect after {self.max_retries} attempts",
                        {"original_error": str(e)}
                    )

                # Exponential backoff
                wait_time = 2 ** attempt
                self.logger.warning(f"Connection failed, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

            except TimeoutError as e:
                if attempt == self.max_retries:
                    raise SomaBrainException(
                        SomaBrainErrorType.TIMEOUT_ERROR,
                        "Request timeout exceeded maximum retries",
                        {"timeout_duration": str(e)}
                    )

                await asyncio.sleep(1)

            except ValueError as e:
                # Don't retry validation errors
                raise SomaBrainException(
                    SomaBrainErrorType.VALIDATION_ERROR,
                    f"Invalid request format: {e}",
                    {"content_length": len(content), "metadata_keys": list(metadata.keys())}
                )

    async def recall_with_fallback(self, query: str, **kwargs) -> list:
        """Recall with multiple fallback strategies"""

        strategies = [
            # Primary strategy
            lambda: self.client.recall(query, **kwargs),

            # Fallback 1: Lower threshold
            lambda: self.client.recall(query, **{**kwargs, "threshold": 0.1}),

            # Fallback 2: Broader search
            lambda: self.client.recall(query, **{**kwargs, "k": kwargs.get("k", 10) * 2, "threshold": 0.1}),

            # Fallback 3: Keyword search
            lambda: self._keyword_fallback(query, **kwargs)
        ]

        for i, strategy in enumerate(strategies):
            try:
                results = await strategy()
                if results:
                    if i > 0:
                        self.logger.info(f"Fallback strategy {i} succeeded")
                    return results

            except Exception as e:
                self.logger.warning(f"Strategy {i} failed: {e}")
                if i == len(strategies) - 1:  # Last strategy
                    raise SomaBrainException(
                        SomaBrainErrorType.SERVER_ERROR,
                        "All recall strategies failed",
                        {"last_error": str(e)}
                    )

        return []

    async def _keyword_fallback(self, query: str, **kwargs):
        """Extract keywords and search individually"""
        keywords = query.lower().split()[:5]  # First 5 words

        for keyword in keywords:
            try:
                results = await self.client.recall(keyword, **kwargs)
                if results:
                    return results
            except Exception:
                continue

        return []
```

### HTTP Status Code Handling

```python
class APIErrorHandler:
    @staticmethod
    def handle_http_error(status_code: int, response_body: str) -> SomaBrainException:
        """Convert HTTP status codes to appropriate exceptions"""

        error_mappings = {
            400: (SomaBrainErrorType.VALIDATION_ERROR, "Bad request - check input format"),
            401: (SomaBrainErrorType.AUTHENTICATION_ERROR, "Authentication failed - check API key"),
            403: (SomaBrainErrorType.AUTHENTICATION_ERROR, "Access forbidden - check tenant permissions"),
            429: (SomaBrainErrorType.RATE_LIMIT_ERROR, "Rate limit exceeded - implement backoff"),
            500: (SomaBrainErrorType.SERVER_ERROR, "Internal server error"),
            503: (SomaBrainErrorType.CONNECTION_ERROR, "Service unavailable - try again later"),
            504: (SomaBrainErrorType.TIMEOUT_ERROR, "Gateway timeout - request took too long")
        }

        error_type, default_message = error_mappings.get(
            status_code,
            (SomaBrainErrorType.SERVER_ERROR, f"Unexpected HTTP status: {status_code}")
        )

        # Try to extract error details from response
        details = {"status_code": status_code, "raw_response": response_body}
        try:
            response_json = json.loads(response_body)
            details.update(response_json)
            message = response_json.get("message", default_message)
        except:
            message = default_message

        return SomaBrainException(error_type, message, details)
```

---

## Performance Optimization

### Connection Pooling and Caching

```python
import aiohttp
import asyncio
from functools import lru_cache
from typing import Dict, Any

class OptimizedSomaBrainClient:
    def __init__(self, base_url: str, tenant_id: str, api_key: str):
        self.base_url = base_url
        self.tenant_id = tenant_id
        self.api_key = api_key
        self.session = None
        self._memory_cache = {}
        self._query_cache = {}

    async def __aenter__(self):
        # Connection pooling configuration
        connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=30,  # Connections per host
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
        )

        timeout = aiohttp.ClientTimeout(
            total=30,  # Total timeout
            connect=5,  # Connection timeout
            sock_read=10  # Socket read timeout
        )

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "X-Tenant-ID": self.tenant_id,
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    @lru_cache(maxsize=1000)
    def _cache_key(self, query: str, filters: str, k: int) -> str:
        """Generate cache key for queries"""
        return f"{query}:{filters}:{k}"

    async def recall_cached(self, query: str, filters: Dict[str, Any] = None, k: int = 10, cache_ttl: int = 300):
        """Recall with local caching to reduce API calls"""

        filters_str = json.dumps(filters or {}, sort_keys=True)
        cache_key = self._cache_key(query, filters_str, k)

        # Check cache
        if cache_key in self._query_cache:
            cached_result, timestamp = self._query_cache[cache_key]
            if time.time() - timestamp < cache_ttl:
                return cached_result

        # Make API call
        result = await self._make_recall_request(query, filters, k)

        # Cache result
        self._query_cache[cache_key] = (result, time.time())

        # Clean old cache entries (simple LRU)
        if len(self._query_cache) > 10000:
            oldest_key = min(self._query_cache.keys(),
                           key=lambda k: self._query_cache[k][1])
            del self._query_cache[oldest_key]

        return result

    async def batch_remember_optimized(self, memories: list, batch_size: int = 50):
        """Optimized batch memory storage with concurrent requests"""

        # Process in batches concurrently
        batches = [memories[i:i+batch_size] for i in range(0, len(memories), batch_size)]

        async def process_batch(batch):
            return await self._make_batch_remember_request(batch)

        # Limit concurrent batches to avoid overwhelming the server
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent batches

        async def bounded_process(batch):
            async with semaphore:
                return await process_batch(batch)

        results = await asyncio.gather(
            *[bounded_process(batch) for batch in batches],
            return_exceptions=True
        )

        # Aggregate results
        success_count = 0
        failed_count = 0
        errors = []

        for result in results:
            if isinstance(result, Exception):
                failed_count += batch_size
                errors.append(str(result))
            else:
                success_count += len(result.get("memory_ids", []))

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors
        }
```

### Request Compression and Streaming

```javascript
import zlib from 'zlib';
import { pipeline } from 'stream/promises';

class StreamingSomaBrainClient extends SomaBrainClient {

  // Stream large recall results
  async *streamRecall(query, options = {}) {
    const pageSize = options.pageSize || 50;
    let offset = 0;
    let hasMore = true;

    while (hasMore) {
      const results = await this.recall({
        ...options,
        query,
        offset,
        k: pageSize
      });

      for (const result of results) {
        yield result;
      }

      hasMore = results.length === pageSize;
      offset += pageSize;

      // Rate limiting
      if (options.rateLimitMs) {
        await new Promise(resolve => setTimeout(resolve, options.rateLimitMs));
      }
    }
  }

  // Compressed batch operations for large datasets
  async rememberBatchCompressed(memories) {
    const batchData = JSON.stringify({ memories });

    // Compress request body
    const compressed = await new Promise((resolve, reject) => {
      zlib.gzip(batchData, (err, result) => {
        if (err) reject(err);
        else resolve(result);
      });
    });

    const response = await fetch(`${this.baseUrl}/remember/batch`, {
      method: 'POST',
      headers: {
        ...this.headers,
        'Content-Encoding': 'gzip',
        'Content-Type': 'application/json'
      },
      body: compressed
    });

    return await response.json();
  }
}
```

---

**Common Errors**: See [FAQ](../faq.md) for API integration troubleshooting.

**References**:
- [Memory Operations Guide](memory-operations.md) for core memory concepts
- [Cognitive Reasoning Guide](cognitive-reasoning.md) for advanced reasoning APIs
- [Multi-Tenant Usage](multi-tenant-usage.md) for tenant management
- [Technical Manual - API Reference](../../technical-manual/architecture.md#api-architecture) for detailed API specifications