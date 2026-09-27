# SOMA AGENT — MODULAR ARCHITECTURE SPECIFICATION

## Document Control

| Field | Value |
|-------|-------|
| Document Title | Soma Agent Modular Architecture — Core vs Optional Modules |
| Document Identifier | SOMA-MOD-ARCH-001 |
| Version | 1.0.0 |
| Date | 2026-06-15 |
| Status | Active |

---

## 1. PRINCIPLE

**Core is always there. Everything else is a module you can turn on or off.**

```
┌──────────────────────────────────────────────────────────────┐
│                         SOMA AGENT                            │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    CORE (always on)                      │ │
│  │  Chat · Memory · Tools · UI · Auth (basic) · Config     │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ Billing  │ │ LDAP/AD  │ │ OPA      │ │ SpiceDB  │        │
│  │ [OFF]    │ │ [OFF]    │ │ [OFF]    │ │ [OFF]    │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ Vault    │ │ Kafka    │ │ Temporal │ │ SSO/SAML │        │
│  │ [OFF]    │ │ [OFF]    │ │ [OFF]    │ │ [OFF]    │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ Browser  │ │ Desktop  │ │ Plugins  │ │ Skills   │        │
│  │ [OFF]    │ │ [OFF]    │ │ [OFF]    │ │ [OFF]    │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
│                                                               │
│  Enable/disable via settings: SOMA_MODULES=billing,opa,plugins│
└──────────────────────────────────────────────────────────────┘
```

---

## 2. MODULE CATALOG

### 2.1 Core Modules (Always On, Cannot Disable)

| Module | ID | Description |
|--------|----|-------------|
| Chat Engine | `core.chat` | V3 12-phase orchestrator, WebSocket streaming |
| Memory | `core.memory` | SomaBrain + SomaFractalMemory integration |
| Basic Auth | `core.auth` | Email/password, JWT tokens, sessions |
| Configuration | `core.config` | Settings registry, env vars |
| Tool Executor | `core.tools` | Sandboxed tool execution |
| Web UI | `core.webui` | Lit 3.x frontend |
| Health | `core.health` | Health endpoints, basic monitoring |
| Logging | `core.logging` | Structured JSON logging |

### 2.2 Optional Modules (Enable via Settings)

| Module | ID | Default | Requires |
|--------|----|---------|----------|
| **Billing** | `billing` | OFF | PostgreSQL, Lago API |
| **LDAP/AD Auth** | `auth.ldap` | OFF | LDAP server |
| **SSO/SAML** | `auth.sso` | OFF | SAML IdP |
| **Keycloak** | `auth.keycloak` | OFF | Keycloak server |
| **OPA Authorization** | `authz.opa` | OFF | OPA server |
| **SpiceDB Authorization** | `authz.spicedb` | OFF | SpiceDB server |
| **Vault Secrets** | `secrets.vault` | OFF | Vault server |
| **Kafka Events** | `events.kafka` | OFF | Kafka broker |
| **Temporal Workflows** | `workflows.temporal` | OFF | Temporal server |
| **Browser Automation** | `tools.browser` | OFF | Chromium |
| **Linux Desktop** | `tools.desktop` | OFF | XFCE + VNC |
| **Plugin System** | `plugins` | OFF | — |
| **Skills System** | `skills` | OFF | — |
| **MCP Integration** | `tools.mcp` | OFF | MCP servers |
| **TTS (Text-to-Speech)** | `voice.tts` | OFF | Kokoro |
| **STT (Speech-to-Text)** | `voice.stt` | OFF | Whisper |
| **Email Integration** | `integrations.email` | OFF | SMTP |
| **Telegram** | `integrations.telegram` | OFF | Bot token |
| **WhatsApp** | `integrations.whatsapp` | OFF | WhatsApp API |
| **Analytics** | `analytics` | OFF | — |
| **Audit Logging** | `audit` | OFF | PostgreSQL |

---

## 3. CONFIGURATION

### 3.1 Environment Variable

```bash
# Comma-separated list of modules to enable
SOMA_MODULES=billing,auth.keycloak,authz.opa,audit

# Or use a preset
SOMA_PROFILE=standalone    # core only
SOMA_PROFILE=enterprise    # all enterprise modules
SOMA_PROFILE=full          # everything
```

### 3.2 Profile Presets

| Profile | Modules Enabled |
|---------|----------------|
| `standalone` | core.* only |
| `enterprise` | core.* + billing + auth.keycloak + authz.opa + authz.spicedb + secrets.vault + events.kafka + audit |
| `full` | Everything |
| `custom` | User-defined via SOMA_MODULES |

### 3.3 Settings UI

The admin settings page shows all modules with toggle switches:

```
┌─────────────────────────────────────────────────────────────┐
│  Settings → Modules                                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  CORE (always on)                                            │
│  ├── Chat Engine                    ● Enabled (locked)       │
│  ├── Memory                         ● Enabled (locked)       │
│  ├── Basic Auth                     ● Enabled (locked)       │
│  └── Web UI                         ● Enabled (locked)       │
│                                                              │
│  AUTHENTICATION                                              │
│  ├── Keycloak SSO                   ○ Disabled    [Enable]   │
│  ├── LDAP / Active Directory        ○ Disabled    [Enable]   │
│  └── SAML                           ○ Disabled    [Enable]   │
│                                                              │
│  AUTHORIZATION                                               │
│  ├── OPA Policy Engine              ○ Disabled    [Enable]   │
│  └── SpiceDB                        ○ Disabled    [Enable]   │
│                                                              │
│  ENTERPRISE                                                  │
│  ├── Billing (Lago)                 ○ Disabled    [Enable]   │
│  ├── Vault Secrets                  ○ Disabled    [Enable]   │
│  ├── Audit Logging                  ○ Disabled    [Enable]   │
│  └── Analytics                      ○ Disabled    [Enable]   │
│                                                              │
│  TOOLS                                                       │
│  ├── Browser Automation             ○ Disabled    [Enable]   │
│  ├── Linux Desktop                  ○ Disabled    [Enable]   │
│  ├── Plugin System                  ○ Disabled    [Enable]   │
│  └── Skills System                  ○ Disabled    [Enable]   │
│                                                              │
│  INTEGRATIONS                                                │
│  ├── Kafka Events                   ○ Disabled    [Enable]   │
│  ├── Temporal Workflows             ○ Disabled    [Enable]   │
│  ├── Email (SMTP)                   ○ Disabled    [Enable]   │
│  └── Telegram Bot                   ○ Disabled    [Enable]   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. IMPLEMENTATION

### 4.1 Module Registry

```python
# core/modules.py

from enum import Enum
from typing import Set

class Module(Enum):
    # Core (always on)
    CHAT = "core.chat"
    MEMORY = "core.memory"
    AUTH = "core.auth"
    CONFIG = "core.config"
    TOOLS = "core.tools"
    WEBUI = "core.webui"
    HEALTH = "core.health"
    LOGGING = "core.logging"
    
    # Optional
    BILLING = "billing"
    AUTH_LDAP = "auth.ldap"
    AUTH_SSO = "auth.sso"
    AUTH_KEYCLOAK = "auth.keycloak"
    AUTHZ_OPA = "authz.opa"
    AUTHZ_SPICEDB = "authz.spicedb"
    SECRETS_VAULT = "secrets.vault"
    EVENTS_KAFKA = "events.kafka"
    WORKFLOWS_TEMPORAL = "workflows.temporal"
    TOOLS_BROWSER = "tools.browser"
    TOOLS_DESKTOP = "tools.desktop"
    PLUGINS = "plugins"
    SKILLS = "skills"
    TOOLS_MCP = "tools.mcp"
    VOICE_TTS = "voice.tts"
    VOICE_STT = "voice.stt"
    INTEGRATIONS_EMAIL = "integrations.email"
    INTEGRATIONS_TELEGRAM = "integrations.telegram"
    INTEGRATIONS_WHATSAPP = "integrations.whatsapp"
    ANALYTICS = "analytics"
    AUDIT = "audit"

# Core modules that cannot be disabled
CORE_MODULES = {Module.CHAT, Module.MEMORY, Module.AUTH, Module.CONFIG,
                Module.WEBUI, Module.TOOLS, Module.HEALTH, Module.LOGGING}

# Profile presets
PROFILES = {
    "standalone": set(),  # core only
    "enterprise": {Module.BILLING, Module.AUTH_KEYCLOAK, Module.AUTHZ_OPA,
                   Module.AUTHZ_SPICEDB, Module.SECRETS_VAULT, Module.EVENTS_KAFKA,
                   Module.AUDIT},
    "full": set(Module) - CORE_MODULES,  # everything
}

class ModuleRegistry:
    _enabled: Set[Module] = CORE_MODULES.copy()
    
    @classmethod
    def load(cls, profile: str = "standalone", extra: str = ""):
        """Load modules from profile + extra comma-separated modules."""
        cls._enabled = CORE_MODULES | PROFILES.get(profile, set())
        if extra:
            for mod in extra.split(","):
                mod = mod.strip()
                try:
                    cls._enabled.add(Module(mod))
                except ValueError:
                    pass
    
    @classmethod
    def is_enabled(cls, module: Module) -> bool:
        return module in cls._enabled
    
    @classmethod
    def enable(cls, module: Module):
        cls._enabled.add(module)
    
    @classmethod
    def disable(cls, module: Module):
        if module in CORE_MODULES:
            raise ValueError(f"Cannot disable core module: {module}")
        cls._enabled.discard(module)
```

### 4.2 Conditional Imports

```python
# Usage in code:
from core.modules import ModuleRegistry, Module

if ModuleRegistry.is_enabled(Module.BILLING):
    from enterprise.billing import BillingService
    
if ModuleRegistry.is_enabled(Module.AUTH_KEYCLOAK):
    from enterprise.auth.keycloak import KeycloakAuth
else:
    from core.auth.simple import EmailPasswordAuth
```

### 4.3 Settings UI Toggle

```typescript
// webui/components/settings/modules.ts
// Each module toggle calls:
// POST /api/v2/settings/modules/{module_id} { "enabled": true/false }
// Backend validates: core modules cannot be disabled
```

---

## 5. DEPLOYMENT PRESETS

### 5.1 Standalone

```yaml
# docker-compose.standalone.yml
environment:
  SOMA_PROFILE: standalone
  # No enterprise modules
```

Starts with: Chat, Memory (embedded), Basic Auth, Tools, UI

### 5.2 Enterprise (Default)

```yaml
# docker-compose.enterprise.yml
environment:
  SOMA_PROFILE: enterprise
  SOMA_MODULES: auth.keycloak,authz.opa,billing,audit
```

Starts with: Everything except browser/desktop/plugins/skills

### 5.3 Full

```yaml
# docker-compose.full.yml
environment:
  SOMA_PROFILE: full
```

Starts with: Everything enabled

---

End of Document
