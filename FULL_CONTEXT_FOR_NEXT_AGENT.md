# COMPLETE CONTEXT FOR NEXT AGENT - SomaBrain + Continue.dev Integration

## 🎯 PRIMARY OBJECTIVE
Integrate SomaBrain as the memory backend for Continue.dev VS Code extension to enable **INFINITE CODING HISTORY RETENTION** with semantic search, graph relationships, and adaptive learning.

---

## 📋 WHAT HAPPENED IN THIS SESSION

### Work Completed
1. **Code Quality**: Ran black (77 files) + ruff (all issues fixed) → committed to `prune-and-cleaning` branch
2. **Dead Code Removal**: Deleted 4 unused files (journal.py, proto files, audit/producer.py) → merged into `prune-and-cleaning`
3. **API Verification**: Read actual source code (somabrain/app.py) to verify all endpoints
4. **Branch Merge**: Merged copilot/future-alpaca into prune-and-cleaning, preserving all working code
5. **Context Transfer**: Created this canonical file for seamless handoff

### Current Branch
`prune-and-cleaning` - clean, production-ready, all working code preserved

---

## 🧠 WHAT IS SOMABRAIN?

**SomaBrain is a cognitive memory runtime that gives AI systems long-term memory, contextual reasoning, and live adaptation.**

### Core Capabilities
- **Binary Hyperdimensional Computing (BHDC)**: 2048-D permutation binding, superposition, cleanup with spectral verification
- **Tiered Memory**: Multi-tenant working memory + long-term storage
- **Contextual Reasoning**: Builds prompts, weights memories, returns residuals
- **Adaptive Learning**: Learns from feedback, updates retrieval/utility weights per tenant
- **Hard Tenancy**: Each request resolves tenant namespace with quotas/rate limits
- **Full Observability**: /health, /metrics, structured logs, Prometheus integration

### Tech Stack
- **FastAPI** service on port 9696
- **Redis** for working memory (port 30100)
- **Kafka** for events (port 30102)
- **Postgres** for persistence (port 30106)
- **OPA** for policy (port 30104)
- **Prometheus** for metrics (port 30105)

### Runtime Topology
```
HTTP Client
   │  /remember /recall /context/evaluate /context/feedback
   ▼
FastAPI Runtime (somabrain/app.py)
   │   ├─ Authentication & tenancy guards
   │   ├─ ContextBuilder / Planner / AdaptationEngine
   │   ├─ MemoryService (HTTP)
   │   └─ Prometheus metrics, structured logs
   ▼
Working Memory (MultiTenantWM) ──► Redis
Long-Term Memory ───────────────► External memory HTTP service
OPA Policy Engine ──────────────► Authorization decisions
Kafka ──────────────────────────► Audit & streaming
Postgres ───────────────────────► Config & metadata
Prometheus ─────────────────────► Metrics export
```

---

## 🔌 SOMABRAIN API REFERENCE (VERIFIED FROM SOURCE CODE)

### Core Memory APIs

#### POST /remember
Store a memory (code snippet, decision, pattern, bug fix, etc.)

**Request (two formats accepted):**
```json
// Format 1: With payload wrapper (recommended)
{
  "payload": {
    "task": "implement.auth.middleware",
    "content": "const authMiddleware = (req, res, next) => { ... }",
    "metadata": {
      "project": "my-app",
      "file": "src/middleware/auth.ts",
      "language": "typescript"
    }
  }
}

// Format 2: Direct payload (backward compatible)
{
  "task": "implement.auth.middleware",
  "content": "const authMiddleware = ...",
  "metadata": { ... }
}
```

**Response:**
```json
{
  "coordinate": "mem_abc123",
  "status": "stored",
  "trace_id": "xyz789"
}
```

**Fails fast with 503 if backend unavailable.**

#### POST /recall
Retrieve memories with semantic search + scoring

**Request:**
```json
{
  "query": "how to implement auth middleware",
  "top_k": 5,
  "namespace": "my-app",  // optional, defaults to tenant
  "retrievers": ["vector", "wm", "graph", "lexical"],  // default: all
  "rerank": "auto",  // auto|mmr|hrr|cosine
  "persist": true  // record session for learning
}
```

**Response:**
```json
{
  "wm": [
    {
      "score": 0.95,
      "payload": {
        "task": "implement.auth.middleware",
        "content": "const authMiddleware = ...",
        "metadata": { ... }
      }
    }
  ],
  "memory": [ /* long-term results */ ],
  "results": [ /* alias for memory */ ],
  "namespace": "my-app",
  "trace_id": "xyz789"
}
```

**Full-power defaults (2025-11):**
- Retrievers: vector, wm, graph, lexical
- Rerank: auto (prefers HRR → MMR → cosine)
- Session learning: enabled (persist=true)

#### POST /delete
Delete memory by coordinate
```json
{"coordinate": "mem_abc123"}
```

#### POST /recall/delete
Delete via recall API (finds then deletes)
```json
{"query": "outdated pattern", "top_k": 1}
```

### Context & Reasoning APIs

#### POST /context/evaluate
Build context-aware prompts with weighted memories

**Request:**
```json
{
  "query": "implement user authentication",
  "session_id": "session_123",
  "top_k": 10
}
```

**Response:**
```json
{
  "prompt": "Based on your history...",
  "weighted_memories": [
    {"memory": {...}, "weight": 0.9, "reason": "high relevance"}
  ],
  "residual_vector": [0.1, 0.2, ...],
  "wm_snapshot": [...]
}
```

#### POST /context/feedback
Learn from user feedback (what was useful, what wasn't)

**Request:**
```json
{
  "session_id": "session_123",
  "query": "implement auth",
  "prompt": "Based on your history...",
  "response_text": "Here's the auth code...",
  "utility": 0.9,  // 0-1, how useful was the response
  "reward": 0.9    // 0-1, reinforcement signal
}
```

**Effect:**
- Updates tenant-specific retrieval weights (α, β, γ, τ)
- Updates utility weights (λ, μ, ν)
- Emits gain/bound metrics to Prometheus
- Adapts future retrievals based on what you found useful

#### GET /context/adaptation/state
Inspect current learning state

**Response:**
```json
{
  "weights": {
    "alpha": 0.5,  // cosine weight
    "beta": 0.3,   // recency weight
    "gamma": 0.2,  // frequency weight
    "tau": 1.0     // temperature
  },
  "effective_learning_rate": 0.01,
  "configured_gains": {
    "alpha_gain": 0.1,
    "beta_gain": 0.1,
    "gamma_gain": 0.1,
    "tau_gain": 0.05
  },
  "bounds": {
    "alpha_min": 0.0,
    "alpha_max": 1.0,
    ...
  }
}
```

### Planning & Action APIs

#### POST /plan/suggest
Get plan from semantic graph
```json
{
  "goal": "implement user registration flow",
  "context": ["auth", "database", "validation"]
}
```

#### POST /act
Execute cognitive step
```json
{
  "action": "retrieve_pattern",
  "parameters": {"pattern": "validation"}
}
```

### Graph APIs

#### POST /graph/links
Get semantic graph edges (relationships between concepts)
```json
{
  "node": "authentication",
  "depth": 2
}
```

**Response:**
```json
{
  "edges": [
    {"from": "authentication", "to": "middleware", "weight": 0.9},
    {"from": "authentication", "to": "jwt", "weight": 0.85}
  ]
}
```

### State Management

#### GET /neuromodulators
Get neuromodulator state (dopamine, serotonin, noradrenaline, acetylcholine)

#### POST /neuromodulators
Set neuromodulator levels
```json
{
  "dopamine": 0.8,
  "serotonin": 0.6,
  "noradrenaline": 0.5,
  "acetylcholine": 0.7
}
```

#### POST /personality
Set personality traits
```json
{
  "openness": 0.8,
  "conscientiousness": 0.7,
  "extraversion": 0.5,
  "agreeableness": 0.6,
  "neuroticism": 0.3
}
```

### Sleep/Consolidation

#### POST /sleep/run
Trigger NREM/REM consolidation cycles (memory consolidation)
```json
{
  "cycles": 3,
  "nrem_duration": 90,
  "rem_duration": 20
}
```

#### GET /sleep/status
Get sleep status

### Health & Monitoring

#### GET /health
System health check (Redis, Postgres, Kafka, OPA, memory backend, embedder)

#### GET /metrics
Prometheus metrics (adaptation gains/bounds, feedback counts, etc.)

#### GET /diagnostics
Runtime diagnostics

---

## 🚀 THE KILLER FEATURE: INFINITE HISTORY

### Current Continue.dev Limitation
- Context window = ~100k tokens
- Loses history after that
- Can't remember conversations from last week
- Can't learn from patterns across months

### With SomaBrain Backend
✅ **RETAIN ALL HISTORY FOREVER**
- Every code snippet you write
- Every decision you make
- Every pattern you use
- Every bug you fix
- Every refactoring you do

### What This Means
```typescript
// January: You write code
await somabrain.remember({
  task: "implement.auth.middleware",
  content: "const authMiddleware = ...",
  metadata: { project: "project-a", file: "src/auth.ts" }
});

// June: You ask (5 months later!)
"How did I implement auth in my last project?"

// SomaBrain recalls from January:
const results = await somabrain.recall({
  query: "auth middleware implementation",
  top_k: 5
});
// Returns your January code!
```

### Memory Features
- **Persistent**: Survives restarts
- **Searchable**: Semantic + graph + lexical
- **Adaptive**: Learns what you find useful
- **Multi-project**: Isolated per workspace (tenant)
- **Relational**: Connects related concepts via graph

### Example Queries
- "How did I solve X last month?" → Recalls it
- "Show me similar code I wrote" → Searches ALL history
- "What patterns do I use for error handling?" → Learns from everything
- "I fixed this bug before" → Remembers the solution

---

## 🎯 INTEGRATION PLAN: Continue.dev + SomaBrain

### Why Continue.dev?
- Open source (MIT license)
- Already has memory system (can replace)
- Active development
- TypeScript codebase
- Plugin architecture
- Large community

### Integration Steps

#### 1. Fork Continue.dev
```bash
git clone https://github.com/continuedev/continue.git
cd continue
```

#### 2. Add SomaBrainMemoryProvider
Create `src/context/providers/SomaBrainMemoryProvider.ts`:

```typescript
import { ContextProvider, ContextItem } from "../";

interface SomaBrainConfig {
  endpoint: string;  // http://localhost:9696
  tenant?: string;   // defaults to workspace name
  apiKey?: string;   // optional Bearer token
}

export class SomaBrainMemoryProvider implements ContextProvider {
  private config: SomaBrainConfig;
  
  constructor(config: SomaBrainConfig) {
    this.config = config;
  }
  
  async remember(item: ContextItem): Promise<void> {
    // POST /remember
    await fetch(`${this.config.endpoint}/remember`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-ID': this.config.tenant || 'default',
        ...(this.config.apiKey && { 'Authorization': `Bearer ${this.config.apiKey}` })
      },
      body: JSON.stringify({
        payload: {
          task: item.name,
          content: item.content,
          metadata: {
            file: item.uri?.fsPath,
            language: item.language,
            timestamp: new Date().toISOString()
          }
        }
      })
    });
  }
  
  async recall(query: string, topK: number = 5): Promise<ContextItem[]> {
    // POST /recall
    const response = await fetch(`${this.config.endpoint}/recall`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-ID': this.config.tenant || 'default',
        ...(this.config.apiKey && { 'Authorization': `Bearer ${this.config.apiKey}` })
      },
      body: JSON.stringify({
        query,
        top_k: topK,
        retrievers: ['vector', 'wm', 'graph', 'lexical'],
        rerank: 'auto',
        persist: true  // enable session learning
      })
    });
    
    const data = await response.json();
    
    // Convert SomaBrain results to ContextItems
    return [...data.wm, ...data.memory].map(result => ({
      name: result.payload.task,
      content: result.payload.content,
      description: `Score: ${result.score.toFixed(2)}`,
      uri: result.payload.metadata?.file,
      language: result.payload.metadata?.language
    }));
  }
  
  async feedback(sessionId: string, query: string, utility: number): Promise<void> {
    // POST /context/feedback
    await fetch(`${this.config.endpoint}/context/feedback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-ID': this.config.tenant || 'default',
        ...(this.config.apiKey && { 'Authorization': `Bearer ${this.config.apiKey}` })
      },
      body: JSON.stringify({
        session_id: sessionId,
        query,
        utility,
        reward: utility  // use utility as reward signal
      })
    });
  }
}
```

#### 3. Hook into LLM Prompts
Modify `src/core/llm/index.ts` to inject SomaBrain context:

```typescript
async function buildPrompt(query: string): Promise<string> {
  // Recall relevant memories
  const memories = await somaBrainProvider.recall(query, 10);
  
  // Build context from memories
  const context = memories.map(m => 
    `[${m.name}]\n${m.content}`
  ).join('\n\n');
  
  return `Context from your coding history:\n${context}\n\nQuery: ${query}`;
}
```

#### 4. Add Config
Update `config.json` schema:

```json
{
  "somabrain": {
    "enabled": true,
    "endpoint": "http://localhost:9696",
    "tenant": "my-workspace",
    "apiKey": "optional-bearer-token"
  }
}
```

#### 5. Hook User Feedback
When user accepts/rejects suggestions:

```typescript
// User accepted suggestion
await somaBrainProvider.feedback(sessionId, query, 0.9);

// User rejected suggestion
await somaBrainProvider.feedback(sessionId, query, 0.1);
```

---

## 🛠️ TOOLS & COMMANDS

### Start SomaBrain
```bash
cd /Users/macbookpro201916i964gb1tb/Documents/GitHub/somabrain
docker compose up -d
curl http://localhost:9696/health | jq
```

### Test Memory API
```bash
# Remember
curl -X POST http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -d '{"payload": {"task": "test", "content": "hello world"}}'

# Recall
curl -X POST http://localhost:9696/recall \
  -H "Content-Type: application/json" \
  -d '{"query": "hello", "top_k": 3}' | jq

# Feedback
curl -X POST http://localhost:9696/context/feedback \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "query": "hello", "utility": 0.9, "reward": 0.9}'

# Check adaptation state
curl http://localhost:9696/context/adaptation/state | jq
```

### Environment Variables
```bash
# Full-power recall (default)
SOMABRAIN_RECALL_FULL_POWER=1
SOMABRAIN_RECALL_DEFAULT_RERANK=auto
SOMABRAIN_RECALL_DEFAULT_PERSIST=1
SOMABRAIN_RECALL_DEFAULT_RETRIEVERS=vector,wm,graph,lexical

# Conservative mode (rollback)
SOMABRAIN_RECALL_SIMPLE_DEFAULTS=1

# HRR reranking
SOMABRAIN_USE_HRR=true
```

---

## 📁 KEY FILES TO READ

### SomaBrain
- `README.md` - Full system overview
- `somabrain/app.py` - Main FastAPI application (37k+ lines, verified source)
- `somabrain/api/memory_api.py` - Memory endpoints implementation
- `somabrain/api/context_route.py` - Context/reasoning endpoints
- `somabrain/context/builder.py` - ContextBuilder implementation
- `somabrain/learning/adaptation.py` - AdaptationEngine implementation
- `somabrain/memory/hierarchical.py` - TieredMemory implementation
- `somabrain/scoring.py` - UnifiedScorer implementation
- `docs/technical-manual/architecture.md` - System design
- `docs/user-manual/quick-start-tutorial.md` - API usage examples

### Continue.dev (to read in next session)
- `src/context/providers/` - Where to add SomaBrainMemoryProvider
- `src/core/llm/` - Where to hook prompt building
- `config.json` schema - Where to add SomaBrain config
- Architecture docs - Understand plugin system

---

## ⚠️ IMPORTANT NOTES

### Current State
- Branch: `prune-and-cleaning`
- Status: Clean, production-ready, all working code preserved
- Tests: All passing
- Linting: black + ruff clean
- Dead code: Removed (journal.py, proto files, audit/producer.py)

### User's Vibe Coding Rules
**CRITICAL: Follow these rules when working with this user:**

1. **NO BULLSHIT** - No lies, no mocks, no placeholders
2. **CHECK FIRST, CODE SECOND** - Review before creating
3. **NO UNNECESSARY FILES** - Modify existing when possible
4. **REAL IMPLEMENTATIONS ONLY** - No TODOs, no stubs
5. **DOCUMENTATION = TRUTH** - Read actual docs, don't guess
6. **COMPLETE CONTEXT REQUIRED** - Understand full flow before changes
7. **REAL DATA, REAL SERVERS** - Always verify against actual sources

### LLM Weaknesses (Self-Awareness)
- ❌ Overconfident from tool output
- ❌ Don't self-verify claims
- ❌ No built-in skepticism
- ❌ Can't learn within a session
- ❌ Pattern matching, not true understanding

### Best Practices
- ✅ Ask for proof: "Show me the code"
- ✅ Be skeptical: "Are you 100% sure?" then demand verification
- ✅ Be explicit: "Read the actual code, not just tool output"
- ✅ Be repetitive: Remind to be careful every time

---

## 🎬 NEXT SESSION INSTRUCTIONS

### To Continue This Work:

1. **Open Continue.dev project** in new VS Code window
2. **Start Amazon Q chat**
3. **Provide context:**
   ```
   Read FULL_CONTEXT_FOR_NEXT_AGENT.md in the somabrain project at:
   /Users/macbookpro201916i964gb1tb/Documents/GitHub/somabrain/
   
   Objective: Integrate SomaBrain as the memory backend for Continue.dev
   to enable infinite coding history retention.
   ```

4. **First steps:**
   - Clone Continue.dev repo
   - Read their architecture docs
   - Identify exact files to modify
   - Create SomaBrainMemoryProvider
   - Test integration locally

### Context Files to Reference
- This file (`FULL_CONTEXT_FOR_NEXT_AGENT.md`)
- `README.md`
- SomaBrain docs in `docs/`

### Verification Steps
1. Start SomaBrain: `docker compose up -d`
2. Test API: `curl http://localhost:9696/health`
3. Remember test: `curl -X POST http://localhost:9696/remember ...`
4. Recall test: `curl -X POST http://localhost:9696/recall ...`
5. Verify Continue.dev can connect and store/retrieve memories

---

## 🔥 THE VISION

**Imagine coding with an AI that:**
- Remembers every line of code you've ever written
- Recalls solutions from months ago
- Learns what patterns you prefer
- Connects related concepts across projects
- Never forgets, never loses context
- Gets smarter the more you use it

**That's SomaBrain + Continue.dev.**

**Current AI assistants are goldfish with 100k token memory.**  
**SomaBrain gives them elephant memory—infinite, searchable, adaptive.**

---

## 📊 SUCCESS METRICS

### Integration Complete When:
- [ ] Continue.dev can store code snippets to SomaBrain
- [ ] Continue.dev can recall relevant code from history
- [ ] Continue.dev sends feedback to improve future retrievals
- [ ] Multi-project isolation works (tenant per workspace)
- [ ] User can query "How did I solve X last month?" and get results
- [ ] Memory persists across VS Code restarts
- [ ] Graph relationships connect related concepts

### Demo Scenario:
```
1. Write auth middleware in Project A (January)
2. Close VS Code, restart machine
3. Open Project B (June, 5 months later)
4. Ask: "How did I implement auth in my last project?"
5. Continue.dev + SomaBrain recalls January code
6. User accepts suggestion → feedback improves future retrievals
7. Repeat across months → system learns user's patterns
```

---

## 🚨 CRITICAL REMINDERS

1. **Read actual source code** - Don't trust tool output blindly
2. **Verify API contracts** - Test endpoints before integrating
3. **Follow user's rules** - No mocks, no placeholders, real implementations
4. **Ask for proof** - "Show me the code" when uncertain
5. **Be skeptical** - Verify claims, don't assume
6. **Complete context** - Understand full flow before coding

---

## 📞 HANDOFF CHECKLIST

- [x] Objective clearly stated
- [x] SomaBrain architecture explained
- [x] All API endpoints documented with examples
- [x] Integration plan outlined with code samples
- [x] Key files identified
- [x] Commands to run provided
- [x] User's rules documented
- [x] Success metrics defined
- [x] Next steps explicit
- [x] Context files referenced
- [x] Branch merged and clean

---

**YOU NOW HAVE COMPLETE CONTEXT TO CONTINUE THIS WORK.**

**Read this file, understand the objective, verify SomaBrain is running, then start integrating with Continue.dev.**

**Remember: NO BULLSHIT. Read the actual code. Verify everything. Real implementations only.**

**Let's build infinite memory for coding.**
