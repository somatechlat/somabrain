# SOMA AGENT — MODEL MANAGER UI SPECIFICATION

## Document Control

| Field | Value |
|---|---|
| Document Title | Model Manager — Card UI Specification |
| Document Identifier | SOMA-UI-MODEL-ADMIN-001 |
| Version | **2.1.0** |
| Date | 2026-10-07 |
| Status | Draft |
| Classification | Internal |
| Field truth | `somaAgent01/admin/llm/api.py` `ModelIn` / `ModelOut` / `SlotsUpdate` / `PresetIn` (117–209) |
| Supersedes | 2.0.0 (invented utility type, fake timeout/max_tokens, in-editor keys) |

## Revision History

| Version | Date | Description |
|---|---|---|
| 2.0.0 | 2026-10-07 | Card redesign draft |
| 2.1.0 | 2026-10-07 | **ADV-2 corrections:** schema-true fields only; keys never in model editor; slots ≠ roles; utility has no type; display_name + is_active restored; preset = slot bundle only |

---

## 1. Field truth (non-negotiable)

### 1.1 Model object (`ModelIn` / `ModelOut`)

| Field | Type | Card face | Editor |
|---|---|---|---|
| `name` | str | ✓ | input + model search |
| `display_name` | str | ✓ | input |
| `model_type` | `chat` \| `embedding` **only** | ✓ badge | select |
| `provider` | str | ✓ | select (may reset api_base/kwargs) |
| `api_base` | str | short | input |
| `capabilities` | list[str] | compact | tags |
| `priority` | int (default 50) | ✓ | number |
| `cost_tier` | free\|low\|standard\|premium | ✓ | select |
| `domains` | list[str] | compact | tags |
| `ctx_length` | int | ✓ | number |
| `limit_requests` | int | compact | number |
| `limit_input` | int | compact | number |
| `limit_output` | int | compact | number |
| `vision` | bool | ✓ | toggle |
| `kwargs` | dict | — | JSON / key=value |
| `is_active` | bool | ✓ | toggle |

**Not on ModelIn (never invent):** temperature, top_p, top_k, max_tokens, timeout, seed, stop, utility type, role checkboxes.

If product later needs temperature etc., they go in **`kwargs`** (escape hatch) or a **schema change** (separate decision).

### 1.2 Keys (never on ModelIn)

`ModelPatch` docstring: *"API keys are never accepted here"* (`api.py:139`).  
Keys: **provider / Vault only** (`PUT /secrets/providers/{id}`). Editor shows **status + link** to Providers & keys — no key field on the model card.

### 1.3 Slots (not roles on the model)

`SlotsUpdate`: `chat_model_id`, `utility_model_id`, `embedding_model_id` (+ optional `capsule_id`).  
UI: **Used as** = derived badges from slots; **Assign** = slot PUT from the card (not multi-role storage).

### 1.4 Utility type does not exist

`model_type` is only `chat` | `embedding`. Utility slot accepts **any existing model id** (`api.py` existence check).  
UI: list **all** models for Utility (not chat-only). Label: “Any model may be bound as Utility (API rule).”

### 1.5 Presets

`PresetIn`: `name`, three model ids, `notes` — **slot bundle only**. No per-preset model params (unlike agent-zero).

---

## 2. Screen — Model Manager (library)

**Route:** `/settings/models` (fix UX-001 map later to this single name).

```
┌────────────────────────────────────────────────────────────────────────────┐
│ SOMA  Settings / Models                                    [Library|Wiring]│
├──────────┬─────────────────────────────────────────────────────────────────┤
│ Library  │  Filter [model_type ▾] [active ▾]  Search [____________]  [+New]│
│ Wiring   │  ┌─ CARD (whole ModelIn object) ─┐ ┌─ CARD ─────────────────┐   │
│ Presets  │  │ ● Active  chat  ⚡ cost:low    │ │ ○ Active  embedding   │   │
│ Providers│  │ gpt-oss-120b                   │ │ text-embed-3-small    │   │
│ & keys   │  │ display: GPT-OSS 120B          │ │ OpenAI                │   │
│          │  │ Groq · api.groq.com/openai/v1  │ │ ctx 1536 · $low       │   │
│          │  │ ctx 131072 · vision ✓ · p=10   │ │ Used as: Embedding    │   │
│          │  │ Used as: Chat, Utility          │ │ [Expand] [Test]       │   │
│          │  │ Key: ●ok (provider)            │ └───────────────────────┘   │
│          │  │ [Expand] [Test]                │                             │
│          │  └────────────────────────────────┘                             │
│          │  ┌─ CARD expanded (all ModelIn fields) ─────────────────────┐   │
│          │  │ Identity  name / display_name / model_type / provider    │   │
│          │  │ Endpoint  api_base                    Key → Providers ⌁ │   │
│          │  │ Capacity  ctx_length  limit_requests  limit_input        │   │
│          │  │           limit_output  vision  is_active                │   │
│          │  │ Routing   priority  cost_tier  domains[]  capabilities[] │   │
│          │  │ Advanced  kwargs (JSON)                                 │   │
│          │  │ Wiring    Assign: [Chat] [Utility] [Embedding] (slots)  │   │
│          │  │ [Save] [Duplicate] [Delete…]                            │   │
│          │  └─────────────────────────────────────────────────────────┘   │
└──────────┴─────────────────────────────────────────────────────────────────┘
```

**Card face = complete identity of the stored model** (name, display_name, type, provider, endpoint, ctx, limits, vision, active, cost, priority, key status, used-as).

**Expanded = every `ModelIn` field** + slot assign + test. **No key input.**

---

## 3. Navigation / context

| Rule | Spec |
|---|---|
| One workspace | Library · Wiring · Presets · Providers & keys |
| Expand | in place + deep link `/settings/models/:id` |
| Assign | slot PUT from card or Wiring lane |
| Used as | live from slots; badge on card |
| Test | per model; error on that card |
| Keyboard | Tab / Enter / Esc / `/` |
| Permission | `system:view` read; `system:configure` model edit; `system:manage_integrations` providers/test |

---

## 4. What we take from agent-zero vs not

| Keep | Reject / adapt |
|---|---|
| model-field layout (label + description) | temperature as real field (use kwargs until schema grows) |
| Advanced collapse | keys inside model form (use Providers page) |
| Model search + confirm delete | Main/Utility/Embedding as model *forms* (use slots + badges) |
| | preset = full model configs (Soma preset = ids only) |

---

## 5. Acceptance

1. Editor fields **exactly** `ModelIn`/`ModelPatch` — no invented inputs.  
2. `display_name` and `is_active` editable and shown.  
3. No API-key input on model card (link to Providers).  
4. Utility lists all models (or documents API rule), not chat-only.  
5. Slot assign writes `SlotsUpdate`; badges reflect it.  
6. Card face shows the whole stored object without expand.  
7. Presets only bind three ids + notes.  

---

## 6. Out of scope

- Implementation (until operator orders code)  
- Changing `model_type` vocabulary or adding temperature columns (schema decisions)  
- Chat transcript / billing  
