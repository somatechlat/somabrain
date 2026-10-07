# SOMA AGENT — SETTINGS & MODEL MANAGER

## Document Control

| Field | Value |
|---|---|
| Document Title | Settings Workspace and Model Manager |
| Document Identifier | SOMA-UI-MODEL-ADMIN-001 |
| Version | **3.0.0** |
| Date | 2026-10-07 |
| Status | Draft |
| Classification | Internal |
| Reference UX | `agent-zero-main/webui/components/settings/*` (section nav, Models + Voice in one place) |
| Field truth | `somaAgent01/admin/llm/api.py` `ModelIn` 117–135 |
| **Forbidden on screen** | The word **“slot”** and the tab zoo of four disconnected model pages |

## Revision History

| Version | Date | Description |
|---|---|---|
| 2.1.0 | 2026-10-07 | Schema-true ModelIn editor |
| 3.0.0 | 2026-10-07 | **Settings workspace** (agent-zero style). **Slots removed from UX.** One Settings page: Agent · Models · Voice · Interface · Tools · Integrations. Model = full CSS card. |

---

## 1. Product rule

**Click Settings → everything is there.**  
No jumping between mystery tabs. Left section nav + right content (same pattern as agent-zero `settings/agent/agent-settings.html`: Agent, Models, Voice, Workdir, Locale, Interface).

```
Settings
├── Agent          personality, prompts, behavior
├── Models         full model cards + connection
├── Voice          TTS / STT
├── Interface      theme, language, density
├── Tools          web, code, files, …
├── Integrations   providers, secrets, events
└── Advanced       modules, limits, experimental
```

**“Slot” never appears in the UI.**  
If we must describe binding, the words are **“Used for: Conversation · Helper · Embeddings”** on the card — a fact, not an admin noun.

---

## 2. Settings shell

```
┌──────────────────────────────────────────────────────────────────┐
│  SOMA        Settings                                            │
├──────────┬───────────────────────────────────────────────────────┤
│ Agent    │  (section content scrolls)                            │
│ Models   │                                                       │
│ Voice    │  [Agent]   [Models]   [Voice]   [Interface]   …       │
│ Interface│  (in-page anchors like agent-zero — or one panel)     │
│ Tools    │                                                       │
│ Integr.  │                                                       │
│ Advanced │                                                       │
└──────────┴───────────────────────────────────────────────────────┘
```

- Dark-first Soma palette (existing mockups COLOR KEY).  
- Section titles + short description (agent-zero `section-title` / `section-description`).  
- **One** settings entry from the app header — not five portals.

---

## 3. MODEL section (the beautiful card library)

### 3.1 What a model is (on screen)

A **CSS card is the entire model record** (every `ModelIn` field lives on that object):

`name` · `display_name` · `model_type` (chat \| embedding) · `provider` · `api_base` ·  
`capabilities` · `priority` · `cost_tier` · `domains` · `ctx_length` ·  
`limit_requests` · `limit_input` · `limit_output` · `vision` · `kwargs` · `is_active`

**Connection** (provider key) is **not** on the card body — one “Manage keys” link (Vault).

### 3.2 Collapsed card (complete at a glance)

```
┌─────────────────────────────────────────────────────────┐
│  ● Active     chat                    cost: standard    │
│  openai/gpt-oss-120b                                    │
│  GPT-OSS 120B · Groq                                    │
│  api.groq.com/openai/v1                                 │
│  ─────────────────────────────────────────────────────  │
│  ctx 131072 · in 0 · out 8192 · vision · priority 10    │
│  Used for: Conversation · Helper                        │
│  key ●ok                                   [ Expand ]  │
└─────────────────────────────────────────────────────────┘
```

### 3.3 Expanded card (edit the whole model)

In-place expand (not a separate “slots” page):

| Group | Fields |
|---|---|
| Identity | name, display_name, model_type, provider |
| Endpoint | api_base · **Manage keys →** |
| Capacity | ctx_length, limit_requests, limit_input, limit_output |
| Flags | vision, is_active |
| Routing | priority, cost_tier, domains[], capabilities[] |
| Advanced | kwargs (JSON) |
| Used for | Conversation / Helper / Embeddings (bound in API as the three named bindings — **UI copy never says slot**) |
| Actions | Save · Test connection · Duplicate · Delete |

### 3.4 Used for (binding without “slots”)

On the card: simple toggles or “Set as …” menu items:

- **Conversation** (main chat model)  
- **Helper** (fast utility work)  
- **Embeddings** (memory/vectors)  

Implementation still calls `SlotsUpdate` / `PresetIn` internally. **User never sees “slot”.**

### 3.5 Library chrome

- Search · filter by type / active / used-for · **Add model**  
- Empty state: “Add a model + provider key”  
- Test errors on the card  

---

## 4. Other Settings sections (same shell)

### Agent
Personality, system prompt, temperature **of the agent behavior** (not fake ModelIn fields), tools policy.

### Voice
TTS / STT provider, voice id, volume, language — **always visible in Settings** (agent-zero `voice.html` section-title pattern). Grid of provider blocks.

### Interface
Theme (dark/light), language, density, chat layout, canvas.

### Tools
Web search, code, files, browser — enable cards.

### Integrations
Provider keys (Vault), events, secrets, OAuth — **keys live here**, linked from Models.

### Advanced
Modules, quotas, experimental.

---

## 5. Navigation / usability audit (what we fixed)

| Was | Now |
|---|---|
| Four tabs: providers / slots / presets / models | **One Settings → Models** library |
| Word “slot” everywhere | **Used for** / section names only |
| 3 naked dropdowns | **Model cards** with full data |
| Model settings split from Voice | **One shell** like agent-zero |
| Keys inside model editor | **Manage keys** → Integrations |
| Invented fields | **ModelIn only** + kwargs |

---

## 6. Acceptance

1. Header **Settings** opens the workspace with **Models and Voice** in the left nav.  
2. Zero UI strings contain `slot` / `slots`.  
3. Each model card shows the full identity block without expand.  
4. Expand edits every `ModelIn` field.  
5. Used-for Conversation/Helper/Embeddings from the card.  
6. Keys only under Integrations (write-only).  
7. Voice is a first-class Settings section, not buried.  

---

## 7. Out of scope

Code until the operator says **code**. Schema changes to ModelIn (e.g. temperature column) are a separate product decision.
