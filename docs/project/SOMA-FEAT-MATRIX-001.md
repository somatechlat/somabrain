# AGENT ZERO vs SOMA — FEATURE MATRIX

## Document Control

| Field | Value |
|-------|-------|
| Document Title | Agent Zero vs Soma Feature Comparison Matrix |
| Document Identifier | SOMA-FEAT-MATRIX-001 |
| Version | 1.0.0 |
| Date | 2026-06-15 |
| Status | Active |

---

## 1. EXECUTIVE SUMMARY

Agent Zero is a **personal AI agent framework** with 2,972 files, 42 plugins, 75 prompt templates, 29 tools, and a full web UI. It provides a Dockerized Linux desktop, browser with DOM annotation, document cowork, projects, skills, plugins, and multi-agent cooperation.

**Soma has the cognitive engine (Brain + Memory) but lacks the user-facing product features that Agent Zero excels at.**

---

## 2. FEATURE MATRIX

### 2.1 Core Agent Engine

| # | Feature | Agent Zero | Soma Current | Gap | Priority |
|---|---------|------------|--------------|-----|----------|
| C-01 | LLM chat with streaming | ✓ (LiteLLM + Responses API) | ✓ (V3 orchestrator + LiteLLM) | NONE | — |
| C-02 | Multi-provider LLM support | ✓ (OpenAI, Anthropic, Groq, Ollama, etc.) | ✓ (LiteLLM) | NONE | — |
| C-03 | Tool calling / function calling | ✓ (native tool_calls + regex fallback) | ✓ (native + regex fallback) | NONE | — |
| C-04 | Conversation memory | ✓ (history.py, persist_chat.py) | ✓ (PostgreSQL + Brain + SFM) | Soma is BETTER | — |
| C-05 | Cognitive memory (brain-like) | ✗ | ✓ (SomaBrain: HRR, neuromodulators, sleep) | Soma ADVANTAGE | — |
| C-06 | Fractal vector memory | ✗ | ✓ (SomaFractalMemory: coordinates, graph) | Soma ADVANTAGE | — |
| C-07 | Agent profiles / personalities | ✓ (agent profiles, behaviour prompts) | ✓ (Capsule system) | Soma needs UI | MEDIUM |
| C-08 | Context window management | ✓ (chat_compaction plugin) | ✓ (5-lane context builder) | NONE | — |
| C-09 | Token counting | ✓ (helpers/tokens.py) | ✓ (tiktoken) | NONE | — |
| C-10 | Rate limiting | ✓ (helpers/rate_limiter.py) | ✓ (Redis sliding window) | NONE | — |
| C-11 | Circuit breaker | ✗ | ✓ (async state machine) | Soma ADVANTAGE | — |
| C-12 | Multi-tenancy | ✗ (single user) | ✓ (Tenant + TenantUser) | Soma ADVANTAGE | — |
| C-13 | Subagent delegation | ✓ (call_subordinate, parallel.py) | ✗ (not implemented) | **MISSING** | HIGH |
| C-14 | A2A (Agent-to-Agent) | ✓ (a2a_chat.py, fasta2a) | ✓ (delegation_gateway) | NONE | — |

### 2.2 Tools

| # | Tool | Agent Zero | Soma Current | Gap | Priority |
|---|------|------------|--------------|-----|----------|
| T-01 | Code execution (Python) | ✓ (_code_execution plugin) | ✓ (tool_executor) | Soma needs sandbox | MEDIUM |
| T-02 | Code execution (Shell) | ✓ (Docker container) | ✓ (tool_executor) | Soma needs sandbox | MEDIUM |
| T-03 | Web search | ✓ (search_engine.py, DuckDuckGo) | ✓ (duckduckgo-search dep) | NONE | — |
| T-04 | Browser automation | ✓ (_browser plugin, DOM annotation) | ✓ (browser-use dep) | Agent Zero is BETTER | HIGH |
| T-05 | File operations | ✓ (helpers/files.py, file_browser.py) | ✗ (not implemented) | **MISSING** | HIGH |
| T-06 | Document query / RAG | ✓ (document_query.py, FAISS) | ✓ (knowledge app) | Soma needs better UI | MEDIUM |
| T-07 | Vision / image loading | ✓ (vision_load.py, helpers/images.py) | ✓ (multimodal service) | NONE | — |
| T-08 | Notification to user | ✓ (notify_user.py) | ✗ | **MISSING** | MEDIUM |
| T-09 | Scheduler / cron tasks | ✓ (scheduler.py, task_scheduler.py) | ✓ (Temporal workflows) | NONE | — |
| T-10 | Wait / delay | ✓ (wait.py) | ✗ | **MISSING** | LOW |
| T-11 | Response formatting | ✓ (response.py) | ✓ (V3 orchestrator) | NONE | — |
| T-12 | Git operations | ✓ (helpers/git.py) | ✗ | **MISSING** | HIGH |
| T-13 | Email integration | ✓ (_email_integration plugin) | ✗ | **MISSING** | LOW |
| T-14 | Telegram integration | ✓ (_telegram_integration plugin) | ✗ | **MISSING** | LOW |
| T-15 | WhatsApp integration | ✓ (_whatsapp_integration plugin) | ✗ | **MISSING** | LOW |
| T-16 | Text-to-speech | ✓ (_kokoro_tts plugin) | ✓ (voice app) | NONE | — |
| T-17 | Speech-to-text | ✓ (_whisper_stt plugin) | ✓ (voice app) | NONE | — |
| T-18 | MCP (Model Context Protocol) | ✓ (helpers/mcp_handler.py, mcp_server.py) | ✓ (fastmcp dep) | NONE | — |
| T-19 | Parallel tool execution | ✓ (parallel.py, helpers/parallel_tools.py) | ✗ (sequential only) | **MISSING** | MEDIUM |
| T-20 | Tool access control / policy | ✓ (helpers/tool_policy.py) | ✓ (UnifiedGate + OPA) | Soma is BETTER | — |

### 2.3 Web UI / UX

| # | Feature | Agent Zero | Soma Current | Gap | Priority |
|---|---------|------------|--------------|-----|----------|
| U-01 | Chat interface | ✓ (Alpine.js + WebSocket) | ✓ (Lit 3.x + WebSocket) | Different tech | — |
| U-02 | Message streaming (SSE/WS) | ✓ (WebSocket) | ✓ (WebSocket deltas) | NONE | — |
| U-03 | Code syntax highlighting | ✓ (safe-markdown.js) | ✗ | **MISSING** | HIGH |
| U-04 | Markdown rendering | ✓ (safe-markdown.js) | ✗ (basic only) | **MISSING** | HIGH |
| U-05 | File attachments in chat | ✓ (attachments/ component) | ✗ | **MISSING** | HIGH |
| U-06 | Image display in chat | ✓ (images in messages) | ✗ | **MISSING** | MEDIUM |
| U-07 | Chat history / sidebar | ✓ (sidebar/chats/) | ✓ (conversation list) | NONE | — |
| U-08 | Chat branching | ✓ (_chat_branching plugin) | ✗ | **MISSING** | MEDIUM |
| U-09 | Chat export | ✓ (api/chat_export.py) | ✗ | **MISSING** | LOW |
| U-10 | Chat search | ✓ (in sidebar) | ✗ | **MISSING** | MEDIUM |
| U-11 | Canvas panel (right side) | ✓ (browser, desktop, docs, code) | ✗ | **MISSING** | HIGH |
| U-12 | Browser in canvas | ✓ (_browser plugin) | ✗ | **MISSING** | HIGH |
| U-13 | Linux desktop in canvas | ✓ (_desktop plugin, XFCE) | ✗ | **MISSING** | MEDIUM |
| U-14 | Document editor in canvas | ✓ (markdown, spreadsheet, presentation) | ✗ | **MISSING** | HIGH |
| U-15 | Code editor in canvas | ✓ (_editor plugin) | ✗ | **MISSING** | HIGH |
| U-16 | Settings panel | ✓ (13 settings sections) | ✓ (saas-settings.ts) | Agent Zero is RICHER | HIGH |
| U-17 | Model provider setup | ✓ (model_config plugin, gate) | ✗ (no UI) | **MISSING** | CRITICAL |
| U-18 | Plugin marketplace / hub | ✓ (_plugin_installer, discovery) | ✗ | **MISSING** | MEDIUM |
| U-19 | Skills management | ✓ (_skills plugin, skills_cli.py) | ✗ | **MISSING** | MEDIUM |
| U-20 | Secrets management UI | ✓ (secrets/ settings section) | ✗ | **MISSING** | HIGH |
| U-21 | MCP server management | ✓ (mcp/ settings section) | ✗ | **MISSING** | MEDIUM |
| U-22 | Agent profile editor | ✓ (agent/ settings section) | ✗ | **MISSING** | HIGH |
| U-23 | Backup / restore UI | ✓ (backup/ settings section) | ✗ | **MISSING** | MEDIUM |
| U-24 | Time travel (snapshots) | ✓ (_time_travel plugin) | ✗ | **MISSING** | LOW |
| U-25 | Notification system | ✓ (notifications/ component) | ✓ (admin/notifications) | NONE | — |
| U-26 | Dark / light theme | ✓ (CSS themes) | ✓ (theme-store.ts) | NONE | — |
| U-27 | Responsive design | ✗ (desktop-first) | ✗ | BOTH MISSING | LOW |
| U-28 | Login page | ✓ (login.html) | ✓ (saas-login.ts) | NONE | — |
| U-29 | Welcome / onboarding | ✓ (_onboarding plugin, welcome/) | ✗ | **MISSING** | MEDIUM |
| U-30 | What's new / changelog | ✓ (_whats_new plugin) | ✗ | **MISSING** | LOW |

### 2.4 Plugin / Extension System

| # | Feature | Agent Zero | Soma Current | Gap | Priority |
|---|---------|------------|--------------|-----|----------|
| P-01 | Plugin architecture | ✓ (42 plugins, extensible hooks) | ✗ (no plugin system) | **MISSING** | HIGH |
| P-02 | Plugin installer | ✓ (_plugin_installer) | ✗ | **MISSING** | HIGH |
| P-03 | Plugin scanner / validator | ✓ (_plugin_scan, _plugin_validator) | ✗ | **MISSING** | MEDIUM |
| P-04 | Plugin discovery (hub) | ✓ (_discovery) | ✗ | **MISSING** | MEDIUM |
| P-05 | Extension system (hooks) | ✓ (helpers/extension.py, @extensible) | ✗ | **MISSING** | HIGH |
| P-06 | Skills system | ✓ (11 skills, import/export) | ✗ | **MISSING** | HIGH |
| P-07 | Skills CLI | ✓ (helpers/skills_cli.py) | ✗ | **MISSING** | MEDIUM |
| P-08 | Prompt templates | ✓ (75 prompt files, composable) | ✓ (SRS docs, not composable) | Agent Zero is BETTER | HIGH |
| P-09 | Behaviour profiles | ✓ (behaviour/*.md, merge/search) | ✗ | **MISSING** | MEDIUM |
| P-10 | MCP server integration | ✓ (helpers/mcp_server.py) | ✓ (fastmcp dep) | NONE | — |

### 2.5 Infrastructure / DevOps

| # | Feature | Agent Zero | Soma Current | Gap | Priority |
|---|---------|------------|--------------|-----|----------|
| I-01 | Docker deployment | ✓ (single container, `docker run`) | ✓ (docker-compose) | Agent Zero is SIMPLER | HIGH |
| I-02 | One-command start | ✓ (`docker run -p 80:80 agent0ai/agent-zero`) | ✗ (needs env files) | **MISSING** | CRITICAL |
| I-03 | Desktop launcher | ✓ (A0 Launcher for Mac/Linux/Win) | ✗ | **MISSING** | MEDIUM |
| I-04 | CLI installer | ✓ (`curl | bash`) | ✗ | **MISSING** | MEDIUM |
| I-05 | Auto-update | ✓ (_self_update plugin, self_update.py) | ✗ | **MISSING** | MEDIUM |
| I-06 | Backup / restore | ✓ (helpers/backup.py, 6 API endpoints) | ✗ (DR doc only) | **MISSING** | HIGH |
| I-07 | Tunnel (expose to internet) | ✓ (Cloudflare, Serveo, Tailscale, ngrok) | ✗ | **MISSING** | LOW |
| I-08 | Multi-instance support | ✓ (A0 Launcher manages instances) | ✗ | **MISSING** | LOW |
| I-09 | Health checks | ✓ (api/health.py) | ✓ (/api/health/) | NONE | — |
| I-10 | Prometheus metrics | ✗ | ✓ (30+ metric modules) | Soma ADVANTAGE | — |
| I-11 | OpenTelemetry tracing | ✗ | ✓ (1.37.0) | Soma ADVANTAGE | — |
| I-12 | K8s manifests | ✗ | ✓ (deployment, HPA, PDB, netpol) | Soma ADVANTAGE | — |

### 2.6 Projects / Multi-Agent

| # | Feature | Agent Zero | Soma Current | Gap | Priority |
|---|---------|------------|--------------|-----|----------|
| M-01 | Projects (isolated workspaces) | ✓ (helpers/projects.py) | ✗ | **MISSING** | HIGH |
| M-02 | Per-project instructions | ✓ (AGENTS.md per project) | ✗ | **MISSING** | HIGH |
| M-03 | Per-project secrets | ✓ (helpers/secrets.py) | ✗ | **MISSING** | HIGH |
| M-04 | Per-project memory | ✓ (knowledge/main/) | ✓ (Brain + SFM namespaces) | Soma is BETTER | — |
| M-05 | Per-project model presets | ✓ (model_providers.yaml) | ✗ | **MISSING** | MEDIUM |
| M-06 | Subagent spawning | ✓ (helpers/subagents.py) | ✗ | **MISSING** | HIGH |
| M-07 | Multi-agent cooperation | ✓ (call_subordinate, parallel) | ✗ | **MISSING** | HIGH |
| M-08 | Agent-to-agent chat | ✓ (a2a_chat.py) | ✓ (delegation_gateway) | NONE | — |
| M-09 | Work directory management | ✓ (file_browser, upload/download) | ✗ | **MISSING** | HIGH |
| M-10 | File tree visualization | ✓ (helpers/file_tree.py) | ✗ | **MISSING** | MEDIUM |

---

## 3. GAP SUMMARY

### 3.1 CRITICAL Gaps (Must Have for Standalone)

| # | Gap | What Agent Zero Has | Effort |
|---|-----|---------------------|--------|
| GAP-C01 | One-command Docker start | `docker run -p 80:80 agent0ai/agent-zero` | 1 week |
| GAP-C02 | Model provider setup UI | Settings → Model Config with API key entry | 1 week |
| GAP-C03 | Chat UI with markdown + code | safe-markdown.js, code highlighting | 1 week |
| GAP-C04 | File operations tool | helpers/files.py, upload/download | 3 days |
| GAP-C05 | Git operations tool | helpers/git.py | 2 days |
| GAP-C06 | Canvas panel (browser/docs/code) | Right-side panel with multiple surfaces | 2 weeks |
| GAP-C07 | Plugin system | 42 plugins, extensible hooks, installer | 3 weeks |
| GAP-C08 | Skills system | 11 skills, import/export, CLI | 2 weeks |
| GAP-C09 | Projects (isolated workspaces) | Per-project instructions, secrets, memory | 2 weeks |
| GAP-C10 | Subagent delegation | call_subordinate, parallel execution | 1 week |

### 3.2 HIGH Gaps (Important for Product)

| # | Gap | Effort |
|---|-----|--------|
| GAP-H01 | File attachments in chat | 1 week |
| GAP-H02 | Secrets management UI | 3 days |
| GAP-H03 | Agent profile editor | 3 days |
| GAP-H04 | Backup / restore UI | 1 week |
| GAP-H05 | Chat branching | 3 days |
| GAP-H06 | Document editor in canvas | 1 week |
| GAP-H07 | Code editor in canvas | 1 week |
| GAP-H08 | Browser automation in canvas | 2 weeks |
| GAP-H09 | Prompt template system (composable) | 1 week |
| GAP-H10 | Extension / hook system | 2 weeks |

### 3.3 MEDIUM Gaps (Nice to Have)

| # | Gap | Effort |
|---|-----|--------|
| GAP-M01 | Chat export | 1 day |
| GAP-M02 | Chat search | 2 days |
| GAP-M03 | Plugin marketplace / hub | 2 weeks |
| GAP-M04 | Onboarding wizard | 1 week |
| GAP-M05 | Time travel / snapshots | 1 week |
| GAP-M06 | Linux desktop in canvas | 2 weeks |
| GAP-M07 | Notification to user tool | 1 day |
| GAP-M08 | Parallel tool execution | 3 days |

---

## 4. WHAT SOMA HAS THAT AGENT ZERO DOESN'T

| # | Feature | Soma Advantage |
|---|---------|----------------|
| S-01 | Cognitive memory (SomaBrain) — HRR vectors, neuromodulators, sleep consolidation | Unique scientific architecture |
| S-02 | Fractal vector memory (SFM) — coordinate-based, graph relationships | Unique storage model |
| S-03 | Multi-tenancy with tenant isolation | Enterprise requirement |
| S-04 | Keycloak OIDC + LDAP/AD/SSO | Enterprise auth |
| S-05 | SpiceDB Zanzibar-style authorization | Enterprise authz |
| S-06 | OPA policy engine | Enterprise policy |
| S-07 | Prometheus + OpenTelemetry observability | Production monitoring |
| S-08 | K8s production manifests (HPA, PDB, netpol) | Production deployment |
| S-09 | Billing integration (Lago) | Enterprise billing |
| S-10 | Circuit breaker pattern | Production resilience |
| S-11 | ISO-compliant documentation (9 standards) | Enterprise compliance |
| S-12 | Transactional outbox pattern | Data reliability |

---

## 5. RECOMMENDATION: TWO-MODE ARCHITECTURE

### Standalone Mode (Agent Zero style)
```
docker run -p 80:80 soma/agent
```
- Simple email/password auth (no Keycloak)
- SQLite or embedded PostgreSQL
- Single user, single agent
- All Agent Zero features (tools, plugins, canvas, browser, desktop)
- SomaBrain embedded (in-process, no separate service)
- SFM embedded (local Milvus or pgvector)

### Enterprise Mode (AAAS)
```
docker compose -f docker-compose.aaas.yml up -d
```
- Keycloak + LDAP/AD/SSO
- PostgreSQL + Redis + Kafka + Milvus
- Multi-tenant, multi-agent
- All Soma enterprise features (billing, OPA, SpiceDB, Vault)
- SomaBrain as separate service
- SFM as separate service
- K8s deployment with full observability

### Shared Core (Same in Both Modes)
- V3 Chat Orchestrator (12-phase pipeline)
- Memory system (Brain + SFM)
- Tool execution engine
- Plugin system
- Skills system
- Prompt template system
- Web UI components

---

End of Document
