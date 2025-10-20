SomaBrain — Use Cases and UML

This document captures core user journeys (use cases) and concise UML-style diagrams (Mermaid) covering sequences, components, and classes.

Actors
- Agent: Calls SomaBrain endpoints to think/recall/remember/reflect.
- Tenant Admin: Manages tokens, quotas, namespaces.
- System Operator: Observes health/metrics; scales deployment.
- Memory Backend: SomaFractalMemory (local/HTTP) provides LTM + graph.
- Predictor Provider: Stub/LLM/ML predictor used by CerebellumPredictor.

Use Cases (MVP + Near-Term)
- Act On Task (/act): Thalamus → RateLimit/Auth → TenantContext → WM/HRR recall → Memory recall → Predictor → AmygdalaSalience → BasalGangliaPolicy → conditional store to LTM + WM admit → response.
- Remember Event (/remember): Thalamus → RateLimit/Auth/Quota → LTM store via MemoryClient → WM admit (and HRR context if enabled).
- Recall Context (/recall): Thalamus → RateLimit/Auth → WM/HRR top‑k → per‑tenant recall cache → LTM hybrid recall → return merged results.
- Reflect & Consolidate (/reflect): recent episodics (WM) → summary → write semantic → link sources.
- Personality Get/Set (/personality): semantic trait storage; influences planning.
- Migration Export/Import (future): export manifest + JSONL memories → import → warm WM/HRR.
- Graph Reasoning (future): k‑hop via memory graph; Hebbian strengthening.
- Operations & Observability: /health, /metrics; SLOs.

Sequence — Act on Task (/act)
```mermaid
sequenceDiagram
    actor Agent
    participant Thalamus as ThalamusRouter
    participant RL as RateLimiter/Quotas
    participant Tenant as TenantContext
    participant WM as PrefrontalWM/HRR Context
    participant Mem as MemoryClient
    participant Pred as CerebellumPredictor
    participant Amy as AmygdalaSalience
    participant BG as BasalGangliaPolicy

    Agent->>Thalamus: POST /act {task}
    Thalamus->>RL: allow(tenant) + quota check
    Thalamus->>Tenant: derive from headers/token
    Thalamus->>WM: recall(embed/HRR(task), k)
    Thalamus->>Mem: recall(task, k)
    Thalamus->>Pred: predict(vec), compare(actual)
    Thalamus->>Amy: score(novelty, error, neuromods)
    Thalamus->>BG: decide(store, act)
    alt store==true
      Thalamus->>Mem: remember(episodic)
      Thalamus->>WM: admit(vec, payload)
    end
    Thalamus-->>Agent: ActResponse {results[]}
```

Sequence — Recall (/recall)
```mermaid
sequenceDiagram
    actor Agent
    participant Thalamus
    participant RL as RateLimiter
    participant WM
    participant Cache as RecallCache
    participant Mem

    Agent->>Thalamus: POST /recall {query, k}
    Thalamus->>RL: allow(tenant)
    Thalamus->>WM: recall(embed/HRR(query), k)
    Thalamus->>Cache: get(tenant, query)
    alt cache miss
      Thalamus->>Mem: recall(query, k)
      Mem-->>Thalamus: payloads
      Thalamus->>Cache: set(...)
    else cache hit
      Cache-->>Thalamus: payloads
    end
    Thalamus-->>Agent: {wm[], memory[]}
```

Sequence — Reflect (/reflect)
```mermaid
sequenceDiagram
    actor Agent
    participant Thalamus
    participant WM
    participant Mem

    Agent->>Thalamus: POST /reflect
    Thalamus->>WM: get recent episodics
    Thalamus->Thalamus: summarize (heuristic/ML)
    Thalamus->>Mem: remember(semantic summary)
    Thalamus->>Mem: link(summary, sources)
    Thalamus-->>Agent: {created, summaries}
```

Component Diagram
```mermaid
graph TD
  Agent --> API[FastAPI Service]
  API --> Thalamus[ThalamusRouter]
  API --> Metrics[Prometheus Middleware]
  Thalamus --> Rate[RateLimiter/Quotas]
  Thalamus --> Tenant[TenantContext]
  Thalamus --> WM[PrefrontalWM]
  Thalamus --> HRR[QuantumLayer/HRR Context]
  Thalamus --> Amy[AmygdalaSalience]
  Thalamus --> BG[BasalGangliaPolicy]
  Thalamus --> Pred[CerebellumPredictor]
  Thalamus --> Mem[MemoryClient]
  Mem --> SFM[(SomaFractalMemory)]
  SFM --> Redis[(Redis/FakeRedis)]
  SFM --> Qdrant[(Qdrant/InMemory vectors)]
```

Class Diagram
```mermaid
classDiagram
  class ThalamusRouter { +normalize(payload) }
  class WorkingMemory { +admit(vec,payload) +recall(vec,k) +novelty(vec) }
  class HRRContext { +admit(id,vec) +novelty(vec) +cleanup(q) }
  class QuantumLayer { +superpose() +bind() +unbind() +permute() +cleanup() }
  class AmygdalaSalience { +score() +gates() }
  class BasalGangliaPolicy { +decide() }
  class Neuromodulators { +get_state() +set_state() +subscribe() }
  class MemoryClient { +remember() +recall() +link() }
  class MultiTenantWM { +admit() +recall() +novelty() +items() }
  class MultiTenantMemory { +for_namespace() }
  class RateLimiter { +allow(key) }
  class QuotaManager { +allow_write() +remaining() }

  ThalamusRouter --> RateLimiter
  ThalamusRouter --> WorkingMemory
  ThalamusRouter --> HRRContext
  ThalamusRouter --> AmygdalaSalience
  ThalamusRouter --> BasalGangliaPolicy
  ThalamusRouter --> MemoryClient
  HRRContext --> QuantumLayer
```

Non‑Functional Requirements
- Latency SLOs: /act p95 < 150 ms (stub predictor), < 600 ms (LLM); /recall p95 < 80 ms with WM/cache hit.
- Throughput: multi‑tenant token bucket per tenant; autoscale horizontally.
- Isolation: strict tenant namespace mapping to SomaFractalMemory; no cross‑tenant WM/HRR context sharing.
- Observability: metrics with bounded cardinality; tracing optional.
- Security: bearer auth (optional), quotas, input normalization; sensitive field redaction.

This document evolves with the architecture; request additional flows or diagrams as needed.
