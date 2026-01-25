# SRS-09: Unified Memory Platform Architecture

**Document Version:** 1.0.0  
**Date:** 2025-12-24  
**Standard:** ISO/IEC/IEEE 29148:2018 Compatible  
**Module:** Unified SomaBrain + SomaFractalMemory Platform

---

## 1. Overview

The SomaBrain AAAS Platform consists of **two microservices** that work together to provide complete memory management for AI agents:

| Service | Port | Purpose |
|---------|------|---------|
| **SomaBrain** | 9696 | Short-term cache, API gateway, tenant management |
| **SomaFractalMemory** | 9595 | Long-term storage, graph database, vector search |

---

## 2. Unified Architecture Diagram

```mermaid
flowchart TB
    subgraph UI["SomaBrain AAAS UI (Lit Components)"]
        D[Dashboard]
        T[Tenants]
        M[Memory Admin]
        S[Settings]
    end
    
    subgraph SomaBrain["SomaBrain (Port 9696)"]
        API[Django Ninja API]
        STC[ShortTermCache]
        TM[TenantManager]
        QM[QuotaManager]
        Auth[JWT Auth]
    end
    
    subgraph SomaFractalMemory["SomaFractalMemory (Port 9595)"]
        FAPI[Django Ninja API]
        LTS[Memory Model]
        Graph[GraphLink Model]
        Search[Vector Search]
    end
    
    subgraph Storage["Shared Storage Layer"]
        PG[(PostgreSQL)]
        Redis[(Redis)]
        Milvus[(Milvus)]
    end
    
    UI --> SomaBrain
    SomaBrain --> SomaFractalMemory
    SomaBrain --> Storage
    SomaFractalMemory --> Storage
```

---

## 3. Service Integration UML

```mermaid
classDiagram
    class SomaBrainAPI {
        +remember(content, tenant_id)
        +recall(query, tenant_id)
        +delete(id, tenant_id)
        +get_stats(tenant_id)
    }
    
    class ShortTermCache {
        +admit(item)
        +query(vector)
        +evict_lowest()
        +promote_to_ltm()
    }
    
    class SomaFractalMemoryAPI {
        +store_memory(coord, payload)
        +retrieve_memory(coord)
        +delete_memory(coord)
        +create_link(from, to)
        +find_neighbors(coord)
        +vector_search(query)
    }
    
    class MemoryModel {
        +UUID id
        +Float[] coordinate
        +JSONB payload
        +String memory_type
        +Float importance
        +String tenant
    }
    
    class GraphLinkModel {
        +UUID id
        +Float[] from_coordinate
        +Float[] to_coordinate
        +String link_type
        +Float strength
        +String tenant
    }
    
    SomaBrainAPI --> ShortTermCache : uses
    SomaBrainAPI --> SomaFractalMemoryAPI : promotes to
    SomaFractalMemoryAPI --> MemoryModel : persists
    SomaFractalMemoryAPI --> GraphLinkModel : creates
```

---

## 4. Data Flow Sequence

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant SB as SomaBrain:9696
    participant STC as ShortTermCache
    participant SFM as SomaFractalMemory:9595
    participant PG as PostgreSQL
    participant MV as Milvus
    
    Note over Agent,MV: STORE OPERATION
    Agent->>SB: POST /api/memory/remember
    SB->>STC: admit(vector, payload)
    SB->>SB: Check salience
    
    alt High Salience
        SB->>SFM: POST /memories
        SFM->>PG: INSERT Memory
        SFM->>MV: INDEX vector
        SFM-->>SB: 201 Created
    end
    SB-->>Agent: {id, stored: true}
    
    Note over Agent,MV: RECALL OPERATION
    Agent->>SB: POST /api/memory/recall
    
    par Query Both
        SB->>STC: query(vector)
        STC-->>SB: cache_results
    and
        SB->>SFM: POST /search
        SFM->>MV: vector_search()
        MV-->>SFM: ltm_results
        SFM-->>SB: ltm_results
    end
    
    SB->>SB: Merge & Rank
    SB-->>Agent: {results: [...]}
```

---

## 5. Docker Compose Architecture

```mermaid
flowchart LR
    subgraph Network["docker network: soma-network"]
        subgraph Apps["Application Services"]
            SB[somabrain<br/>:9696]
            SFM[somafractalmemory<br/>:9595]
        end
        
        subgraph Data["Data Services"]
            PG[(postgres<br/>:5432)]
            Redis[(redis<br/>:6379)]
        end
        
        subgraph Vector["Vector Services"]
            MV[(milvus<br/>:19530)]
            ETCD[etcd]
            MINIO[minio]
        end
    end
    
    SB --> PG
    SB --> Redis
    SB --> SFM
    SFM --> PG
    SFM --> Redis
    SFM --> MV
    MV --> ETCD
    MV --> MINIO
```

---

## 6. Unified API Endpoints

### 6.1 SomaBrain Endpoints (Port 9696)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/memory/remember` | POST | Store memory (cache + LTM) |
| `/api/memory/recall` | POST | Query from cache + LTM |
| `/api/memory/delete` | DELETE | Delete from both stores |
| `/api/memory/stats` | GET | Unified memory statistics |
| `/api/admin/tenants` | CRUD | Tenant management |
| `/api/admin/settings` | GET/PATCH | Platform settings |

### 6.2 SomaFractalMemory Endpoints (Port 9595)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/memories` | POST | Store memory by coordinate |
| `/memories/{coord}` | GET | Retrieve by coordinate |
| `/memories/{coord}` | DELETE | Delete by coordinate |
| `/search` | POST | Vector similarity search |
| `/graph/link` | POST | Create graph link |
| `/graph/neighbors` | GET | Get neighbors |
| `/graph/path` | GET | Find path between coords |
| `/stats` | GET | Memory statistics |

---

## 7. Unified Admin UI Screens

### 7.1 Screen Map

| Screen | Route | Source Data |
|--------|-------|-------------|
| Dashboard | `/platform` | SomaBrain + SFM metrics |
| Tenants | `/platform/tenants` | SomaBrain TenantRegistry |
| Memory Overview | `/platform/memory` | SomaBrain + SFM combined |
| Memory Browser | `/platform/memory/browse` | SFM Memory table |
| Graph Explorer | `/platform/memory/graph` | SFM GraphLink |
| Vector Index | `/platform/memory/vectors` | Milvus stats |
| Settings | `/platform/settings` | Both services |

### 7.2 Memory Admin Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│ 📊 Memory Overview                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ ShortTerm    │  │ LongTerm     │  │ Graph Links  │          │
│  │    127       │  │   45,231     │  │    8,456     │          │
│  │ in cache     │  │ in storage   │  │ connections  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ TABS: [Overview] [Browse] [Graph] [Vectors] [Config]      │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │                                                           │ │
│  │  Memory Type Distribution    │   Storage by Tenant       │ │
│  │  [Pie Chart]                 │   [Bar Chart]             │ │
│  │                                                           │ │
│  │  ● Episodic: 65%             │   Acme Corp: 12,456      │ │
│  │  ● Semantic: 35%             │   Beta Inc:  8,921       │ │
│  │                                                           │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Configuration Unification

### 8.1 Shared Settings

| Setting | SomaBrain | SomaFractalMemory | Description |
|---------|-----------|-------------------|-------------|
| `POSTGRES_HOST` | ✓ | ✓ | PostgreSQL host |
| `POSTGRES_PORT` | ✓ | ✓ | PostgreSQL port |
| `REDIS_HOST` | ✓ | ✓ | Redis host |
| `REDIS_PORT` | ✓ | ✓ | Redis port |
| `SOMA_MILVUS_HOST` | ✓ | ✓ | Milvus host |
| `SOMA_MILVUS_PORT` | ✓ | ✓ | Milvus port |

### 8.2 Service-Specific Settings

| Service | Setting | Description |
|---------|---------|-------------|
| SomaBrain | `SOMABRAIN_WM_CAPACITY` | Cache capacity |
| SomaBrain | `SOMABRAIN_SALIENCE_THRESHOLD` | Store threshold |
| SomaFractalMemory | `SOMA_API_PORT` | LTM API port |
| SomaFractalMemory | `SOMA_COLLECTION_NAME` | Milvus collection |

---

## 9. Metrics Consolidation

### 9.1 Combined Metrics Dashboard

| Metric | Source | Description |
|--------|--------|-------------|
| `soma_cache_items` | SomaBrain | ShortTerm cache count |
| `soma_cache_hit_ratio` | SomaBrain | Cache hit rate |
| `soma_ltm_items` | SFM | LongTerm memory count |
| `soma_ltm_store_latency` | SFM | Store latency |
| `soma_graph_links` | SFM | Graph link count |
| `soma_vector_search_latency` | SFM | Vector search latency |
| `soma_milvus_collection_size` | Milvus | Vector index size |

---

## 10. Deployment Scenarios

### 10.1 Standalone Mode

```mermaid
flowchart LR
    A[SomaBrain Only] --> B[Local Cache]
    A --> C[No LTM]
```

### 10.2 Integrated Mode

```mermaid
flowchart LR
    A[SomaBrain] --> B[ShortTerm Cache]
    A --> C[SomaFractalMemory]
    C --> D[LongTerm Storage]
    C --> E[Graph Database]
```

### 10.3 Full Production

```mermaid
flowchart TB
    LB[Load Balancer] --> SB1[SomaBrain 1]
    LB --> SB2[SomaBrain 2]
    SB1 --> SFM[SomaFractalMemory]
    SB2 --> SFM
    SFM --> PG[(PostgreSQL)]
    SFM --> MV[(Milvus Cluster)]
```

---

## 11. Key Files Reference

### SomaBrain

| File | Purpose |
|------|---------|
| `somabrain/settings.py` | Django settings |
| `somabrain/wm.py` | ShortTerm cache |
| `somabrain/tenant_manager.py` | Multi-tenancy |
| `somabrain/api/endpoints/` | API routes |

### SomaFractalMemory

| File | Purpose |
|------|---------|
| `somafractalmemory/settings.py` | Django settings |
| `somafractalmemory/models.py` | Memory/GraphLink models |
| `somafractalmemory/services.py` | Business logic |
| `somafractalmemory/api/routers/` | API routes |

---

*Unified Memory Platform - SomaBrain AAAS*
