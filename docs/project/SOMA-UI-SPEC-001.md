# SOMA AGENT — DEFINITIVE UI/UX SPECIFICATION

## Document Control

| Field | Value |
|---|---|
| Document Title | Soma Agent Definitive UI/UX Specification |
| Document Identifier | SOMA-UI-SPEC-001 |
| Version | 2.0.0 |
| Date | 2026-06-15 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | — |
| Classification | Internal |
| ISO Reference | ISO 9241-210:2019 — Human-centred design |
| Next Review | 2026-12-28 |
## Revision History
| 1.1.0 | 2026-10-07 | SomaTech Engineering | soma-model-card/editor/field; soma-used-for; parity with Agent Zero fields. |

| Version | Date | Author | Description |
|---|---|---|---|
| 2.0.0 | 2026-09-28 | SomaTech Engineering | Document control normalised: prior status `Baseline` normalised to `Draft` (no approver named). |


## 1. BRAND IDENTITY

### 1.1 Color System (from somatech.dev + yachaq.ai)

```
PRIMARY PALETTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Soma Black       #0A0A0A    Backgrounds, primary surfaces
Soma Dark        #111111    Card backgrounds, panels
Soma Surface     #1A1A1A    Elevated surfaces, inputs
Soma Border      #2A2A2A    Borders, dividers
Soma Muted       #666666    Secondary text, labels
Soma Text        #E5E5E5    Primary text
Soma White       #FFFFFF    Headings, emphasis

ACCENT COLORS (from Yachaq gradient)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Soma Blue        #3B82F6    Primary action, links, focus
Soma Indigo      #6366F1    Secondary accent, gradients
Soma Violet      #8B5CF6    Tertiary accent, badges
Soma Gradient    linear-gradient(135deg, #3B82F6, #8B5CF6)

STATUS COLORS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Success          #10B981    Online, healthy, confirmed
Warning          #F59E0B    Degraded, attention needed
Error            #EF4444    Failed, critical, danger
Info             #3B82F6    Informational

TYPOGRAPHY (from SomaTech + Yachaq)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Heading Font     Inter, -apple-system, sans-serif
Body Font        Inter, -apple-system, sans-serif
Mono Font        JetBrains Mono, Fira Code, monospace

Heading 1        32px / 700 / 1.2
Heading 2        24px / 600 / 1.3
Heading 3        18px / 600 / 1.4
Body             14px / 400 / 1.6
Caption          12px / 400 / 1.4
Code             13px / 400 / 1.5 (JetBrains Mono)

SPACING (4px grid)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

xs:  4px     sm:  8px     md:  12px
lg:  16px    xl:  24px    2xl: 32px
3xl: 48px    4xl: 64px

BORDER RADIUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

sm:  4px (inputs, badges)
md:  8px (cards, buttons)
lg:  12px (modals, panels)
xl:  16px (hero cards)
full: 9999px (pills, avatars)

SHADOWS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

sm:  0 1px 2px rgba(0,0,0,0.3)
md:  0 4px 12px rgba(0,0,0,0.4)
lg:  0 8px 24px rgba(0,0,0,0.5)
glow: 0 0 20px rgba(59,130,246,0.15)  (accent glow on focus)
```

### 1.2 Logo

```
SOMA
  └─ Wordmark: "SOMA" in Inter 700, #FFFFFF
  └─ Icon: S lettermark in Soma Gradient circle
  └─ Tagline: "Cognitive AI Agent" in Inter 400, #666666
```

---

## 2. LAYOUT SYSTEM

### 2.1 Three-Panel Layout (improved from Agent Zero)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           TOP BAR (48px, fixed)                              │
│  [☰] [SOMA] [Agent Name ●]                    [🔍] [🔔] [⚙️] [👤]         │
├────────┬─────────────────────────────────┬───────────────────────────────────┤
│        │                                 │                                   │
│ LEFT   │         CHAT AREA               │         CANVAS                    │
│ PANEL  │         (flex: 1)               │         (400px, resizable)        │
│ 260px  │                                 │                                   │
│        │  ┌─────────────────────────┐    │  ┌─────────────────────────────┐  │
│ (fixed)│  │    Welcome Screen       │    │  │ [🌐][💻][📄][📁][🖥️][>_] │  │
│        │  │    (when no chat)       │    │  ├─────────────────────────────┤  │
│        │  └─────────────────────────┘    │  │                             │  │
│        │                                 │  │    Canvas Content            │  │
│        │  ┌─────────────────────────┐    │  │    (Browser/Code/Docs/      │  │
│        │  │    Message History      │    │  │     Files/Desktop/Terminal)  │  │
│        │  │    (scrollable)         │    │  │                             │  │
│        │  │                         │    │  │                             │  │
│        │  │    👤 User message      │    │  │                             │  │
│        │  │    🤖 Agent response    │    │  │                             │  │
│        │  │    💻 Code block        │    │  │                             │  │
│        │  │    🔧 Tool execution    │    │  │                             │  │
│        │  │                         │    │  │                             │  │
│        │  └─────────────────────────┘    │  └─────────────────────────────┘  │
│        │                                 │                                   │
│        │  ┌─────────────────────────┐    │                                   │
│        │  │    Chat Input Bar       │    │                                   │
│        │  └─────────────────────────┘    │                                   │
├────────┴─────────────────────────────────┴───────────────────────────────────┤
│                           STATUS BAR (24px, optional)                        │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Responsive Breakpoints

| Breakpoint | Width | Layout |
|------------|-------|--------|
| Desktop XL | >= 1440px | Sidebar 280px + Chat + Canvas 440px |
| Desktop | >= 1200px | Sidebar 260px + Chat + Canvas 400px |
| Laptop | >= 992px | Sidebar 240px + Chat + Canvas (collapsible) |
| Tablet | >= 768px | Sidebar (overlay) + Chat + Canvas (hidden) |
| Mobile | < 768px | Chat only, hamburger for sidebar |

---

## 3. SCREEN SPECIFICATIONS

### 3.1 WELCOME SCREEN (shown when no active chat)

Agent Zero has a welcome screen. Ours will be better — it shows the agent's capabilities, recent activity, and quick actions.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│                              ┌──────────┐                                    │
│                              │   SOMA   │                                    │
│                              └──────────┘                                    │
│                                                                              │
│                        Welcome back, Test User                               │
│                                                                              │
│                    ┌──────────────────────────────┐                          │
│                    │  What can I help you with?   │                          │
│                    │                              │                          │
│                    │  [Type a message...]     ➤   │                          │
│                    └──────────────────────────────┘                          │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ 💬           │  │ 💻           │  │ 📄           │  │ 🔍           │    │
│  │ Chat         │  │ Code         │  │ Write        │  │ Research     │    │
│  │ Ask anything │  │ Generate &   │  │ Documents &  │  │ Search &     │    │
│  │              │  │ debug code   │  │ reports      │  │ analyze      │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ 📊           │  │ 🌐           │  │ 🖥️           │  │ 🎤           │    │
│  │ Analyze      │  │ Browse       │  │ Desktop      │  │ Voice        │    │
│  │ Data &       │  │ Web &        │  │ Run desktop  │  │ Talk to      │    │
│  │ visualize    │  │ interact     │  │ apps         │  │ your agent   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                              │
│  Recent Conversations                                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ 💬 Analyze sales data Q3                    2 hours ago              │   │
│  │ 💬 Write API documentation                  Yesterday                │   │
│  │ 💬 Debug WebSocket connection               2 days ago              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│                    SomaTech LAT · Cognitive AI Agent                         │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Behavior:**
- Shows when user opens app or creates new chat
- Quick action cards start a new chat with a pre-filled system context
- Recent conversations clickable to resume
- Central input box is the primary CTA
- Background: subtle gradient from Soma Black to Soma Dark

---

### 3.2 LEFT PANEL (Sidebar)

```
┌────────────────────────┐
│ ┌────┐                 │
│ │ S  │ SOMA            │
│ └────┘                 │
├────────────────────────┤
│                        │
│  ┌──────────────────┐  │
│  │ 🔍 Search...     │  │
│  └──────────────────┘  │
│                        │
│  [+ New Chat]          │
│                        │
│  ── TODAY ──────────   │
│                        │
│  ▸ Analyze sales data  │
│    Soma Assistant       │
│    2 hours ago          │
│                        │
│  ▸ Write API docs      │
│    Code Assistant       │
│    Yesterday            │
│                        │
│  ▸ Debug WebSocket     │
│    Soma Assistant       │
│    2 days ago           │
│                        │
│  ── YESTERDAY ──────   │
│                        │
│  ▸ Research AI papers  │
│    Research Agent       │
│                        │
│  ── THIS WEEK ──────   │
│                        │
│  ▸ Create landing page │
│    Code Assistant       │
│                        │
├────────────────────────┤
│  ┌──────────────────┐  │
│  │ 🤖 Soma Assistant│  │
│  │    🟢 Online     │  │
│  └──────────────────┘  │
│                        │
│  ┌────┐ ┌────┐ ┌────┐ │
│  │ ⚙️ │ │ 📦 │ │ 👤 │ │
│  │Set │ │Mod │ │Prof│ │
│  └────┘ └────┘ └────┘ │
└────────────────────────┘
```

**Components:**
- **Header**: Logo + collapse button
- **Search**: Filter conversations by text
- **New Chat**: Primary CTA button
- **Chat List**: Grouped by time (Today, Yesterday, This Week, Older)
- **Each Chat Item**: Title, agent name, timestamp, context menu (rename, delete, export, branch)
- **Agent Selector**: Shows current agent, click to switch
- **Bottom Bar**: Settings, Modules, Profile shortcuts

---

### 3.3 CHAT MESSAGE TYPES

#### User Message
```
┌─────────────────────────────────────────────────┐
│                                    👤 Test User  │
│  ┌───────────────────────────────────────────┐  │
│  │                                            │  │
│  │  Can you help me analyze this CSV data?    │  │
│  │                                            │  │
│  └───────────────────────────────────────────┘  │
│                                    2:34 PM  ✓   │
└─────────────────────────────────────────────────┘
```

#### Agent Text Response
```
┌─────────────────────────────────────────────────┐
│ 🤖 Soma Assistant                               │
│ ┌─────────────────────────────────────────────┐ │
│ │                                              │ │
│ │ Of course! I can help you analyze your CSV   │ │
│ │ data. Please share the file or paste the     │ │
│ │ data directly.                               │ │
│ │                                              │ │
│ │ Here's what I can do:                        │ │
│ │ - **Descriptive statistics** (mean, median)  │ │
│ │ - **Correlation analysis**                   │ │
│ │ - **Visualization** (charts, graphs)         │ │
│ │ - **Anomaly detection**                      │ │
│ │                                              │ │
│ └─────────────────────────────────────────────┘ │
│ 2:34 PM                              [Copy] [↩] │
└─────────────────────────────────────────────────┘
```

#### Agent Code Block
```
┌─────────────────────────────────────────────────┐
│ 🤖 Soma Assistant                               │
│ ┌─────────────────────────────────────────────┐ │
│ │ Here's a quick analysis:                     │ │
│ └─────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────┐ │
│ │ 🐍 Python                          [Copy][▶] │ │
│ │ ──────────────────────────────────────────── │ │
│ │  1 │ import pandas as pd                     │ │
│ │  2 │ import matplotlib.pyplot as plt         │ │
│ │  3 │                                        │ │
│ │  4 │ df = pd.read_csv('data.csv')            │ │
│ │  5 │ print(df.describe())                    │ │
│ │  6 │                                        │ │
│ │  7 │ df.hist(figsize=(12, 8))                │ │
│ │  8 │ plt.savefig('analysis.png')             │ │
│ └─────────────────────────────────────────────┘ │
│ 2:35 PM                              [Copy] [↩] │
└─────────────────────────────────────────────────┘
```

#### Agent Tool Execution
```
┌─────────────────────────────────────────────────┐
│ 🤖 Soma Assistant                               │
│ ┌─────────────────────────────────────────────┐ │
│ │ 🔧 Tool: web_search              [▶ Expand] │ │
│ │ ──────────────────────────────────────────── │ │
│ │ Input: "latest AI research 2026"             │ │
│ │ Output:                                      │ │
│ │   1. "GPT-5 Architecture Revealed"...        │ │
│ │   2. "New Breakthrough in RLHF"...           │ │
│ │   3. "Multi-Modal Agents Survey"...          │ │
│ │ Status: ✅ Success (1.2s)                    │ │
│ └─────────────────────────────────────────────┘ │
│ 2:35 PM                              [Copy] [↩] │
└─────────────────────────────────────────────────┘
```

#### Agent Thinking / Streaming
```
┌─────────────────────────────────────────────────┐
│ 🤖 Soma Assistant                               │
│ ┌─────────────────────────────────────────────┐ │
│ │ 🧠 Thinking...                          [✕] │ │
│ │ ──────────────────────────────────────────── │ │
│ │ Analyzing data structure...                  │ │
│ │ Calculating statistics...                    │ │
│ │ Generating visualization...                  │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

---

### 3.4 CHAT INPUT BAR

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────────┐    │
│ │ 📎  Ask anything...                                          🎤 ➤ │    │
│ └─────────────────────────────────────────────────────────────────────┘    │
│  [📎 Attach] [🎤 Voice] [Model: gpt-oss-120b ▼] [Agent: Soma ▼] [Send ➤] │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Features:**
- **File attachment**: Click 📎 or drag-and-drop (supports images, PDFs, code files, CSVs)
- **Voice input**: Click 🎤 to record, Whisper transcribes
- **Model selector**: Quick switch between configured models
- **Agent selector**: Quick switch between agents
- **Send button**: Click ➤ or press Enter
- **Shift+Enter**: New line
- **Auto-resize**: Input grows as user types (max 200px)

---

### 3.5 CANVAS SURFACES

#### Browser Canvas
```
┌───────────────────────────────────────────────┐
│ [🌐 Browser]  ← → ↻   [https://example.com ] │
├───────────────────────────────────────────────┤
│                                               │
│  ┌───────────────────────────────────────┐   │
│  │                                       │   │
│  │        [Rendered Web Page]            │   │
│  │                                       │   │
│  │  Agent can: click, type, scroll,      │   │
│  │  take screenshots, read DOM           │   │
│  │                                       │   │
│  │  User can: annotate elements,         │   │
│  │  click to inspect, give directives    │   │
│  │                                       │   │
│  └───────────────────────────────────────┘   │
│                                               │
│ [📸 Screenshot] [🔍 Inspect] [✏️ Annotate]  │
└───────────────────────────────────────────────┘
```

#### Code Editor Canvas
```
┌───────────────────────────────────────────────┐
│ [💻 Code]  main.py   Python ▼   [Run ▶] [Save]│
├───────────────────────────────────────────────┤
│  1 │ import pandas as pd                       │
│  2 │                                           │
│  3 │ df = pd.read_csv('data.csv')              │
│  4 │ print(df.describe())                      │
├───────────────────────────────────────────────┤
│ Output:                                        │
│ ┌───────────────────────────────────────────┐ │
│ │        count   mean    std    min    max   │ │
│ │ price   100  1234.5  567.8   10.0  5000.0 │ │
│ │ qty     100    42.3   18.7    1.0   100.0 │ │
│ └───────────────────────────────────────────┘ │
│ [Clear] [Copy Output]                         │
└───────────────────────────────────────────────┘
```

#### Document Editor Canvas
```
┌───────────────────────────────────────────────┐
│ [📄 Document]  report.md   [Preview] [Export]  │
├───────────────────────────────────────────────┤
│  # Sales Report Q3                             │
│                                                │
│  ## Summary                                    │
│  Revenue increased by **23%** compared to Q2.  │
│                                                │
│  ## Key Metrics                                │
│  | Metric     | Q2      | Q3      | Change   │ |
│  |------------|---------|---------|----------| |
│  | Revenue    | $1.2M   | $1.5M   | +23%     │ |
│  | Customers  | 1,234   | 1,567   | +27%     │ |
│  | Churn      | 3.2%    | 2.8%    | -12%     │ |
│                                                │
│  ## Next Steps                                  │
│  - Expand to EU market                          │
│  - Launch enterprise tier                       │
│                                                │
└───────────────────────────────────────────────┘
```

---

### 3.6 SETTINGS SCREENS

#### Settings Hub
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ☰ SOMA   Settings                                                  👤       │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐  ┌──────────────────────────────────────────────────────┐  │
│  │             │  │                                                      │  │
│  │ CORE        │  │   Model Provider Configuration                        │  │
│  │ 🖥️ UI       │  │                                                      │  │
│  │ 🤖 Model    │  │   ┌──────────────────────────────────────────────┐  │  │
│  │ 🧠 Agent    │  │   │ Active: Groq                                 │  │  │
│  │ 🔧 Tools    │  │   │ Model: openai/gpt-oss-120b                   │  │  │
│  │             │  │   │ API Key: gsk_••••••••••••••••                │  │  │
│  │ MODULES     │  │   │ [Change] [Test Connection]                    │  │  │
│  │ 📦 Modules  │  │   └──────────────────────────────────────────────┘  │  │
│  │ 🔐 Auth     │  │                                                      │  │
│  │ 🛡️ Authz    │  │   Available Providers                                │  │
│  │ 💳 Billing  │  │   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │  │
│  │ 🔑 Secrets  │  │   │  Groq   │ │ OpenAI  │ │Anthropic│ │ Ollama  │  │  │
│  │ 📨 Events   │  │   │  ●      │ │  ○      │ │  ○      │ │  ○      │  │  │
│  │ ⚙️ Workflows│  │   └─────────┘ └─────────┘ └─────────┘ └─────────┘  │  │
│  │ 🔌 Plugins  │  │                                                      │  │
│  │ 📚 Skills   │  │   Ollama Configuration                                │  │
│  │ 🔗 MCP      │  │   ┌──────────────────────────────────────────────┐  │  │
│  │ 🎤 Voice    │  │   │ URL: http://localhost:11434                   │  │  │
│  │ 📧 Email    │  │   │ [Connect]                                     │  │  │
│  │ 📊 Analytics│  │   └──────────────────────────────────────────────┘  │  │
│  │ 📋 Audit    │  │                                                      │  │
│  │             │  │                                                      │  │
│  └─────────────┘  └──────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. USER JOURNEYS

### 4.1 First-Time Setup (Standalone)

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  docker  │───▶│  Login   │───▶│  Model   │───▶│  Create  │───▶│  Chat    │
│  run     │    │  Page    │    │  Setup   │    │  Agent   │    │  Works   │
│          │    │          │    │          │    │          │    │          │
│ One cmd  │    │ Email    │    │ Enter    │    │ Name,    │    │ Agent    │
│ starts   │    │ Password │    │ API key  │    │ prompt,  │    │ responds │
│ every-   │    │ Create   │    │ Select   │    │ tools    │    │ to user  │
│ thing    │    │ account  │    │ model    │    │          │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
   30 sec          1 min           1 min           2 min           Instant
```

### 4.2 Chat with Tools

```
User types: "Search for latest AI news and summarize"
    │
    ▼
┌─────────────────────────────────────────┐
│ Agent processes through V3 pipeline:    │
│                                         │
│ 1. Auth check ✓                         │
│ 2. Permission check ✓                   │
│ 3. Context build (5 lanes) ✓            │
│ 4. Model selection (Groq) ✓             │
│ 5. LLM decides: call web_search tool    │
│    ┌─────────────────────────────────┐  │
│    │ 🔧 Tool: web_search            │  │
│    │ Input: "AI news 2026"          │  │
│    │ Output: [3 search results]     │  │
│    │ Status: ✅ 1.2s                │  │
│    └─────────────────────────────────┘  │
│ 6. LLM generates summary from results   │
│ 7. Memory stored (PG + Brain + SFM)     │
│ 8. Response streamed to user            │
│    ┌─────────────────────────────────┐  │
│    │ Here are the latest AI         │  │
│    │ developments...                │  │
│    │ 1. GPT-5 Architecture...       │  │
│    │ 2. New RLHF Breakthrough...    │  │
│    └─────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

## 5. COMPONENT LIBRARY

### 5.1 Core Components

| Component | Tag | Purpose | Variants |
|-----------|-----|---------|----------|
| Button | `<soma-button>` | Primary action | primary, secondary, ghost, danger |
| Input | `<soma-input>` | Text input | default, search, textarea |
| Toggle | `<soma-toggle>` | Enable/disable | on/off |
| Select | `<soma-select>` | Dropdown | single, multi |
| Card | `<soma-card>` | Content container | default, hoverable, selected |
| Badge | `<soma-badge>` | Status indicator | success, warning, error, info |
| Avatar | `<soma-avatar>` | User/agent avatar | image, initials, icon |
| Toast | `<soma-toast>` | Notification | success, error, info, warning |
| Modal | `<soma-modal>` | Dialog | small, medium, large, fullscreen |
| Tooltip | `<soma-tooltip>` | Hover info | top, bottom, left, right |
| Loading | `<soma-loading>` | Spinner | spinner, skeleton, progress |
| Tabs | `<soma-tabs>` | Tab navigation | horizontal, vertical |
| Table | `<soma-table>` | Data table | sortable, filterable, paginated |

### 5.2 Chat Components

| Component | Tag | Purpose |
|-----------|-----|---------|
| Chat Container | `<soma-chat>` | Full chat layout |
| Message List | `<soma-message-list>` | Scrollable message container |
| Message | `<soma-message>` | Single message (user/agent) |
| Message Content | `<soma-message-content>` | Markdown rendered content |
| Code Block | `<soma-code-block>` | Syntax highlighted code |
| Tool Call | `<soma-tool-call>` | Collapsible tool execution |
| Chat Input | `<soma-chat-input>` | Input bar with attachments |
| Chat Sidebar | `<soma-chat-sidebar>` | Conversation list |
| Welcome Screen | `<soma-welcome>` | First-time / new chat screen |

### 5.3 Canvas Components

| Component | Tag | Purpose |
|-----------|-----|---------|
| Canvas Panel | `<soma-canvas>` | Right-side panel container |
| Canvas Tabs | `<soma-canvas-tabs>` | Tab bar for surfaces |
| Browser | `<soma-browser>` | Embedded browser |
| Code Editor | `<soma-code-editor>` | Code editor with run |
| Document Editor | `<soma-doc-editor>` | Markdown/WYSIWYG editor |
| File Browser | `<soma-file-browser>` | File tree + preview |
| Terminal | `<soma-terminal>` | Terminal emulator |
| Desktop | `<soma-desktop>` | VNC desktop viewer |

### 5.4 Settings Components

| Component | Tag | Purpose |
|-----------|-----|---------|
| Settings Layout | `<soma-settings>` | Settings page layout |
| Settings Nav | `<soma-settings-nav>` | Settings sidebar navigation |
| Settings Section | `<soma-settings-section>` | Settings group |
| Module Card | `<soma-module-card>` | Module toggle card |
| Provider Card | `<soma-provider-card>` | LLM provider card |
| **Model Card** | `<soma-model-card>` | Selectable model card (name, roles, ctx, status). Variants: default, hoverable, **selected** |
| **Model Editor** | `<soma-model-editor>` | Full `ModelIn` editor + Advanced collapse + Used for (see SOMA-UI-MODEL-ADMIN-001) |
| **Model Field** | `<soma-model-field>` | Label + control row for one model setting |
| **Used-for** | `<soma-used-for>` | Chat / Help / Memory binding summary (never "slot") |
| Secret Field | `<soma-secret-field>` | Masked input for secrets |

---

## 6. ACCESSIBILITY

| Requirement | Implementation |
|-------------|----------------|
| Keyboard navigation | Tab through all interactive elements, Enter to activate |
| Screen reader | ARIA labels, roles, live regions on chat messages |
| Color contrast | WCAG AA (4.5:1 text, 3:1 large text) |
| Focus indicators | Soma Blue outline, 2px offset |
| Reduced motion | `prefers-reduced-motion` disables animations |
| Font scaling | rem units, no fixed pixel fonts |
| High contrast | Optional high-contrast mode |

---

## 7. INTERNATIONALIZATION

| Language | Status |
|----------|--------|
| Spanish (ES) | Primary (SomaTech is Ecuador-based) |
| English (EN) | Secondary |
| Kichwa | Future (Yachaq LLM EC supports it) |

---

End of Document
