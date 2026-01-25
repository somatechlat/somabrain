# Memory Integration Flows

**Version:** 1.0.0  
**Date:** 2025-12-24  
**Purpose:** Complete flow documentation for unified memory operations

---

## 1. Overview

Flow documentation for memory operations across both SomaBrain (cache) and SomaFractalMemory (long-term storage).

---

## 2. Store Memory - Complete Flow

```mermaid
flowchart TD
    A[Agent: POST /api/memory/remember] --> B[SomaBrain API :9696]
    B --> C[Validate Request]
    C --> D[Generate Embedding]
    D --> E[Calculate Salience]
    E --> F{Salience > threshold?}
    
    F -->|No| G[Log: Discarded]
    G --> H[Return: stored=false]
    
    F -->|Yes| I[Admit to ShortTermCache]
    I --> J{Cache full?}
    J -->|Yes| K[Evict lowest priority]
    K --> L[Store in cache]
    J -->|No| L
    
    L --> M{Priority >= promotion_threshold?}
    M -->|No| N[Remain in cache only]
    M -->|Yes| O[POST to SomaFractalMemory :9595]
    
    O --> P[SFM: Generate coordinate]
    P --> Q[SFM: INSERT Memory]
    Q --> R[SFM: INDEX in Milvus]
    R --> S[SFM: Return memory_id]
    
    S --> T[Return: stored=true, id=...]
    N --> T
```

---

## 3. Recall Memory - Complete Flow

```mermaid
flowchart TD
    A[Agent: POST /api/memory/recall] --> B[SomaBrain API :9696]
    B --> C[Parse query]
    C --> D[Generate query embedding]
    
    D --> E[Query ShortTermCache]
    D --> F[POST to SomaFractalMemory /search]
    
    E --> G[Cache results]
    F --> H[SFM: Query Milvus]
    H --> I[SFM: Fetch from PostgreSQL]
    I --> J[LTM results]
    
    G --> K[Merge results]
    J --> K
    
    K --> L[Deduplicate]
    L --> M[Rank by relevance]
    M --> N[Apply top_k limit]
    N --> O[Return results]
```

---

## 4. Browse Memory - Admin Flow

```mermaid
sequenceDiagram
    participant Admin
    participant UI as AAAS UI
    participant SB as SomaBrain
    participant SFM as SomaFractalMemory
    participant PG as PostgreSQL
    
    Admin->>UI: Navigate to /platform/memory/browse
    UI->>SFM: GET /memories?tenant=&page=1&limit=50
    SFM->>PG: SELECT * FROM memory LIMIT 50
    PG-->>SFM: memory_rows
    SFM-->>UI: {items: [...], total: 45231}
    UI->>Admin: Display memory table
    
    Admin->>UI: Click memory row
    UI->>SFM: GET /memories/{coord}
    SFM->>PG: SELECT * FROM memory WHERE coord=...
    PG-->>SFM: memory
    SFM-->>UI: {memory detail}
    UI->>Admin: Show detail modal
    
    Admin->>UI: Click 'Check in Cache'
    UI->>SB: GET /api/memory/cache/lookup?coord=...
    SB-->>UI: {in_cache: true/false, priority: 0.85}
    UI->>Admin: Show cache status
```

---

## 5. Graph Explorer Flow

```mermaid
sequenceDiagram
    participant Admin
    participant UI as AAAS UI
    participant SFM as SomaFractalMemory
    participant PG as PostgreSQL
    
    Admin->>UI: Navigate to /platform/memory/graph
    UI->>Admin: Show coordinate input
    
    Admin->>UI: Enter start coordinate, depth=2
    UI->>SFM: GET /graph/neighbors?coord=1.0,2.0,3.0&depth=2
    
    SFM->>PG: SELECT * FROM graph_link WHERE from_coord=...
    PG-->>SFM: level_1_links
    SFM->>PG: SELECT * FROM graph_link WHERE from_coord IN (...)
    PG-->>SFM: level_2_links
    
    SFM-->>UI: {nodes: [...], edges: [...]}
    UI->>UI: Render graph visualization
    UI->>Admin: Display interactive graph
    
    Admin->>UI: Click node
    UI->>SFM: GET /memories/{coord}
    SFM-->>UI: memory_detail
    UI->>Admin: Show node detail panel
```

---

## 6. Delete Memory Flow

```mermaid
flowchart TD
    A[Admin: Select memory] --> B[Click Delete]
    B --> C[Confirm dialog]
    C --> D{Confirmed?}
    D -->|No| E[Cancel]
    D -->|Yes| F[DELETE /api/memory/{id}]
    
    F --> G[SomaBrain: Remove from cache]
    G --> H[SomaBrain: Call SFM DELETE]
    H --> I[SFM: DELETE FROM memory]
    I --> J[SFM: DELETE FROM milvus]
    J --> K[SFM: DELETE FROM graph_link]
    
    K --> L[Audit log]
    L --> M[Return success]
```

---

## 7. Bulk Import Flow (Admin)

```mermaid
flowchart TD
    A[Admin: Upload JSON/CSV file] --> B[Parse file]
    B --> C{Valid format?}
    C -->|No| D[Show validation errors]
    C -->|Yes| E[Create import job]
    E --> F[Queue items]
    
    F --> G[Worker: Process batch]
    G --> H[Generate embeddings]
    H --> I[Store in SomaBrain]
    I --> J[Promote to SFM if high priority]
    J --> K{More batches?}
    K -->|Yes| G
    K -->|No| L[Complete]
    
    L --> M[Email notification]
    M --> N[Update UI progress]
```

---

## 8. Vector Index Maintenance Flow

```mermaid
sequenceDiagram
    participant Cron
    participant API as SomaBrain
    participant SFM as SomaFractalMemory
    participant MV as Milvus
    
    Note over Cron: Scheduled: Daily 3 AM
    
    Cron->>API: POST /api/admin/maintenance/vectors
    API->>SFM: POST /admin/reindex
    
    SFM->>MV: Get collection stats
    MV-->>SFM: {row_count, index_size}
    
    alt Index fragmented
        SFM->>MV: Compact collection
        MV-->>SFM: Compaction complete
        SFM->>MV: Rebuild index
        MV-->>SFM: Index rebuilt
    end
    
    SFM-->>API: {status: complete, stats: {...}}
    API->>API: Log maintenance event
```

---

## 9. Cache → LTM Promotion Flow

```mermaid
flowchart TD
    A[ShortTermCache: Item exists] --> B{Tick counter}
    B --> C[Check priority over time]
    C --> D{Priority >= 0.85 for 3+ ticks?}
    
    D -->|No| E[Keep in cache]
    E --> F{Eviction candidate?}
    F -->|Yes| G[Remove from cache]
    F -->|No| B
    
    D -->|Yes| H[Mark for promotion]
    H --> I[POST to SomaFractalMemory]
    I --> J[Store in PostgreSQL]
    J --> K[Index in Milvus]
    K --> L[Mark as promoted]
    L --> M[Remove from cache]
```

---

## 10. Memory Stats Aggregation

```mermaid
flowchart LR
    subgraph SomaBrain["SomaBrain :9696"]
        SB_API[GET /api/admin/stats]
        SB_Cache[Cache Stats]
        SB_Quota[Quota Stats]
    end
    
    subgraph SFM["SomaFractalMemory :9595"]
        SFM_API[GET /stats]
        SFM_Memory[Memory Count]
        SFM_Graph[Graph Stats]
    end
    
    subgraph Milvus["Milvus"]
        MV_Stats[Collection Stats]
    end
    
    UI[Admin Dashboard] --> SB_API
    UI --> SFM_API
    SB_API --> SB_Cache
    SB_API --> SB_Quota
    SFM_API --> SFM_Memory
    SFM_API --> SFM_Graph
    SFM_API --> MV_Stats
```

---

*Memory Integration Flows - SomaBrain AAAS*
