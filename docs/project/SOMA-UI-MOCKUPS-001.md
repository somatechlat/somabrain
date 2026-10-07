# SOMA AGENT — SCREEN MOCKUPS & WIREFRAMES

## Document Control

| Field | Value |
|---|---|
| Document Title | Soma Agent Screen Mockups and Wireframes |
| Document Identifier | SOMA-UI-MOCKUPS-001 |
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
| 1.0.1 | 2026-10-07 | SomaTech Engineering | Screen 8 rewritten: card grid + full model editor + slot map (SOMA-UI-MODEL-ADMIN-001). |


## COLOR KEY

```
█ #0A0A0A  Soma Black (background)
█ #111111  Soma Dark (panels)
█ #1A1A1A  Soma Surface (inputs, cards)
█ #2A2A2A  Soma Border
█ #666666  Soma Muted (secondary text)
█ #E5E5E5  Soma Text (primary text)
█ #FFFFFF  Soma White (headings)
█ #3B82F6  Soma Blue (primary action)
█ #6366F1  Soma Indigo (secondary accent)
█ #8B5CF6  Soma Violet (badges)
█ #10B981  Success (green)
█ #F59E0B  Warning (yellow)
█ #EF4444  Error (red)
```

---

## SCREEN 1: LOGIN PAGE

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                          ╔══════════════╗                                │
│                          ║     SOMA     ║                                │
│                          ╚══════════════╝                                │
│                     Cognitive AI Agent                                    │
│                                                                          │
│               ┌────────────────────────────────────────┐                │
│               │                                         │                │
│               │  Email                                   │                │
│               │  ┌───────────────────────────────────┐  │                │
│               │  │ user@company.com                   │  │                │
│               │  └───────────────────────────────────┘  │                │
│               │                                         │                │
│               │  Password                         👁    │                │
│               │  ┌───────────────────────────────────┐  │                │
│               │  │ ••••••••••••                       │  │                │
│               │  └───────────────────────────────────┘  │                │
│               │                                         │                │
│               │  ☐ Remember me     Forgot password?     │                │
│               │                                         │                │
│               │  ┌───────────────────────────────────┐  │                │
│               │  │           ▶ Sign in                │  │                │
│               │  └───────────────────────────────────┘  │                │
│               │                                         │                │
│               │  ──────────── or continue with ──────── │                │
│               │                                         │                │
│               │  [G] Google   [M] Microsoft   [S] SAML  │                │
│               │                                         │                │
│               │  Don't have an account? Sign up          │                │
│               │                                         │                │
│               └────────────────────────────────────────┘                │
│                                                                          │
│                      Powered by SomaTech LAT                             │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## SCREEN 2: WELCOME SCREEN (First Chat / New Chat)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ☰  S SOMA        Soma Assistant  🟢           🔔  ⚙️  👤                    │
├──────┬───────────────────────────────────────────────────────┬──────────────┤
│      │                                                       │              │
│ S    │                     ╔══════════════╗                  │  [Browser]   │
│ O    │                     ║     SOMA     ║                  │  [Code]      │
│ M    │                     ╚══════════════╝                  │  [Docs]      │
│ A    │                                                       │  [Files]     │
│      │              Welcome back, Test User                  │  [Desktop]   │
│ 🔍   │                                                       │  [Terminal]  │
│      │         ┌─────────────────────────────────┐           │              │
│ ───  │         │  What can I help you with?      │           │              │
│      │         │  [Type a message...]         ➤  │           │              │
│ +    │         └─────────────────────────────────┘           │              │
│ New  │                                                       │              │
│ Chat │    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │              │
│      │    │ 💬       │ │ 💻       │ │ 📄       │ │ 🔍     │ │              │
│ ───  │    │ Chat     │ │ Code     │ │ Write    │ │Research│ │              │
│      │    │ Ask      │ │ Generate │ │ Docs &   │ │Search &│ │              │
│ Conv │    │ anything │ │ & debug  │ │ reports  │ │analyze │ │              │
│  1   │    └──────────┘ └──────────┘ └──────────┘ └────────┘ │              │
│ Conv │    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │              │
│  2   │    │ 📊       │ │ 🌐       │ │ 🖥️       │ │ 🎤     │ │              │
│ Conv │    │ Analyze  │ │ Browse   │ │ Desktop  │ │ Voice  │ │              │
│  3   │    │ Data &   │ │ Web &    │ │ Run apps │ │ Talk   │ │              │
│      │    │ visualize│ │ interact │ │          │ │ to agent│ │              │
│      │    └──────────┘ └──────────┘ └──────────┘ └────────┘ │              │
│      │                                                       │              │
│      │    Recent Conversations                               │              │
│      │    ┌─────────────────────────────────────────────┐   │              │
│      │    │ 💬 Analyze sales data    2 hours ago         │   │              │
│      │    │ 💬 Write API docs        Yesterday           │   │              │
│      │    │ 💬 Debug WebSocket       2 days ago          │   │              │
│      │    └─────────────────────────────────────────────┘   │              │
│      │                                                       │              │
│      │              SomaTech · Cognitive AI Agent             │              │
│      │                                                       │              │
│ [⚙️] │                                                       │              │
│ [📦] │                                                       │              │
│ [👤] │                                                       │              │
└──────┴───────────────────────────────────────────────────────┴──────────────┘
```

---

## SCREEN 3: ACTIVE CHAT (Agent Responding with Tool)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ☰  S SOMA        Soma Assistant  🟢           🔔  ⚙️  👤                    │
├──────┬───────────────────────────────────────────────────────┬──────────────┤
│      │                                                       │              │
│ S    │  ┌───────────────────────────────────────────────┐   │  [Browser]   │
│ O    │  │ 👤 Test User                           2:34 PM│   │  [Code]      │
│ M    │  │ ┌───────────────────────────────────────────┐ │   │  [Docs]      │
│ A    │  │ │ Search for latest AI news and summarize   │ │   │  [Files]     │
│      │  │ └───────────────────────────────────────────┘ │   │  [Desktop]   │
│ 🔍   │  └───────────────────────────────────────────────┘   │  [Terminal]  │
│      │                                                       │              │
│ ───  │  ┌───────────────────────────────────────────────┐   │ ┌──────────┐ │
│      │  │ 🤖 Soma Assistant                       2:34 PM│   │ │          │ │
│ +    │  │ ┌───────────────────────────────────────────┐ │   │ │          │ │
│ New  │  │ │ 🔧 Tool: web_search          [▶ Expand]  │ │   │ │ Browser  │ │
│ Chat │  │ │ ─────────────────────────────────────────  │ │   │ │          │ │
│      │  │ │ Input: "AI news 2026"                     │ │   │ │ https:// │ │
│ ───  │  │ │ Output:                                   │ │   │ │ example  │ │
│      │  │ │  1. GPT-5 Architecture Revealed...        │ │   │ │ .com     │ │
│ Conv │  │ │  2. New RLHF Breakthrough...              │ │   │ │          │ │
│  1   │  │ │  3. Multi-Modal Agents Survey...          │ │   │ │ [Page    │ │
│      │  │ │ Status: ✅ 1.2s                           │ │   │ │  Content]│ │
│ Conv │  │ └───────────────────────────────────────────┘ │   │ │          │ │
│  2   │  │                                               │   │ │          │ │
│      │  │ ┌───────────────────────────────────────────┐ │   │ │          │ │
│ Conv │  │ │ Here are the latest AI developments:      │ │   │ │          │ │
│  3   │  │ │                                           │ │   │ │          │ │
│      │  │ │ **1. GPT-5 Architecture**                 │ │   │ │          │ │
│      │  │ │ OpenAI revealed the GPT-5 architecture... │ │   │ │          │ │
│      │  │ │                                           │ │   │ │          │ │
│      │  │ │ **2. RLHF Breakthrough**                  │ │   │ │          │ │
│      │  │ │ A new approach to reinforcement learning..│ │   │ │          │ │
│      │  │ └───────────────────────────────────────────┘ │   │ │          │ │
│      │  │ 2:35 PM                            [Copy] [↩] │   │ └──────────┘ │
│      │  └───────────────────────────────────────────────┘   │              │
│      │                                                       │              │
│      │  ┌───────────────────────────────────────────────┐   │              │
│      │  │ 📎 Ask anything...                      🎤  ➤ │   │              │
│      │  └───────────────────────────────────────────────┘   │              │
│      │  Model: gpt-oss-120b ▼    Agent: Soma Assistant ▼   │              │
│      │                                                       │              │
│ [⚙️] │                                                       │              │
│ [📦] │                                                       │              │
│ [👤] │                                                       │              │
└──────┴───────────────────────────────────────────────────────┴──────────────┘
```

---

## SCREEN 4: AGENT LIST

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ☰  S SOMA        Agents                                          👤        │
├──────┬───────────────────────────────────────────────────────┬──────────────┤
│      │                                                       │              │
│ S    │  Your Agents                          [+ Create Agent] │              │
│ O    │                                                       │              │
│ M    │  ┌───────────────────────────────────────────────┐   │              │
│ A    │  │ 🤖 Soma Assistant                              │   │              │
│      │  │    groq/openai/gpt-oss-120b                    │   │              │
│ 🔍   │  │    AI assistant powered by Groq                │   │              │
│      │  │    Created: Jun 15  Conversations: 3           │   │              │
│ ───  │  │                            [Chat] [Edit] [⋮]   │   │              │
│      │  └───────────────────────────────────────────────┘   │              │
│ +    │                                                       │              │
│ New  │  ┌───────────────────────────────────────────────┐   │              │
│ Chat │  │ 🤖 Code Assistant                              │   │              │
│      │  │    openai/gpt-4o                               │   │              │
│ ───  │  │    Specialized in code generation and review   │   │              │
│      │  │    Created: Jun 10  Conversations: 12          │   │              │
│ Conv │  │                            [Chat] [Edit] [⋮]   │   │              │
│  1   │  └───────────────────────────────────────────────┘   │              │
│ Conv │                                                       │              │
│  2   │  ┌───────────────────────────────────────────────┐   │              │
│ Conv │  │ 🤖 Research Agent                              │   │              │
│  3   │  │    anthropic/claude-sonnet                     │   │              │
│      │  │    Deep research and analysis                  │   │              │
│      │  │    Created: Jun 8   Conversations: 7           │   │              │
│      │  │                            [Chat] [Edit] [⋮]   │   │              │
│      │  └───────────────────────────────────────────────┘   │              │
│      │                                                       │              │
│ [⚙️] │                                                       │              │
│ [📦] │                                                       │              │
│ [👤] │                                                       │              │
└──────┴───────────────────────────────────────────────────────┴──────────────┘
```

---

## SCREEN 5: CREATE AGENT WIZARD (Step 1: Basic Info)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ☰  S SOMA        Create Agent — Step 1 of 4                       👤        │
├──────┬───────────────────────────────────────────────────────┬──────────────┤
│      │                                                       │              │
│ S    │  ┌───────────────────────────────────────────────┐   │              │
│ O    │  │ ● 1. Info    ○ 2. Model    ○ 3. Tools  ○ 4.  │   │              │
│ M    │  │                              Review & Create   │   │              │
│ A    │  └───────────────────────────────────────────────┘   │              │
│      │                                                       │              │
│ 🔍   │  Agent Name                                           │              │
│      │  ┌───────────────────────────────────────────────┐   │              │
│ ───  │  │ My AI Assistant                                 │   │              │
│      │  └───────────────────────────────────────────────┘   │              │
│ +    │                                                       │              │
│ New  │  Description                                          │              │
│ Chat │  ┌───────────────────────────────────────────────┐   │              │
│      │  │ A helpful assistant for daily tasks             │   │              │
│ ───  │  └───────────────────────────────────────────────┘   │              │
│      │                                                       │              │
│ Conv │  System Prompt                                        │              │
│  1   │  ┌───────────────────────────────────────────────┐   │              │
│ Conv │  │ You are a helpful AI assistant. Be concise     │   │              │
│  2   │  │ and clear. You have access to tools for web    │   │              │
│ Conv │  │ search, code execution, and file operations.   │   │              │
│  3   │  │                                                 │   │              │
│      │  │                                                 │   │              │
│      │  └───────────────────────────────────────────────┘   │              │
│      │                                                       │              │
│      │  Personality                                          │              │
│      │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │              │
│      │  │ Professional │ │ Friendly     │ │ Creative     │ │              │
│      │  │ ●            │ │ ○            │ │ ○            │ │              │
│      │  └──────────────┘ └──────────────┘ └──────────────┘ │              │
│      │                                                       │              │
│      │                              [Back]  [Next →]         │              │
│      │                                                       │              │
│ [⚙️] │                                                       │              │
└──────┴───────────────────────────────────────────────────────┴──────────────┘
```

---

## SCREEN 6: CREATE AGENT WIZARD (Step 2: Model Selection)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ☰  S SOMA        Create Agent — Step 2 of 4                       👤        │
├──────┬───────────────────────────────────────────────────────┬──────────────┤
│      │                                                       │              │
│ S    │  ┌───────────────────────────────────────────────┐   │              │
│ O    │  │ ✓ 1. Info    ● 2. Model    ○ 3. Tools  ○ 4.  │   │              │
│ M    │  │                              Review & Create   │   │              │
│ A    │  └───────────────────────────────────────────────┘   │              │
│      │                                                       │              │
│ 🔍   │  Provider: [Groq ▼]                                  │              │
│      │                                                       │              │
│ ───  │  ┌─────────────────────┐ ┌─────────────────────┐    │              │
│      │  │ 🚀 gpt-oss-120b    │ │ 🚀 gpt-oss-20b     │    │              │
│ +    │  │    Fast, large ctx  │ │    Fast, compact     │    │              │
│ New  │  │    131K tokens      │ │    32K tokens        │    │              │
│ Chat │  │    [Selected ✓]     │ │    [Select]          │    │              │
│      │  └─────────────────────┘ └─────────────────────┘    │              │
│ ───  │                                                       │              │
│      │  ┌─────────────────────┐ ┌─────────────────────┐    │              │
│ Conv │  │ 🧠 llama-3.3-70b   │ │ ⚡ llama-3.1-8b     │    │              │
│  1   │  │    Balanced         │ │    Ultra fast        │    │              │
│ Conv │  │    128K tokens      │ │    128K tokens       │    │              │
│  2   │  │    [Select]         │ │    [Select]          │    │              │
│ Conv │  └─────────────────────┘ └─────────────────────┘    │              │
│  3   │                                                       │              │
│      │  API Key                                               │              │
│      │  ┌───────────────────────────────────────────────┐   │              │
│      │  │ gsk_••••••••••••••••••••••••••••••••••••      │   │              │
│      │  └───────────────────────────────────────────────┘   │              │
│      │  [+ Add New API Key]                                  │              │
│      │                                                       │              │
│      │                              [← Back]  [Next →]       │              │
│ [⚙️] │                                                       │              │
└──────┴───────────────────────────────────────────────────────┴──────────────┘
```

---

## SCREEN 7: SETTINGS — MODULE MANAGER

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ☰  S SOMA        Settings > Modules                               👤        │
├──────┬───────────────────────────────────────────────────────┬──────────────┤
│      │                                                       │              │
│ S    │  Module Manager         Profile: [Custom ▼]           │              │
│ O    │                                                       │              │
│ M    │  Presets: [Standalone] [Enterprise] [Full] [Custom]   │              │
│ A    │                                                       │              │
│      │  CORE (always on)                                      │              │
│ 🔍   │  ┌───────────────────────────────────────────────┐   │              │
│      │  │ 💬 Chat Engine           ● Enabled (locked)   │   │              │
│ ───  │  │ 🧠 Memory                ● Enabled (locked)   │   │              │
│      │  │ 🔐 Basic Auth            ● Enabled (locked)   │   │              │
│ +    │  │ 🔧 Tool Executor         ● Enabled (locked)   │   │              │
│ New  │  │ 🖥️ Web UI                ● Enabled (locked)   │   │              │
│ Chat │  └───────────────────────────────────────────────┘   │              │
│      │                                                       │              │
│ ───  │  AUTHENTICATION                                        │              │
│      │  ┌───────────────────────────────────────────────┐   │              │
│      │  │ 🔑 Keycloak SSO        ○ Disabled  [Enable ▶] │   │              │
│ Conv │  │    Requires: Keycloak server                   │   │              │
│  1   │  ├───────────────────────────────────────────────┤   │              │
│ Conv │  │ 🏢 LDAP / Active Dir    ○ Disabled  [Enable ▶] │   │              │
│  2   │  │    Requires: LDAP server                       │   │              │
│ Conv │  └───────────────────────────────────────────────┘   │              │
│  3   │                                                       │              │
│      │  AUTHORIZATION                                         │              │
│      │  ┌───────────────────────────────────────────────┐   │              │
│      │  │ 🛡️ OPA Policy Engine   ○ Disabled  [Enable ▶] │   │              │
│      │  ├───────────────────────────────────────────────┤   │              │
│      │  │ 🔒 SpiceDB             ○ Disabled  [Enable ▶] │   │              │
│      │  └───────────────────────────────────────────────┘   │              │
│      │                                                       │              │
│      │  ENTERPRISE                                            │              │
│      │  ┌───────────────────────────────────────────────┐   │              │
│      │  │ 💳 Billing (Lago)      ○ Disabled  [Enable ▶] │   │              │
│      │  ├───────────────────────────────────────────────┤   │              │
│      │  │ 🔑 Vault Secrets       ○ Disabled  [Enable ▶] │   │              │
│      │  ├───────────────────────────────────────────────┤   │              │
│      │  │ 📋 Audit Logging       ○ Disabled  [Enable ▶] │   │              │
│      │  └───────────────────────────────────────────────┘   │              │
│      │                                                       │              │
│      │  TOOLS                                                 │              │
│      │  ┌───────────────────────────────────────────────┐   │              │
│      │  │ 🌐 Browser Automation  ○ Disabled  [Enable ▶] │   │              │
│      │  ├───────────────────────────────────────────────┤   │              │
│      │  │ 🔌 Plugin System       ○ Disabled  [Enable ▶] │   │              │
│      │  ├───────────────────────────────────────────────┤   │              │
│      │  │ 📚 Skills System       ○ Disabled  [Enable ▶] │   │              │
│      │  └───────────────────────────────────────────────┘   │              │
│      │                                                       │              │
│ [⚙️] │                                                       │              │
└──────┴───────────────────────────────────────────────────────┴──────────────┘
```

---

## SCREEN 8: SETTINGS — MODEL ADMINISTRATION (card UI)

**Canonical spec:** `SOMA-UI-MODEL-ADMIN-001.md`. Selecting a **full card** opens the **complete** model editor (every `ModelIn` field). Slots are assigned from the card, not three bare dropdowns.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ☰  S SOMA        Settings > Models                                 👤        │
├──────┬───────────────────────────────────────────────────────┬──────────────┤
│      │  MODEL ADMINISTRATION                                  │              │
│ S    │  ┌───────────────────────────────────────────────┐   │              │
│ O    │  │ Active  Provider: Groq · openai/gpt-oss-120b   │   │              │
│ M    │  │ Roles: [Chat] [Utility]   Key: gsk_••••  ●OK  │   │              │
│ A    │  │ [Edit Selected] [Test Connection ✓]            │   │              │
│      │  └───────────────────────────────────────────────┘   │              │
│ 🔍   │                                                       │              │
│ ───  │  MODELS                                               │              │
│      │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │              │
│ +    │  │ ● SELECTED  │ │   OpenAI    │ │   Local     │   │              │
│ New  │  │   GROQ      │ │   ○ Setup   │ │   ○ Setup   │   │              │
│ Chat │  │ gpt-oss-120b│ │ gpt-4o-mini │ │ llama3.1    │   │              │
│      │  │ 131K ⚡ v   │ │ 128K        │ │ 32K         │   │              │
│ ───  │  │ [Chat][Uty] │ │ [—]         │ │ [—]         │   │              │
│      │  └─────────────┘ └─────────────┘ └─────────────┘   │              │
│ Conv │  ┌─────────────┐ ┌─────────────┐                    │              │
│  1   │  │  OpenRouter │ │  + ADD      │                    │              │
│ Conv │  │   ○ Setup   │ │             │                    │              │
│  2   │  │ …           │ │             │                    │              │
│ Conv │  └─────────────┘ └─────────────┘                    │              │
│  3   │                                                       │              │
│      │  FULL MODEL EDIT — openai/gpt-oss-120b                │              │
│      │  ┌───────────────────────────────────────────────┐   │              │
│      │  │ Provider  [Groq v]     Model [openai/gpt-oss…]│   │              │
│      │  │ API key   [••••••] [Show] [Test]              │   │              │
│      │  │ Vision    [● on]     Type [chat v]            │   │              │
│      │  │ Assign    ☑ Chat  ☑ Utility  ☐ Embedding     │   │              │
│      │  │ ▸ Advanced Settings                           │   │              │
│      │  │   Base URL | ctx_length | max tokens | timeout│   │              │
│      │  │   cost_tier | domains | priority | capabilities│  │              │
│      │  │   rate limits | kwargs (JSON)                 │   │              │
│      │  │ [Save Model] [Delete…]                        │   │              │
│      │  └───────────────────────────────────────────────┘   │              │
│      │                                                       │              │
│      │  SLOT MAP          Chat → gpt-oss-120b                │              │
│      │  Utility → gpt-oss-120b   Embedding → —               │              │
│ [⚙️] │  [Open Presets]                                        │              │
└──────┴───────────────────────────────────────────────────────┴──────────────┘
```

Card states: default · hoverable · **selected** (Soma Blue border). Advanced collapsed (P-03).

---

## SCREEN 9: SETTINGS — TOOLS

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ☰  S SOMA        Settings > Tools                                  👤        │
├──────┬───────────────────────────────────────────────────────┬──────────────┤
│      │                                                       │              │
│ S    │  Tool Configuration                                   │              │
│ O    │                                                       │              │
│ M    │  ┌───────────────────────────────────────────────┐   │              │
│ A    │  │ 🔍 Web Search              ● Enabled          │   │              │
│      │  │    Search the internet for information         │   │              │
│ 🔍   │  │    Provider: DuckDuckGo                        │   │              │
│      │  ├───────────────────────────────────────────────┤   │              │
│ ───  │  │ 💻 Code Execution          ● Enabled          │   │              │
│      │  │    Run Python and shell code in sandbox        │   │              │
│ +    │  │    Timeout: 30s  Max memory: 512MB             │   │              │
│ New  │  ├───────────────────────────────────────────────┤   │              │
│ Chat │  │ 📁 File Operations         ● Enabled          │   │              │
│      │  │    Read, write, and manage files               │   │              │
│ ───  │  │    Max file size: 10MB                        │   │              │
│      │  ├───────────────────────────────────────────────┤   │              │
│ Conv │  │ 🌐 Browser                 ○ Disabled         │   │              │
│  1   │  │    Browse websites and interact with pages     │   │              │
│ Conv │  │    Requires: Chromium                          │   │              │
│  2   │  ├───────────────────────────────────────────────┤   │              │
│ Conv │  │ 📊 Document Editor         ○ Disabled         │   │              │
│  3   │  │    Create and edit documents, spreadsheets     │   │              │
│      │  ├───────────────────────────────────────────────┤   │              │
│      │  │ 🎤 Voice (TTS/STT)        ○ Disabled         │   │              │
│      │  │    Text-to-speech and speech-to-text           │   │              │
│      │  ├───────────────────────────────────────────────┤   │              │
│      │  │ 🔗 Git Operations          ● Enabled          │   │              │
│      │  │    Clone, commit, push, diff                   │   │              │
│      │  ├───────────────────────────────────────────────┤   │              │
│      │  │ 📧 Email                   ○ Disabled         │   │              │
│      │  │    Send emails via SMTP                        │   │              │
│      │  └───────────────────────────────────────────────┘   │              │
│      │                                                       │              │
│ [⚙️] │                                                       │              │
└──────┴───────────────────────────────────────────────────────┴──────────────┘
```

---

## SCREEN 10: CANVAS — BROWSER

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ☰  S SOMA        Soma Assistant  🟢           🔔  ⚙️  👤                    │
├──────┬───────────────────────────────────────────────────────┬──────────────┤
│      │                                                       │              │
│ S    │  User: Search for the latest AI research papers       │              │
│ O    │                                                       │              │
│ M    │  🤖 I'll search for that now.                         │              │
│ A    │                                                       │ [🌐 Browser] │
│      │  🔧 Tool: web_search                                 │ [💻 Code]    │
│ 🔍   │  Input: "AI research papers 2026"                    │ [📄 Docs]    │
│      │  Status: ✅ 0.8s                                     │ [📁 Files]   │
│ ───  │                                                       │ [🖥️ Desktop]│
│      │  Here are the latest papers:                          │ [>_ Terminal]│
│ +    │  1. Scaling Laws for Neural Machine Translation       │              │
│ New  │  2. Constitutional AI: Harmlessness from AI Feedback  │ ┌──────────┐ │
│ Chat │  3. FlashAttention-3: Fast Attention...               │ │ ← → ↻   │ │
│      │                                                       │ │ https:// │ │
│ ───  │                                                       │ │ arxiv.org│ │
│      │                                                       │ ├──────────┤ │
│ Conv │                                                       │ │          │ │
│  1   │                                                       │ │ [Paper   │ │
│ Conv │                                                       │ │  List]   │ │
│  2   │                                                       │ │          │ │
│ Conv │                                                       │ │ ┌──────┐ │ │
│  3   │                                                       │ │ │Paper │ │ │
│      │                                                       │ │ │Title │ │ │
│      │                                                       │ │ │      │ │ │
│      │                                                       │ │ │Abs.. │ │ │
│      │                                                       │ │ └──────┘ │ │
│      │                                                       │ │          │ │
│      │                                                       │ └──────────┘ │
│      │                                                       │ [📸][🔍][✏️] │
│      │  ┌───────────────────────────────────────────────┐   │              │
│      │  │ 📎 Ask anything...                      🎤  ➤ │   │              │
│      │  └───────────────────────────────────────────────┘   │              │
│      │                                                       │              │
│ [⚙️] │                                                       │              │
└──────┴───────────────────────────────────────────────────────┴──────────────┘
```

---

## SCREEN 11: CANVAS — CODE EDITOR

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ☰  S SOMA        Soma Assistant  🟢           🔔  ⚙️  👤                    │
├──────┬───────────────────────────────────────────────────────┬──────────────┤
│      │                                                       │              │
│ S    │  🤖 Here's a Python script to analyze your data:      │              │
│ O    │                                                       │ [🌐 Browser] │
│ M    │  ┌───────────────────────────────────────────────┐   │ [💻 Code]    │
│ A    │  │ 🐍 Python                          [Copy] [▶] │   │ [📄 Docs]    │
│      │  │ ─────────────────────────────────────────────  │   │ [📁 Files]   │
│ 🔍   │  │  1 │ import pandas as pd                      │   │ [🖥️ Desktop]│
│      │  │  2 │ import matplotlib.pyplot as plt          │   │ [>_ Terminal]│
│ ───  │  │  3 │                                          │   │              │
│      │  │  4 │ df = pd.read_csv('data.csv')              │   │ ┌──────────┐ │
│ +    │  │  5 │ print(df.describe())                      │   │ │main.py ▼ │ │
│ New  │  │  6 │                                          │   │ │Python  [▶]│ │
│ Chat │  │  7 │ df.hist(figsize=(12, 8))                  │   │ ├──────────┤ │
│      │  │  8 │ plt.savefig('analysis.png')               │   │ │ 1│import │ │
│ ───  │  │  9 │                                          │   │ │ 2│  pd   │ │
│      │  │ 10 │ # Correlation matrix                      │   │ │ 3│       │ │
│ Conv │  │ 11 │ corr = df.corr()                          │   │ │ 4│df =.. │ │
│  1   │  │ 12 │ print(corr)                               │   │ │ 5│print..│ │
│ Conv │  └───────────────────────────────────────────────┘   │ │ 6│       │ │
│  2   │                                                       │ │ 7│df.hist│ │
│ Conv │                                                       │ ├──────────┤ │
│  3   │                                                       │ │Output:   │ │
│      │                                                       │ │          │ │
│      │                                                       │ │ count    │ │
│      │                                                       │ │  mean    │ │
│      │                                                       │ │  std     │ │
│      │                                                       │ │  min     │ │
│      │                                                       │ │  max     │ │
│      │                                                       │ └──────────┘ │
│      │  ┌───────────────────────────────────────────────┐   │              │
│      │  │ 📎 Ask anything...                      🎤  ➤ │   │              │
│      │  └───────────────────────────────────────────────┘   │              │
│ [⚙️] │                                                       │              │
└──────┴───────────────────────────────────────────────────────┴──────────────┘
```

---

## SCREEN 12: ADMIN DASHBOARD (Enterprise Only)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ☰  S SOMA        Admin Dashboard                                   👤        │
├──────┬───────────────────────────────────────────────────────┬──────────────┤
│      │                                                       │              │
│ S    │  System Overview                                      │              │
│ O    │                                                       │              │
│ M    │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│              │
│ A    │  │ 🟢 3     │ │ 👤 156   │ │ 💬 2.4K  │ │ 🤖 12    ││              │
│      │  │ Agents   │ │ Users    │ │ Messages │ │ Active   ││              │
│ 🔍   │  │ Online   │ │ Total    │ │ Today    │ │ Now      ││              │
│      │  └──────────┘ └──────────┘ └──────────┘ └──────────┘│              │
│ ───  │                                                       │              │
│      │  Module Status                                        │              │
│ 📊   │  ┌───────────────────────────────────────────────┐   │              │
│ Dash │  │ 💬 Chat Engine        🟢 Running    12ms      │   │              │
│      │  │ 🧠 Memory             🟢 Running    5ms       │   │              │
│ 👥   │  │ 🔐 Keycloak Auth      🟢 Running    45ms      │   │              │
│ Users│  │ 🛡️ OPA Policy         🟢 Running    15ms      │   │              │
│      │  │ 🔒 SpiceDB            🟢 Running    8ms       │   │              │
│ 🤖   │  │ 💳 Billing            🟡 Degraded   200ms     │   │              │
│Agents│  │ 📋 Audit              🟢 Running    3ms       │   │              │
│      │  │ 📨 Kafka              🟢 Running    2ms       │   │              │
│ 💳   │  └───────────────────────────────────────────────┘   │              │
│ Bill │                                                       │              │
│      │  Recent Activity                                      │              │
│ 🛡️   │  ┌───────────────────────────────────────────────┐   │              │
│ Sec  │  │ 14:32  user@co.com  Login success              │   │              │
│      │  │ 14:30  agent-001    New conversation started   │   │              │
│ 📋   │  │ 14:28  user@co.com  Password changed           │   │              │
│ Audit│  │ 14:25  system       Billing module degraded    │   │              │
│      │  └───────────────────────────────────────────────┘   │              │
│ ⚙️   │                                                       │              │
│System│                                                       │              │
│ [⚙️] │                                                       │              │
└──────┴───────────────────────────────────────────────────────┴──────────────┘
```

---

## SCREEN 13: MOBILE VIEW

```
┌────────────────────────┐
│ ☰  SOMA   Soma Asst  👤│
├────────────────────────┤
│                        │
│ 👤 Analyze this data   │
│                        │
│ 🤖 Of course! I can    │
│    help you analyze    │
│    your CSV data.      │
│                        │
│ ```python              │
│ import pandas as pd    │
│ df = pd.read_csv(...)  │
│ ```                    │
│                        │
│ 🔧 Tool: web_search   │
│ Status: ✅ 0.8s       │
│                        │
│ ┌────────────────────┐ │
│ │ 📎 Ask...      ➤  │ │
│ └────────────────────┘ │
│                        │
└────────────────────────┘
```

---

End of Document
