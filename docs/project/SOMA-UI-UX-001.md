# SOMA AGENT — UI/UX SPECIFICATION

## Document Control

| Field | Value |
|---|---|
| Document Title | Soma Agent UI/UX Complete Specification |
| Document Identifier | SOMA-UI-UX-001 |
| Version | 1.0.1 |
| Date | 2026-06-15 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | — |
| Classification | Internal |
| ISO Reference | ISO 9241-210:2019 — Human-centred design processes for interactive systems |
| Next Review | 2026-12-28 |

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-06-15 | SomaTech Engineering | Initial complete UI/UX specification — all screens, journeys, modules |
| 1.0.1 | 2026-09-28 | SomaTech Engineering | Document control normalised: prior status `Baseline` normalised to `Draft` (no approver named). |
| 1.0.2 | 2026-10-07 | SomaTech Engineering | Model settings hub: card-based full-model admin per SOMA-UI-MODEL-ADMIN-001. |
| 1.0.3 | 2026-10-07 | SomaTech Engineering | Cross-link FIELD-PARITY-001 + MODEL-ADMIN-001; Settings suite; no slot language. |

---

## 1. DESIGN PRINCIPLES

### 1.1 Core Principles

| # | Principle | Description |
|---|-----------|-------------|
| P-01 | **Chat is primary** | The chat interface is the hero. Everything else is secondary. |
| P-02 | **Canvas is context** | Right panel shows what the agent is doing — browser, docs, code, desktop. |
| P-03 | **Settings are progressive** | Simple by default. Advanced settings revealed on demand. |
| P-04 | **Modules are visual** | Every module shows as a card with status, toggle, and config. |
| P-05 | **Two modes, one UI** | Standalone and Enterprise share the same UI. Enterprise adds panels, never removes them. |
| P-06 | **Dark first** | Dark theme default. Light theme available. |
| P-07 | **Keyboard first** | Power users navigate with keyboard. Mouse is optional. |
| P-08 | **Mobile aware** | Not mobile-first, but responsive enough to work on tablets. |

### 1.2 Design System

| Element | Value |
|---------|-------|
| Framework | Lit 3.x Web Components (VIBE mandate) |
| Typography | Inter (body), JetBrains Mono (code) |
| Colors | Dark: #0a0a0a bg, #ffffff text, #3b82f6 accent |
| Spacing | 4px grid system (4, 8, 12, 16, 24, 32, 48, 64) |
| Border radius | 8px (cards), 6px (buttons), 4px (inputs) |
| Shadows | Subtle: 0 1px 3px rgba(0,0,0,0.3) |
| Icons | Material Symbols Outlined |

---

## 2. SCREEN MAP

### 2.1 Complete Screen Inventory

```
SOMA AGENT SCREENS
├── PUBLIC (no auth)
│   ├── /login                          — Login page
│   ├── /register                       — Registration page
│   ├── /forgot-password                — Password reset request
│   ├── /reset-password/:token          — Password reset form
│   └── /auth/callback                  — OAuth/SSO callback
│
├── CORE (always available)
│   ├── /chat                           — Main chat interface (HERO SCREEN)
│   ├── /chat/:conversation_id          — Specific conversation
│   ├── /agents                         — Agent list
│   ├── /agents/:id                     — Agent detail
│   ├── /agents/create                  — Create agent wizard
│   ├── /settings                       — Settings hub
│   ├── /settings/model                 — Model provider configuration
│   ├── /settings/agent                 — Agent personality & prompt
│   ├── /settings/tools                 — Tool management
│   ├── /settings/ui                    — UI preferences (theme, language)
│   └── /profile                        — User profile
│
├── MODULES (enabled via settings)
│   ├── /settings/modules               — Module manager (toggle on/off)
│   ├── /settings/billing               — Billing configuration (billing module)
│   ├── /settings/auth                  — Auth providers config (keycloak/ldap/sso modules)
│   ├── /settings/authz                 — Authorization config (opa/spicedb modules)
│   ├── /settings/secrets               — Secrets management (vault module)
│   ├── /settings/events                — Event streaming config (kafka module)
│   ├── /settings/workflows             — Workflow config (temporal module)
│   ├── /settings/plugins               — Plugin marketplace (plugins module)
│   ├── /settings/skills                — Skills manager (skills module)
│   ├── /settings/mcp                   — MCP server manager (mcp module)
│   ├── /settings/voice                 — Voice config (tts/stt modules)
│   ├── /settings/integrations          — Third-party integrations
│   ├── /settings/audit                 — Audit log viewer (audit module)
│   └── /settings/analytics             — Analytics dashboard (analytics module)
│
├── CANVAS SURFACES (right panel in chat)
│   ├── Canvas/Browser                  — Embedded browser
│   ├── Canvas/Code                     — Code editor
│   ├── Canvas/Document                 — Document editor (markdown, spreadsheet)
│   ├── Canvas/Desktop                  — Linux desktop (VNC)
│   ├── Canvas/FileBrowser              — File tree + preview
│   └── Canvas/Terminal                 — Terminal emulator
│
└── ADMIN (enterprise only)
    ├── /admin                          — Admin dashboard
    ├── /admin/tenants                  — Tenant management
    ├── /admin/users                    — User management
    ├── /admin/agents                   — All agents across tenants
    ├── /admin/billing                  — Billing overview
    ├── /admin/security                 — Security dashboard
    └── /admin/system                   — System health & modules
```

---

## 3. SCREEN SPECIFICATIONS

### 3.1 LOGIN PAGE (/login)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│                          SOMA                                    │
│                   Cognitive AI Agent                              │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                                                            │  │
│  │  Email                                                     │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │ user@company.com                                     │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                            │  │
│  │  Password                                    👁             │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │ ••••••••••••                                       │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                            │  │
│  │  ☐ Remember me                     Forgot password?        │  │
│  │                                                            │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │                      Sign in                         │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                            │  │
│  │  ─────────────── or continue with ───────────────         │  │
│  │                                                            │  │
│  │  [ Google ]  [ Microsoft ]  [ SAML ]  [ LDAP ]            │  │
│  │                                                            │  │
│  │  Don't have an account? Sign up                            │  │
│  │                                                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│              Powered by SomaTech                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Behavior:**
- Email field: type="email", autocomplete="email"
- Password field: type="password" with eye toggle (show/hide)
- SSO buttons: only shown if respective module is enabled
- Sign in: POST /api/v2/auth/login → redirect to /chat
- Error: inline error message below form (not toast)

---

### 3.2 CHAT PAGE (/chat) — THE HERO SCREEN

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ┌──────────┐                                        ┌─────────────────────┐│
│ │ ☰ SOMA   │  Soma Assistant    🟢 Online    ⚙️  👤 │                     ││
│ ├──────────┤                                        │                     ││
│ │          │                                        │    CANVAS            ││
│ │ CHATS    │  ┌──────────────────────────────────┐  │    (Right Panel)     ││
│ │          │  │                                  │  │                     ││
│ │ ▸ Conv 1 │  │  🤖 Hello! I'm Soma, your AI   │  │  ┌───────────────┐  ││
│ │   Conv 2 │  │     assistant. How can I help?  │  │  │               │  ││
│ │   Conv 3 │  │                                  │  │  │  Browser      │  ││
│ │          │  │  👤 Can you help me analyze      │  │  │  Code Editor  │  ││
│ │          │  │     this data?                   │  │  │  Documents    │  ││
│ │          │  │                                  │  │  │  Terminal     │  ││
│ │          │  │  🤖 Of course! I can help with  │  │  │  Files        │  ││
│ │          │  │     data analysis. Please share  │  │  │  Desktop      │  ││
│ │          │  │     the file or paste the data.  │  │  │               │  ││
│ │          │  │                                  │  │  │  [Content]    │  ││
│ │          │  │  ```python                       │  │  │               │  ││
│ │          │  │  import pandas as pd             │  │  │               │  ││
│ │          │  │  df = pd.read_csv('data.csv')    │  │  │               │  ││
│ │          │  │  print(df.describe())            │  │  │               │  ││
│ │          │  │  ```                             │  │  │               │  ││
│ │          │  │                                  │  │  └───────────────┘  ││
│ │          │  └──────────────────────────────────┘  │                     ││
│ │          │                                        │                     ││
│ │ + New    │  ┌──────────────────────────────────┐  │                     ││
│ │          │  │ 📎 Ask anything...          ➤   │  │                     ││
│ │          │  └──────────────────────────────────┘  │                     ││
│ └──────────┘                                        └─────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

**Components:**
- **Left Sidebar** (240px, collapsible): Chat history, New Chat button, search
- **Chat Area** (flex): Message list with markdown rendering, code blocks, images
- **Right Canvas** (400px, collapsible): Tabbed surface (Browser/Code/Docs/Terminal/Files/Desktop)
- **Top Bar**: Agent name, status indicator, settings gear, user avatar
- **Input Bar**: File attachment, text input, send button, voice button

**Message Types:**
- Text (markdown rendered)
- Code (syntax highlighted, copy button, run button)
- Image (inline display, click to expand)
- File (download link, preview)
- Tool call (collapsible: tool name, input, output)
- Error (red border, retry button)
- Thinking (animated dots, cancellable)

**Keyboard Shortcuts:**
| Key | Action |
|-----|--------|
| Enter | Send message |
| Shift+Enter | New line |
| Ctrl+Enter | Send (alternative) |
| Ctrl+N | New conversation |
| Ctrl+K | Search conversations |
| Ctrl+B | Toggle sidebar |
| Ctrl+J | Toggle canvas |
| Ctrl+/ | Show shortcuts |
| Escape | Cancel current generation |

---

### 3.3 AGENT LIST (/agents)

```
┌─────────────────────────────────────────────────────────────────┐
│ ☰ SOMA   Agents                                    👤          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Your Agents                                    [+ Create Agent] │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 🤖 Soma Assistant              groq/openai/gpt-oss-120b │    │
│  │    AI assistant powered by Groq                          │    │
│  │    Created: Jun 15, 2026    Conversations: 3             │    │
│  │                                        [Chat] [Edit] [⋮] │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 🤖 Code Assistant              openai/gpt-4o             │    │
│  │    Specialized in code generation and review             │    │
│  │    Created: Jun 10, 2026    Conversations: 12            │    │
│  │                                        [Chat] [Edit] [⋮] │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 🤖 Research Agent              anthropic/claude-sonnet   │    │
│  │    Deep research and analysis                            │    │
│  │    Created: Jun 8, 2026     Conversations: 7             │    │
│  │                                        [Chat] [Edit] [⋮] │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3.4 CREATE AGENT WIZARD (/agents/create)

**Step 1: Basic Info**
```
┌─────────────────────────────────────────────────────────────────┐
│ Create Agent — Step 1 of 4                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Agent Name                                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ My AI Assistant                                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Description                                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ A helpful assistant for daily tasks                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  System Prompt                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ You are a helpful AI assistant. Be concise and clear.    │    │
│  │                                                          │    │
│  │                                                          │    │
│  │                                                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│                                          [Next →]                 │
└─────────────────────────────────────────────────────────────────┘
```

**Step 2: Model Selection**
```
┌─────────────────────────────────────────────────────────────────┐
│ Create Agent — Step 2 of 4                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Select Model                                                    │
│                                                                  │
│  Provider: [Groq ▼]                                              │
│                                                                  │
│  ┌─────────────────────────────┐ ┌─────────────────────────┐    │
│  │ 🚀 openai/gpt-oss-120b     │ │ 🚀 openai/gpt-oss-20b  │    │
│  │    Fast, large context      │ │    Fast, compact         │    │
│  │    131K tokens    [Select]  │ │    32K tokens   [Select] │    │
│  └─────────────────────────────┘ └─────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────┐ ┌─────────────────────────┐    │
│  │ 🧠 llama-3.3-70b           │ │ ⚡ llama-3.1-8b          │    │
│  │    Balanced                 │ │    Ultra fast            │    │
│  │    128K tokens    [Select]  │ │    128K tokens  [Select] │    │
│  └─────────────────────────────┘ └─────────────────────────┘    │
│                                                                  │
│  API Key: [••••••••••••••••••]  [Add New Key]                   │
│                                                                  │
│                              [← Back]  [Next →]                  │
└─────────────────────────────────────────────────────────────────┘
```

**Step 3: Tools**
```
┌─────────────────────────────────────────────────────────────────┐
│ Create Agent — Step 3 of 4                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Enable Tools                                                    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 🔍 Web Search              ● Enabled                    │    │
│  │    Search the internet for information                   │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │ 💻 Code Execution          ● Enabled                    │    │
│  │    Run Python and shell code in sandbox                  │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │ 📁 File Operations         ● Enabled                    │    │
│  │    Read, write, and manage files                         │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │ 🌐 Browser                 ○ Disabled                   │    │
│  │    Browse websites and interact with pages               │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │ 📊 Document Editor         ○ Disabled                   │    │
│  │    Create and edit documents, spreadsheets               │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │ 🔊 Voice (TTS/STT)        ○ Disabled                   │    │
│  │    Text-to-speech and speech-to-text                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│                              [← Back]  [Next →]                  │
└─────────────────────────────────────────────────────────────────┘
```

**Step 4: Review & Create**
```
┌─────────────────────────────────────────────────────────────────┐
│ Create Agent — Step 4 of 4                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Review Configuration                                            │
│                                                                  │
│  Name:        My AI Assistant                                    │
│  Description: A helpful assistant for daily tasks                │
│  Model:       groq/openai/gpt-oss-120b                          │
│  Tools:       Web Search, Code Execution, File Operations        │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ System Prompt Preview                                    │    │
│  │                                                          │    │
│  │ You are a helpful AI assistant. Be concise and clear.    │    │
│  │                                                          │    │
│  │ You have access to the following tools:                  │    │
│  │ - web_search: Search the internet                        │    │
│  │ - code_execution: Run Python/shell code                  │    │
│  │ - file_operations: Read/write files                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│                              [← Back]  [Create Agent]            │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3.5 SETTINGS HUB (/settings)

Model configuration is **card-based full-model admin** (see `SOMA-UI-MODEL-ADMIN-001.md` and MOCKUPS Settings suite): model card grid → open card → edit **all** model settings + **Used for** Chat / Help / Memory. Provider keys live under Integrations.

```
┌─────────────────────────────────────────────────────────────────┐
│ ☰ SOMA   Settings                                   👤          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐                                               │
│  │ CORE          │  ┌─────────────────────────────────────────┐ │
│  │ 🖥️ UI         │  │  Model Administration                    │ │
│  │ 🤖 Model      │  │  ┌─────────────────────────────────┐    │ │
│  │ 🧠 Agent      │  │  │ Active: Groq · gpt-oss-120b      │    │ │
│  │ 🔧 Tools      │  │  │ Roles: Chat, Utility  Key: ●OK   │    │ │
│  │               │  │  │ [Edit Selected] [Test ✓]         │    │ │
│  │ MODULES       │  │  └─────────────────────────────────┘    │ │
│  │ 📦 Modules    │  │  Cards:  [GROQ ●] [OpenAI ○] [Ollama ○]│ │
│  │ 🔐 Auth       │  │          [+ Add model]                  │ │
│  │ …             │  │  Open card → full editor + Used for     │ │
│  └──────────────┘  └─────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3.6 MODULE MANAGER (/settings/modules)

```
┌─────────────────────────────────────────────────────────────────┐
│ ☰ SOMA   Settings > Modules                        👤          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Module Manager                                    Profile: [Custom ▼] │
│                                                                  │
│  Presets: [Standalone] [Enterprise] [Full] [Custom]              │
│                                                                  │
│  CORE (always on)                                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 💬 Chat Engine              ● Enabled (locked)          │    │
│  │ 🧠 Memory                   ● Enabled (locked)          │    │
│  │ 🔐 Basic Auth               ● Enabled (locked)          │    │
│  │ 🔧 Tool Executor            ● Enabled (locked)          │    │
│  │ 🖥️ Web UI                   ● Enabled (locked)          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  AUTHENTICATION                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 🔑 Keycloak SSO             ○ Disabled    [▶ Enable]    │    │
│  │    Requires: Keycloak server                              │    │
│  │    Provides: OIDC, LDAP, SAML                             │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │ 🏢 LDAP / Active Directory  ○ Disabled    [▶ Enable]    │    │
│  │    Requires: LDAP server                                  │    │
│  │    Provides: Enterprise directory auth                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  AUTHORIZATION                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 🛡️ OPA Policy Engine       ○ Disabled    [▶ Enable]    │    │
│  │    Requires: OPA server                                   │    │
│  │    Provides: Fine-grained policy decisions                │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │ 🔒 SpiceDB                  ○ Disabled    [▶ Enable]    │    │
│  │    Requires: SpiceDB server                               │    │
│  │    Provides: Zanzibar-style permissions                   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ENTERPRISE                                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 💳 Billing (Lago)           ○ Disabled    [▶ Enable]    │    │
│  │    Requires: PostgreSQL, Lago API                         │    │
│  │    Provides: Usage tracking, invoicing                    │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │ 🔑 Vault Secrets            ○ Disabled    [▶ Enable]    │    │
│  │    Requires: HashiCorp Vault                              │    │
│  │    Provides: Secret management                            │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │ 📋 Audit Logging            ○ Disabled    [▶ Enable]    │    │
│  │    Requires: PostgreSQL                                   │    │
│  │    Provides: Complete audit trail                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  TOOLS                                                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 🌐 Browser Automation       ○ Disabled    [▶ Enable]    │    │
│  │ 🖥️ Linux Desktop            ○ Disabled    [▶ Enable]    │    │
│  │ 🔌 Plugin System            ○ Disabled    [▶ Enable]    │    │
│  │ 📚 Skills System            ○ Disabled    [▶ Enable]    │    │
│  │ 🔗 MCP Integration          ○ Disabled    [▶ Enable]    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  INTEGRATIONS                                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 📨 Kafka Events             ○ Disabled    [▶ Enable]    │    │
│  │ ⚙️ Temporal Workflows       ○ Disabled    [▶ Enable]    │    │
│  │ 📧 Email (SMTP)             ○ Disabled    [▶ Enable]    │    │
│  │ 📱 Telegram Bot             ○ Disabled    [▶ Enable]    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3.7 CANVAS SURFACES

The Canvas is a collapsible right panel (400px default, resizable) that shows context for what the agent is doing.

**Canvas Tab Bar:**
```
┌─────────────────────────────────────────────────┐
│ [🌐 Browser] [💻 Code] [📄 Docs] [📁 Files] [🖥️ Desktop] [>_ Terminal] │
├─────────────────────────────────────────────────┤
│                                                  │
│              [Content Area]                      │
│                                                  │
└─────────────────────────────────────────────────┘
```

**Browser Canvas:**
```
┌─────────────────────────────────────────────────┐
│ [🌐 Browser]  ←  →  ↻  ┌──────────────────────┐│
│                          │ https://example.com   ││
├──────────────────────────┴──────────────────────┤
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │                                          │   │
│  │     [Rendered Web Page]                  │   │
│  │                                          │   │
│  │     Agent can click, type, scroll        │   │
│  │     User can annotate elements           │   │
│  │                                          │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  📸 Screenshot  🔍 Inspect  ✏️ Annotate         │
└─────────────────────────────────────────────────┘
```

**Code Editor Canvas:**
```
┌─────────────────────────────────────────────────┐
│ [💻 Code]  main.py          Python  ▼  [Run] [Save] │
├─────────────────────────────────────────────────┤
│  1 │ import pandas as pd                        │
│  2 │                                            │
│  3 │ df = pd.read_csv('data.csv')               │
│  4 │ print(df.describe())                       │
│  5 │                                            │
│  6 │ # Analysis                                 │
│  7 │ for col in df.columns:                     │
│  8 │     print(f"{col}: {df[col].mean():.2f}")  │
├─────────────────────────────────────────────────┤
│  Output:                                        │
│  ┌──────────────────────────────────────────┐   │
│  │ price: 1234.56                            │   │
│  │ quantity: 42.30                           │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

---

## 4. USER JOURNEYS

### 4.1 Journey: First-Time User (Standalone)

```
START
  │
  ▼
┌─────────────┐
│ docker run   │  User runs one command
│ soma/agent   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ /login      │  Auto-creates admin user on first run
│ Create      │  No Keycloak needed
│ Account     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ /settings/  │  Configure LLM provider
│ model       │  Enter API key (Groq/OpenAI/etc)
│ Select model│
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ /agents/    │  Create first agent
│ create      │  Name, model, system prompt, tools
│ Wizard      │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ /chat       │  Start chatting
│ Agent       │  Agent responds via configured LLM
│ responds    │  Canvas shows tool outputs
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ /settings/  │  Enable more modules as needed
│ modules     │  Browser, plugins, skills, etc.
└─────────────┘
```

### 4.2 Journey: Enterprise Deployment

```
START
  │
  ▼
┌──────────────────┐
│ docker compose    │  Full stack deployment
│ -f enterprise.yml │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Keycloak setup    │  Realm created, LDAP configured
│ Admin creates     │
│ first user        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ /settings/modules │  Enable enterprise modules
│ Enable:           │  Keycloak, OPA, SpiceDB, Billing, Audit
│ keycloak,opa,     │
│ spicedb,billing   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ /admin/tenants    │  Create tenant
│ Create tenant     │  Assign subscription tier
│ Assign users      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ /admin/agents     │  Create agents per tenant
│ Create agents     │  Configure models, tools per tenant
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ /chat             │  Users chat with their agents
│ Multi-tenant      │  Each tenant isolated
│ isolation         │  Billing metered per tenant
└──────────────────┘
```

### 4.3 Journey: Chat with Tool Execution

```
USER: "Search for the latest AI news and summarize it"
  │
  ▼
┌──────────────────────┐
│ V3 Orchestrator       │
│ Phase 1-4: Auth/Gate  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Phase 5: Context      │  System prompt + history + memory
│ Build 5-lane context  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Phase 6: Model        │  Select groq/openai/gpt-oss-120b
│ Selection             │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Phase 8: LLM          │  LLM decides to call web_search tool
│ Invocation            │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Phase 9: Tool         │  web_search("latest AI news 2026")
│ Execution             │  → Returns search results
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Phase 8 (again):      │  LLM processes search results
│ LLM with tool results │  Generates summary
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Phase 11: Memory      │  Store in PostgreSQL + SomaBrain
│ Storage               │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Phase 12: Stream      │  Stream response to user
│ Response              │  Show in chat + canvas
└──────────────────────┘
```

---

## 5. COMPONENT LIBRARY

### 5.1 Core Components (always available)

| Component | Tag | Purpose |
|-----------|-----|---------|
| Chat Input | `<soma-chat-input>` | Message input with attachments, voice |
| Chat Message | `<soma-message>` | Single message bubble (user/agent) |
| Chat History | `<soma-chat-list>` | Conversation list in sidebar |
| Agent Card | `<soma-agent-card>` | Agent display with status |
| Settings Form | `<soma-settings-form>` | Generic settings form |
| Toggle Switch | `<soma-toggle>` | Enable/disable toggle |
| Code Block | `<soma-code-block>` | Syntax highlighted code with copy/run |
| Markdown | `<soma-markdown>` | Safe markdown renderer |
| File Tree | `<soma-file-tree>` | Hierarchical file browser |
| Canvas Panel | `<soma-canvas>` | Right-side context panel |
| Canvas Tab | `<soma-canvas-tab>` | Individual canvas surface |
| Toast | `<soma-toast>` | Notification toast |
| Modal | `<soma-modal>` | Dialog modal |
| Button | `<soma-button>` | Styled button (primary/secondary/danger) |
| Input | `<soma-input>` | Styled text input |
| Select | `<soma-select>` | Styled dropdown |
| Badge | `<soma-badge>` | Status badge (online/offline/error) |
| Loading | `<soma-loading>` | Spinner / skeleton |

### 5.2 Module Components (loaded when module enabled)

| Component | Tag | Module |
|-----------|-----|--------|
| Billing Card | `<soma-billing-card>` | billing |
| Usage Chart | `<soma-usage-chart>` | billing |
| Audit Log Table | `<soma-audit-table>` | audit |
| Plugin Card | `<soma-plugin-card>` | plugins |
| Skill Card | `<soma-skill-card>` | skills |
| MCP Server Card | `<soma-mcp-card>` | mcp |
| Browser Surface | `<soma-browser>` | tools.browser |
| Code Editor | `<soma-code-editor>` | core (canvas) |
| Terminal | `<soma-terminal>` | tools.desktop |
| Desktop Viewer | `<soma-desktop>` | tools.desktop |

---

## 6. RESPONSIVE BREAKPOINTS

| Breakpoint | Width | Layout |
|------------|-------|--------|
| Desktop | >= 1200px | Sidebar + Chat + Canvas |
| Tablet | 768-1199px | Sidebar (collapsed) + Chat + Canvas (overlay) |
| Mobile | < 768px | Chat only, hamburger menu for sidebar, no canvas |

---

## 7. ACCESSIBILITY

| Requirement | Implementation |
|-------------|----------------|
| Keyboard navigation | All interactive elements focusable via Tab |
| Screen reader | ARIA labels on all components |
| Color contrast | WCAG AA (4.5:1 minimum) |
| Focus indicators | Visible focus rings on all interactive elements |
| Reduced motion | `prefers-reduced-motion` media query support |
| Font scaling | rem units, no fixed pixel fonts |

---

End of Document
