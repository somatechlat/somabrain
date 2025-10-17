# Quick Start Tutorial

**Purpose**: A guided walkthrough of a core SomaBrain workflow to help you achieve your first success quickly.

**Audience**: New users of SomaBrain.

**Prerequisites**: SomaBrain is installed and running. See the [Installation Guide](installation.md).

---

## 💡 Try SomaBrain in 3 Simple Steps

This tutorial will guide you through storing a memory and then recalling it using a semantic search query.

### Step 1: Store a Memory

Open your terminal and use `curl` to send a `POST` request to the `/remember` endpoint. This will store a piece of information in SomaBrain's memory.

```bash
curl -X POST "http://localhost:9696/remember" \
     -H "Content-Type: application/json" \
     -d '{
        "coord": null,
        "payload": {
            "content": "Paris is the capital of France",
            "task": "geography-knowledge",
            "phase": "general"
        }
    }'
```

You should receive a response confirming that the memory has been stored.

### Step 2: Intelligent Recall with Cognitive Scoring

Now, let's retrieve the memory we just stored. We'll use a query that is semantically similar, but not identical, to the stored content. This demonstrates SomaBrain's ability to understand meaning.

```bash
curl -X POST "http://localhost:9696/recall" \
     -H "Content-Type: application/json" \
     -d '{
        "query": "capital of France",
        "top_k": 5
    }'
```

### Step 3: Get Cognitive Insights

The response from the `/recall` endpoint will be a JSON object containing the retrieved memories, along with a similarity score.

Example Response:
```json
{
  "results": [
    {
      "memory_id": "mem_some_unique_id",
      "content": "Paris is the capital of France",
      "similarity_score": 0.95,
      "metadata": {
        "task": "geography-knowledge",
        "phase": "general"
      }
    }
  ]
}
```

Notice that even though we searched for "capital of France", SomaBrain correctly identified "Paris is the capital of France" as the most relevant memory. This is the power of cognitive memory!

---

Congratulations! You have successfully stored and recalled your first memory with SomaBrain. You are now ready to explore more advanced features.