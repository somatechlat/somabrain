# SOMA AGENT — MODULE SYSTEM TECHNICAL SPECIFICATION

## Document Control

| Field | Value |
|---|---|
| Document Title | Soma Agent Module System Technical Specification |
| Document Identifier | SOMA-MOD-SPEC-001 |
| Version | 1.0.0 |
| Date | 2026-06-15 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | — |
| Classification | Internal |
| ISO Reference | ISO 9001:2015 — Quality Management Systems — Requirements |
| Next Review | 2026-12-28 |
## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-09-28 | SomaTech Engineering | Document control normalised: prior status `Baseline` normalised to `Draft` (no approver named). |


## 1. MODULE CATALOG

### 1.1 Complete Module Inventory

| Module ID | Name | Category | Default | Dependencies | Conflicts With | Provides |
|-----------|------|----------|---------|-------------|----------------|----------|
| `core.chat` | Chat Engine | Core | ON (locked) | — | — | V3 orchestrator, WebSocket, REST chat |
| `core.memory` | Memory System | Core | ON (locked) | — | — | SomaBrain + SFM integration |
| `core.auth` | Basic Auth | Core | ON (locked) | — | — | Email/password, JWT, sessions |
| `core.config` | Configuration | Core | ON (locked) | — | — | Settings registry, env vars |
| `core.tools` | Tool Executor | Core | ON (locked) | — | — | Sandboxed tool execution |
| `core.webui` | Web UI | Core | ON (locked) | — | — | Lit 3.x frontend, all core screens |
| `core.health` | Health Monitor | Core | ON (locked) | — | — | Health endpoints, basic metrics |
| `core.logging` | Structured Logging | Core | ON (locked) | — | — | JSON logging, log levels |
| `auth.keycloak` | Keycloak SSO | Auth | OFF | PostgreSQL | auth.ldap | OIDC, realm management |
| `auth.ldap` | LDAP/AD | Auth | OFF | — | auth.keycloak | LDAP authentication |
| `auth.sso` | SAML/SSO | Auth | OFF | — | — | SAML authentication |
| `authz.opa` | OPA Policy Engine | Authz | OFF | — | — | Policy evaluation |
| `authz.spicedb` | SpiceDB | Authz | OFF | — | — | Zanzibar permissions |
| `billing` | Billing | Enterprise | OFF | PostgreSQL, auth.keycloak | — | Lago integration, usage tracking |
| `secrets.vault` | Vault Secrets | Enterprise | OFF | — | — | Secret management |
| `events.kafka` | Kafka Events | Enterprise | OFF | — | — | Event streaming |
| `workflows.temporal` | Temporal Workflows | Enterprise | OFF | — | — | Workflow orchestration |
| `audit` | Audit Logging | Enterprise | OFF | PostgreSQL | — | Complete audit trail |
| `analytics` | Analytics | Enterprise | OFF | PostgreSQL | — | Usage analytics |
| `tools.browser` | Browser Automation | Tools | OFF | Chromium | — | Web browsing, DOM interaction |
| `tools.desktop` | Linux Desktop | Tools | OFF | XFCE, VNC | — | Desktop apps in canvas |
| `plugins` | Plugin System | Tools | OFF | — | — | Plugin install/management |
| `skills` | Skills System | Tools | OFF | plugins | — | Skill import/export/CLI |
| `tools.mcp` | MCP Integration | Tools | OFF | — | — | MCP server management |
| `voice.tts` | Text-to-Speech | Voice | OFF | Kokoro | — | Speech synthesis |
| `voice.stt` | Speech-to-Text | Voice | OFF | Whisper | — | Speech recognition |
| `integrations.email` | Email | Integration | OFF | SMTP | — | Email sending |
| `integrations.telegram` | Telegram | Integration | OFF | Bot token | — | Telegram bot |
| `integrations.whatsapp` | WhatsApp | Integration | OFF | WhatsApp API | — | WhatsApp messaging |

---

## 2. MODULE LIFECYCLE

### 2.1 State Machine

```
                    ┌──────────────┐
                    │  DISCOVERED  │
                    └──────┬───────┘
                           │ initialize()
                           ▼
                    ┌──────────────┐
                    │ INITIALIZING │
                    └──────┬───────┘
                           │
                    ┌──────┴───────┐
                    │              │
                    ▼              ▼
             ┌──────────┐   ┌──────────┐
             │ RUNNING  │   │  FAILED  │
             └────┬─────┘   └──────────┘
                  │
           ┌──────┴───────┐
           │              │
           ▼              ▼
    ┌────────────┐  ┌────────────┐
    │  DEGRADED  │  │  STOPPED   │
    └──────┬─────┘  └────────────┘
           │
           ▼
    ┌────────────┐
    │ RECOVERING │
    └────────────┘
```

### 2.2 Lifecycle Hooks

| Hook | When Called | Can Fail? | Effect of Failure |
|------|------------|-----------|-------------------|
| `initialize()` | Once at startup, after dependencies are RUNNING | Yes | Module marked FAILED, not started |
| `start()` | After initialize(), when all deps are RUNNING | Yes | Module marked FAILED |
| `health_check()` | Every 15 seconds while RUNNING | No (returns health object) | If unhealthy → DEGRADED |
| `on_dependency_state_change()` | When a dependency changes state | No (best effort) | Logged, module decides action |
| `stop()` | At shutdown, in reverse dependency order | No (best effort) | Logged, shutdown continues |

---

## 3. DEPENDENCY RESOLUTION

### 3.1 Dependency Graph

```
core.chat
├── core.memory
├── core.auth
├── core.config
├── core.tools
└── core.health

core.memory
├── core.config
└── core.health

auth.keycloak
├── core.auth
└── PostgreSQL (external)

authz.opa
├── core.auth
└── OPA server (external)

authz.spicedb
├── core.auth
└── SpiceDB server (external)

billing
├── core.auth
├── auth.keycloak
└── PostgreSQL (external)

audit
├── core.auth
└── PostgreSQL (external)

plugins
└── core.config

skills
└── plugins
```

### 3.2 Resolution Algorithm (Kahn's Topological Sort)

```
1. Build adjacency list from module.dependencies
2. Calculate in-degree for each module
3. Queue modules with in-degree 0 (no dependencies)
4. Process queue:
   a. Dequeue module
   b. Add to initialization order
   c. Decrement in-degree of all dependents
   d. If dependent's in-degree reaches 0, enqueue it
5. If processed count < total count → circular dependency error
6. Initialize modules in order
```

---

## 4. CONFIGURATION

### 4.1 Environment Variables

```bash
# Profile preset (optional)
SOMA_PROFILE=standalone|enterprise|full|custom

# Individual modules (comma-separated, overrides profile)
SOMA_MODULES=billing,auth.keycloak,audit

# Module-specific config
SOMA_BILLING_LAGO_URL=http://lago:3000
SOMA_KEYCLOAK_URL=http://keycloak:8080
SOMA_OPA_URL=http://opa:8181
SOMA_SPICEDB_HOST=spicedb
SOMA_VAULT_ADDR=http://vault:8200
SOMA_KAFKA_BOOTSTRAP_SERVERS=kafka:9092
```

### 4.2 Settings UI API

```
GET  /api/v2/settings/modules              → List all modules with state
POST /api/v2/settings/modules/{id}/enable  → Enable a module
POST /api/v2/settings/modules/{id}/disable → Disable a module (core blocked)
GET  /api/v2/settings/modules/{id}/health  → Module health detail
POST /api/v2/settings/modules/profile      → Apply a profile preset
```

### 4.3 Settings UI Response Format

```json
{
  "modules": [
    {
      "id": "core.chat",
      "name": "Chat Engine",
      "category": "core",
      "state": "running",
      "enabled": true,
      "locked": true,
      "version": "1.0.0",
      "health": {"healthy": true, "message": "OK"},
      "description": "V3 12-phase orchestrator, WebSocket streaming",
      "dependencies": [],
      "config_schema": {}
    },
    {
      "id": "billing",
      "name": "Billing",
      "category": "enterprise",
      "state": "stopped",
      "enabled": false,
      "locked": false,
      "version": "1.0.0",
      "health": null,
      "description": "Lago integration, usage tracking, invoicing",
      "dependencies": ["core.auth", "auth.keycloak"],
      "config_schema": {
        "lago_url": {"type": "string", "required": true},
        "lago_api_key": {"type": "string", "required": true, "secret": true}
      }
    }
  ],
  "active_profile": "standalone",
  "available_profiles": ["standalone", "enterprise", "full", "custom"]
}
```

---

## 5. MODULE IMPLEMENTATION TEMPLATE

### 5.1 Standard Module Structure

```
modules/
├── billing/
│   ├── __init__.py          # Module class definition
│   ├── service.py           # Business logic
│   ├── api.py               # API endpoints (auto-registered when module enabled)
│   ├── models.py            # Data models (auto-migrated when module enabled)
│   ├── tasks.py             # Background tasks
│   └── README.md            # Module documentation
├── auth/
│   ├── keycloak/
│   │   ├── __init__.py
│   │   ├── service.py
│   │   └── api.py
│   └── ldap/
│       ├── __init__.py
│       └── service.py
└── ...
```

### 5.2 Module Implementation Example

```python
# modules/billing/__init__.py
from core.module import Module, ModuleHealth, ModuleState, ModuleInitError

class BillingModule(Module):
    name = "billing"
    version = "1.0.0"
    dependencies = ["core.auth", "auth.keycloak"]
    conflicts_with = []

    async def initialize(self) -> None:
        """Set up database tables, connect to Lago API."""
        from .service import BillingService
        self._service = BillingService()
        await self._service.connect()
        # Auto-register API routes
        self._register_routes()

    async def start(self) -> None:
        """Start background billing metering task."""
        await self._service.start_metering()

    async def stop(self) -> None:
        """Stop metering, flush pending records."""
        await self._service.stop_metering()

    async def health_check(self) -> ModuleHealth:
        """Check Lago API connectivity."""
        try:
            ok = await self._service.ping()
            return ModuleHealth(
                healthy=ok,
                state=ModuleState.RUNNING if ok else ModuleState.DEGRADED,
                message="Lago API reachable" if ok else "Lago API unreachable",
            )
        except Exception as e:
            return ModuleHealth(
                healthy=False,
                state=ModuleState.DEGRADED,
                message=str(e),
            )

    async def on_dependency_state_change(self, dependency: str, new_state: ModuleState) -> None:
        """React to dependency state changes."""
        if dependency == "auth.keycloak" and new_state == ModuleState.FAILED:
            # Keycloak down — billing can still work for API-key auth
            pass

    def _register_routes(self) -> None:
        """Register billing API routes on the master router."""
        from admin.api import master_router
        from .api import router
        master_router.add_router("/billing", router)
```

---

## 6. MIGRATION STRATEGY

### 6.1 Database Migrations per Module

When a module is enabled:
1. Module's `models.py` is discovered
2. Django migrations are generated (if needed)
3. Migrations are applied
4. Module's API routes are registered

When a module is disabled:
1. Module's API routes are unregistered
2. Module's `stop()` is called
3. Database tables are preserved (not dropped)
4. Module state changes to STOPPED

### 6.2 Zero-Downtime Module Toggle

```
Enable module:
  1. Register module in registry
  2. Run migrations (if needed)
  3. Initialize module
  4. Start module
  5. Register API routes
  6. Module is live

Disable module:
  1. Unregister API routes (new requests rejected)
  2. Wait for in-flight requests to complete (30s timeout)
  3. Call module.stop()
  4. Module is stopped
  5. Database tables preserved
```

---

## 7. MONITORING

### 7.1 Module Health Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│ System Health                                    Refresh: 15s │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  CORE                                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Chat 🟢  │ │ Memory 🟢│ │ Auth 🟢  │ │ Tools 🟢 │       │
│  │ 12ms     │ │ 5ms      │ │ 2ms      │ │ 8ms      │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│                                                              │
│  MODULES                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Bill 🟢  │ │ OPA 🟢   │ │ Audit 🟢 │ │ Kafka 🟡 │       │
│  │ 45ms     │ │ 15ms     │ │ 3ms      │ │ degraded │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│                                                              │
│  Uptime: 14d 6h 32m    Requests: 1.2M    Errors: 0.01%      │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Prometheus Metrics per Module

```
# Module state
soma_module_state{module="billing"} 1  # 1=running, 0=stopped, -1=failed

# Module health check latency
soma_module_health_latency_seconds{module="billing"} 0.045

# Module request count
soma_module_requests_total{module="billing", endpoint="/api/v2/billing/usage"} 1234

# Module error count
soma_module_errors_total{module="billing"} 5
```

---

End of Document
