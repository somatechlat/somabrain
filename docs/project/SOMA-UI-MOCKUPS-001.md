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
| 1.0.1 | 2026-10-07 | SomaTech Engineering | Screen 8 rewritten: card grid + full model editor. |
| 2.0.0 | 2026-10-07 | SomaTech Engineering | Full Settings suite (Agent, Models, Voice, Interface, Tools, Integrations, Advanced). **No "slot" wording.** Every field tables. Human test language. |


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

## 0. PRODUCT MAP — every somaAgent01 feature must have a screen

**Rule:** UI = 100% of live API/CRUD (chat, memory, models, voice, files, agents, sessions, plugins, secrets, multimodal, quality, observability, gateway, skills, tools). Agent Zero settings power **without** Agent Zero UX debt.

| Area | CRUD / ops (API) | Screen |
|---|---|---|
| **Models** | list/get/create/update/delete; Used for Chat/Help/Memory; presets save/apply/delete; test connection; setup gate | **7B Models** |
| **Providers & keys** | provider update; write-only keys set/delete; test | **7F Integrations** |
| **Chat** | conversations list/create/rename/delete/export; messages; sessions | **3 + 3A Chat list** |
| **Memory** | list/recall/save/forget; metrics; browse | **3B Memory** |
| **Voice** | personas CRUD; default; TTS/STT; sessions list/stats/terminate; voices | **7C Voice** |
| **Agents** | list/create/update; users/roles; transfer | **4 + 5 Wizard** |
| **Files** | list/upload/download/delete | **5C Files** |
| **Tools** | list; catalog upsert | **7E Tools** |
| **Plugins** | install/enable/disable/uninstall/config; marketplace | **7G Advanced** |
| **Secrets** | provider key status/set/delete | **7F** |
| **Multimodal** | image/diagram/screenshot/video settings + assets | **7D+ Multimodal** |
| **Quality** | evaluate; retry policies; thresholds | **7G Quality** |
| **Observability** | health, metrics, SLA, usage/cost | **12 Admin / 7G** |
| **Sessions** | list/terminate/config | **7G Sessions** |
| **Gateway / A2A** | keys, constitution, workflows | **7G** |
| **UI skins** | list/create/approve/reject | **7D Skins** |
| **SSO/Auth** | login/register/MFA/impersonate | **1 / 1A Profile** |
| **Brain (somabrain)** | cognition, neuromod, sleep | **3C Brain** (agent power) |

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

## SETTINGS SUITE (Screens 7–7G)

**One workspace** (Agent Zero style). Header **Settings** opens this.  
**Language law:** never say “slot”. Say **Used for** (Chat / Help / Memory).  
Canonical spec: `SOMA-UI-MODEL-ADMIN-001.md` (v3).

### Settings nav (human)

```
Agent · Models · Voice · Interface · Tools · Integrations · Advanced
```

Global footer: **Save** · **Cancel**. Search box filters sections. Loading / error / Retry.

---

## SCREEN 7: SETTINGS SHELL + AGENT

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ☰ SOMA   Settings    [Search settings…]                          [Save][Cancel]│
├──────────┬───────────────────────────────────────────────────────────────────┤
│ Agent    │  AGENT                                                             │
│ Models   │  How new chats behave.                                             │
│ Voice    │  ┌─────────────────────────────────────────────────────────────┐   │
│ Interface│  │ Default personality     [Friendly assistant        ▼]        │   │
│ Tools    │  │   What new chats use for tone and style.                     │   │
│ Integr.  │  │                                                             │   │
│ Advanced │  │ System instructions                                         │   │
│          │  │ ┌─────────────────────────────────────────────────────────┐ │   │
│          │  │ │ You are helpful, precise, and honest.                   │ │   │
│          │  │ └─────────────────────────────────────────────────────────┘ │   │
│          │  │   Standing rules the agent always follows.                  │   │
│          │  │                                                             │   │
│          │  │ Knowledge folder      [general-kb                   ▼]      │   │
│          │  │   Extra docs the agent may use.                             │   │
│          │  │                                                             │   │
│          │  │ Inherit current project  [● on]                            │   │
│          │  │   New chats keep this project’s context.                    │   │
│          │  │                                                             │   │
│          │  │ Max failed replies in a row  [ 5 ]                         │   │
│          │  │   Stop after this many broken answers.                      │   │
│          │  └─────────────────────────────────────────────────────────────┘   │
└──────────┴───────────────────────────────────────────────────────────────────┘
```

**Fields (test table)**

| Label | Control | Default | Help |
|---|---|---|---|
| Default personality | select | Friendly assistant | New chat behavior |
| System instructions | textarea | (template) | Standing rules |
| Knowledge folder | select | general-kb | Extra docs |
| Inherit current project | toggle | on | Project context in new chats |
| Max failed replies in a row | number ≥1 | 5 | Stop broken loops |

**States:** read-only banner if no `settings:edit`; Save disabled.

---

## SCREEN 7B: SETTINGS — MODELS (cards + Activate + modal editor)

**Interaction (product law)**

| Action | Result |
|---|---|
| **Activate** on card | That model becomes the active chat model (one-click). Card gets ● LIVE |
| **Use for** chips on card | Quick set Chat / Help / Memory without opening editor |
| **Click card** (or **Edit**) | Opens **Model editor modal** — Normal tab + **Advanced** tab |
| **Add model** | Same modal, empty form |
| **Test** | On card + in modal |
| **Manage keys** | Opens Integrations (never on model) |

**Default out of the box:** Groq · **DeepSeek 2.8** is **● LIVE** (active).

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ☰ SOMA   Settings · Models                              [Add model] [Keys→]  │
├──────────┬───────────────────────────────────────────────────────────────────┤
│ …        │  [Search models…]     Type [All ▼]     Status [All ▼]             │
│          │                                                                   │
│          │  ┌─────────────────────────────┐  ┌─────────────────────────────┐ │
│          │  │ ● LIVE        Chat           │  │ ○        Chat               │ │
│          │  │ deepseek-2.8                │  │ gpt-oss-120b                │ │
│          │  │ DeepSeek 2.8 · Groq         │  │ GPT-OSS · Groq              │ │
│          │  │ fast · price low            │  │ •••                         │ │
│          │  │ Used for: Chat, Help        │  │ Used for: —                 │ │
│          │  │ key ● set                   │  │ key ● set                   │ │
│          │  │ [✓ Active]  [Edit]  [Test]  │  │ [ Activate ]  [Edit] [Test] │ │
│          │  └─────────────────────────────┘  └─────────────────────────────┘ │
│          │  ┌─────────────────────────────┐  ┌─────────────────────────────┐ │
│          │  │ ○        Embeddings         │  │ ○        Chat               │ │
│          │  │ text-embed-3-small          │  │ llama3.1 · Ollama           │ │
│          │  │ OpenAI                      │  │ local                       │ │
│          │  │ Used for: Memory            │  │ [ Activate ] [Edit] [Test]  │ │
│          │  │ [ Activate ] [Edit] [Test]  │  └─────────────────────────────┘ │
│          │  └─────────────────────────────┘                                  │
└──────────┴───────────────────────────────────────────────────────────────────┘

Click [Edit] or card body → MODAL (same card design language):

┌─────────────────────────────────────────────────────────────────────────────┐
│  ✕   Edit model — deepseek-2.8 · Groq                    ● LIVE             │
│  ─────────────────────────────────────────────────────────────────────────  │
│  [ Normal ]   [ Advanced ]   [ Used for ]                                  │
│  ─────────────────────────────────────────────────────────────────────────  │
│  NORMAL  (common settings — what you touch most)                            │
│    Model ID         [deepseek-2.8            ]  [Search models]            │
│    Display name     [DeepSeek 2.8            ]                              │
│    Type             [Chat                     ▼]                            │
│    Provider         [Groq                     ▼]                            │
│    API address      [https://api.groq.com/openai/v1]                        │
│    Price level      [low                       ▼]                           │
│    Sees images      [● on]      Use this model [● on]                       │
│    Provider key     [● set]     [Manage keys →]                             │
│                                                                             │
│  ADVANCED  (max tokens, context, limits — when you need them)              │
│    Context window   [131072] tokens                                        │
│    Max output tokens[8192]                                                 │
│    Requests / min   [0]   Input tokens / min [0]   Output tokens / min [0] │
│    Priority         [10]   Good at [chat, reasoning]  Used in [general]    │
│    Extra options    [ temperature: 0.7, top_p: 1, ... ]  JSON              │
│    ── power of the brain ──                                                 │
│    Memory / context [● on]   Vision model [auto ▼]                         │
│                                                                             │
│  USED FOR                                                                   │
│    [✓] Chat   [✓] Help   [ ] Memory                                        │
│                                                                             │
│  [ Save model ]   [ Test connection ]   [ Make live ]   [ Delete… ]         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Field groups (normal vs advanced)

| Tab | Human labels | API |
|---|---|---|
| **Normal** | Model ID, Display name, Type, Provider, API address, Price level, Sees images, Use this model, Provider key status | `name, display_name, model_type, provider, api_base, cost_tier, vision, is_active` |
| **Advanced** | Context window, Max output tokens*, Requests/Input/Output per minute, Priority, Good at, Used in, Extra options (JSON), Memory/context, Vision model | `ctx_length, limit_*, priority, capabilities, domains, kwargs` + product extras |
| **Used for** | Chat / Help / Memory | binding API |

\*Max output tokens may live in Extra options until schema adds a column — **UI still shows it** and maps to `kwargs.max_tokens` (honest label under field: “stored in extra options”).

### Card states

| State | Look |
|---|---|
| **● LIVE** | Blue border, “✓ Active” (the one chat uses) |
| Available | “Activate” button |
| Needs key | Warning chip + “Add key” |
| Test failed | Red chip + Retry |

### Add model
Same modal, empty Normal tab. **Add another model** after save.

---

## SCREEN 7C: SETTINGS — VOICE

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ☰ SOMA   Settings · Voice                                    [Save][Cancel] │
├──────────┬───────────────────────────────────────────────────────────────────┤
│ …        │  VOICE — how the agent speaks and listens                          │
│          │  ┌─────────────────────────────────────────────────────────────┐   │
│          │  │ Persona name          [Support voice               ]        │   │
│          │  │ Description           [Calm helper for calls       ]        │   │
│          │  │                                                             │   │
│          │  │ SPEAKING                                                      │   │
│          │  │   Voice ID            [en-US-AriaNeural     ▼]              │   │
│          │  │   Speaking speed      [1.0 ═════●═══════]                   │   │
│          │  │   Volume              [0.8 ═══════●════]                    │   │
│          │  │   Text-to-speech      [Azure                     ▼]        │   │
│          │  │                                                             │   │
│          │  │ LISTENING                                                     │   │
│          │  │   Speech-to-text      [Whisper                  ▼]         │   │
│          │  │   Listen language     [English (US)            ▼]          │   │
│          │  │   Detect when to stop [● on]                               │   │
│          │  │   Stop sensitivity    [0.5 ═════●═══════]                  │   │
│          │  │   Silence before stop [400] ms                            │   │
│          │  │                                                             │   │
│          │  │ REPLIES                                                       │   │
│          │  │   Model for voice     [openai/gpt-oss-120b   ▼]  (Models)  │   │
│          │  │   Persona instructions                                    │   │
│          │  │   ┌───────────────────────────────────────────────────┐   │   │
│          │  │   │ Speak simply. Confirm before actions.             │   │   │
│          │  │   └───────────────────────────────────────────────────┘   │   │
│          │  │   Creativity (temperature)  [0.7 ═════●════]              │   │
│          │  │   Max reply length          [2000]                        │   │
│          │  │                                                             │   │
│          │  │   [● on] Use this voice    [○] Make default                │   │
│          │  └─────────────────────────────────────────────────────────────┘   │
│          │  [Save voice]  [Test speak]  [Test listen]                        │
└──────────┴───────────────────────────────────────────────────────────────────┘
```

| Human label | Control | API |
|---|---|---|
| Persona name | text | `name` |
| Description | text | `description` |
| Voice ID | select/text | `voice_id` |
| Speaking speed | slider | `voice_speed` |
| Volume | slider | TTS volume |
| Text-to-speech | select | TTS provider |
| Speech-to-text | select | `stt_model` |
| Listen language | select | `stt_language` |
| Detect when to stop | toggle | `turn_detection_enabled` |
| Stop sensitivity | slider | `turn_detection_threshold` |
| Silence before stop (ms) | number | `silence_duration_ms` |
| Model for voice | select | `llm_config_id` |
| Persona instructions | textarea | `system_prompt` |
| Creativity (temperature) | slider | `temperature` |
| Max reply length | number | `max_tokens` |
| Use this voice | toggle | `is_active` |
| Make default | toggle | `is_default` |

**Test buttons:** Test speak · Test listen.

---

## SCREEN 7D: SETTINGS — INTERFACE

| Human label | Control | Notes |
|---|---|---|
| Theme | Dark / Light | P-06 |
| Language | select | UI language |
| Density | Comfortable / Compact | |
| Time format | 12h / 24h | |
| Timezone | select | Effective timezone shown |
| Show project bar | Mobile ○ Desktop ● | per-device |
| Show clock | Mobile ● Desktop ● | |
| Show connection status | Mobile ● Desktop ● | |
| Right panel | Mobile ○ Desktop ● | canvas rail |

---

## SCREEN 7E: SETTINGS — TOOLS

Keep Screen 9 tool cards (web, code, files, browser, documents, voice, git, email):  
**Enable** toggle · one-line description · 1–3 settings (timeout, max size).

---

## SCREEN 7F: SETTINGS — INTEGRATIONS (keys live here)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ☰ SOMA   Settings · Integrations                            [Save][Cancel]  │
├──────────┬───────────────────────────────────────────────────────────────────┤
│ …        │  PROVIDERS & KEYS     (write-only — never shown after save)       │
│          │  ┌─────────────────────────────────────────────────────────────┐   │
│          │  │ Groq          [● on]   key [● set]  address [api.groq…]     │   │
│          │  │   [Manage key] [Test connection]                            │   │
│          │  │ OpenAI        [● on]   key [○ missing]  address [api.openai]│   │
│          │  │   [Add key]   [Test connection]                             │   │
│          │  │ Ollama        [○ off]  key [—]  address [localhost:11434]   │   │
│          │  └─────────────────────────────────────────────────────────────┘   │
│          │  Secret storage: Vault · Events · OAuth  (Advanced links)         │
└──────────┴───────────────────────────────────────────────────────────────────┘
```

| Human label | Control |
|---|---|
| Provider on/off | toggle |
| Key | masked + Manage key / Add key |
| API address | text |
| Test connection | button → ok / ms / error |

---

## SCREEN 7G: SETTINGS — ADVANCED

| Human label | Control |
|---|---|
| Modules | card list (Screen 7 old module manager body) |
| Quotas | numbers |
| Experimental features | toggles |
| Backup / Restore | buttons |

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
