# SRS-05: Memory Management System

**Document Version:** 2.0.0  
**Date:** 2025-12-24  
**Standard:** ISO/IEC/IEEE 29148:2018 Compatible  
**Module:** Memory Management Subsystem

---

## 1. Overview

SomaBrain provides a **memory storage and retrieval system** for AI agents. Agents use SomaBrain as their memory backend, similar to how applications use databases.

### 1.1 Scope

| Component | Description |
|-----------|-------------|
| ShortTermCache | Fast, capacity-limited buffer |
| LongTermStore | Persistent vector storage |
| SalienceScorer | Priority scoring algorithm |
| ConsolidationService | Background data optimization |

---

## 2. Memory Architecture UML Class Diagram

```mermaid
classDiagram
    class ShortTermCache {
        -int capacity
        -int dimension
        -List~CacheItem~ items
        -CachePersister persister
        +admit(item_id, vector, payload)
        +query(query_vec, top_k) List
        +get_priority(query_vec) float
    }
    
    class CacheItem {
        +ndarray vector
        +dict payload
        +int tick
        +float created_at
        +float priority_score
        +str item_id
    }
    
    class LongTermStore {
        -StoreConfig cfg
        -Dict buffers
        +store(payload, tenant_id)
        +optimize(tenant_id) dict
    }
    
    class StoreConfig {
        +str tenant
        +int buffer_max
        +int batch_size
        +int max_summaries
    }
    
    class SalienceScorer {
        -ScorerConfig cfg
        +score(novelty, error) float
        +should_store(score) bool
    }
    
    class ScorerConfig {
        +float novelty_weight
        +float error_weight
        +float store_threshold
        +float hysteresis
    }
    
    ShortTermCache --> CacheItem : contains
    LongTermStore --> StoreConfig : configured_by
    SalienceScorer --> ScorerConfig : configured_by
```

---

## 3. Memory Lifecycle Flowchart

```mermaid
flowchart TD
    subgraph Input["Memory Input"]
        A[New Data] --> B{Priority Check}
        B -->|Low Priority| C[Discard]
        B -->|High Priority| D[Admit to Cache]
    end
    
    subgraph Cache["Short-Term Cache (Capacity Limited)"]
        D --> E{Cache Full?}
        E -->|No| F[Store in Cache]
        E -->|Yes| G[Find Lowest Priority]
        G --> H[Evict Lowest]
        H --> F
        F --> I{Duplicate Check}
        I -->|Exists sim > 0.95| J[Update Existing]
        I -->|New| K[Add New Item]
    end
    
    subgraph Optimization["Background Optimization"]
        L[Scheduled Job] --> M[Select Top-K Items]
        M --> N[Summarize Related Data]
        N --> O[Store to LongTermStore]
    end
    
    subgraph LongTerm["Long-Term Store"]
        J --> S[Persist to SomaFractalMemory]
        K --> T{Promotion Check}
        T -->|Priority >= threshold| S
        T -->|Below threshold| U[Remain in Cache]
    end
    
    subgraph Query["Memory Query"]
        V[Query Vector] --> W[Search LongTermStore]
        W --> X[Search Cache]
        X --> Y[Merge Results]
        Y --> Z[Return Top-K]
    end
```

---

## 4. Store Sequence Diagram

```mermaid
sequenceDiagram
    participant Agent as Agent (API Client)
    participant API as SomaBrain API
    participant Scorer as SalienceScorer
    participant Cache as ShortTermCache
    participant LTS as LongTermStore
    
    Agent->>API: POST /api/memory/remember
    API->>Scorer: Calculate Priority
    Scorer-->>API: priority_score
    
    alt Priority > threshold
        API->>Cache: admit(vector, payload)
        Cache->>Cache: Check Capacity
        Cache->>Cache: Evict if Full
        Cache-->>API: item_id
        
        alt Priority >= promotion_threshold
            Cache->>LTS: Promote to LongTerm
        end
    else Priority <= threshold
        API-->>Agent: Discarded (low priority)
    end
    
    API-->>Agent: {success: true, id: "..."}
```

---

## 5. SomaBrain ↔ SomaFractalMemory Integration

```mermaid
flowchart LR
    subgraph SomaBrain["SomaBrain (Port 9696)"]
        Cache[ShortTermCache]
        LTS[LongTermStore]
        Scorer[SalienceScorer]
    end
    
    subgraph SomaFractalMemory["SomaFractalMemory (Port 9595)"]
        Graph[Graph Store]
        Vector[Vector Index]
    end
    
    Cache -->|"promote()"| Graph
    LTS -->|"persist()"| Graph
    LTS -->|"index()"| Vector
    
    Graph -->|"query()"| Cache
    Vector -->|"similarity_search()"| Cache
```

---

## 6. Functional Requirements

| REQ-ID | Requirement | Priority | Status | Implementation |
|--------|-------------|----------|--------|----------------|
| REQ-MEM-001 | Short-term cache with configurable capacity | HIGH | ✅ EXISTS | `ShortTermCache` |
| REQ-MEM-002 | Priority-based eviction when cache full | HIGH | ✅ EXISTS | `eviction.py` |
| REQ-MEM-003 | Duplicate detection (similarity > 0.95) | HIGH | ✅ EXISTS | `_find_duplicate()` |
| REQ-MEM-004 | Cache → LongTerm promotion | HIGH | ✅ EXISTS | `promotion.py` |
| REQ-MEM-005 | Background data optimization | MEDIUM | ✅ EXISTS | `ConsolidationService` |
| REQ-MEM-006 | Per-tenant data isolation | CRITICAL | ✅ EXISTS | All ops take tenant_id |
| REQ-MEM-007 | Vector normalization (unit-norm) | HIGH | ✅ EXISTS | Dimension enforcement |
| REQ-MEM-008 | Cache persistence to disk | MEDIUM | ✅ EXISTS | `CachePersister` |

---

## 7. Key Files

| File | Purpose | Lines |
|------|---------|-------|
| [wm.py](file:///Users/macbookpro201916i964gb1tb/Documents/GitHub/somabrain/somabrain/wm.py) | Short-term cache | 546 |
| [memory/](file:///Users/macbookpro201916i964gb1tb/Documents/GitHub/somabrain/somabrain/memory/) | Memory subsystem (22 files) | ~150k |

---

*SomaBrain: Memory System for AI Agents*
