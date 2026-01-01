# SomaBrain Features

**Purpose** Orient users to the major feature areas documented in the User Manual.

**Audience** Product owners and developers who want a map of the available guides.

**Prerequisites** Complete the [Quick Start Tutorial](../quick-start-tutorial.md).

---

## Core Themes

- **Memory Operations** – `/remember`, `/recall`, cleanup and quotas.
- **Context & Feedback** – Evaluate prompts, submit feedback, inspect adaptation state.
- **Integration Patterns** – Required headers, error handling, and examples using curl/httpx.
- **Tenant Isolation** – How namespaces, quotas, and metrics remain tenant-aware.

---

## Feature Matrix

| Feature | What it Covers | Link |
|---------|----------------|------|
| Memory Operations | Payload schema, ingestion responses, recall output, deletion helpers. | [Memory Operations](memory-operations.md) |
| Cognitive Reasoning | `/context/evaluate`, `/context/feedback`, neuromodulators, sleep cycles. | [Cognitive Reasoning](cognitive-reasoning.md) |
| API Integration | Base URL, authentication, endpoint catalogue, httpx examples. | [API Integration](api-integration.md) |
| Multi-Tenant Usage | Tenant headers, namespaces, quotas, monitoring per tenant. | [Multi-Tenant Usage](multi-tenant-usage.md) |
| Use Cases | Reference scenarios lifted from the codebase and tests. | [Use Cases](use-cases.md) |

---

## Verification Checklist

1. Open each linked feature page and run at least one sample request against your environment.
2. Confirm that response examples match the live API (schemas defined in `somabrain/schemas.py`).
3. Re-run the documentation link checker before merging changes (`markdownlint` + link validation CI jobs).

---

## Common Pitfalls

| Issue | Why it Happens | Remedy |
|-------|----------------|--------|
| Feature links drift | Pages get renamed without updating the matrix. | Update this index whenever files move. |
| Samples diverge from API | Code changes land without doc updates. | Compare docs to the relevant module (app, schemas, services) during reviews. |
| Missing prerequisites | Feature pages assume Quick Start knowledge. | Keep prerequisites section accurate and cross-link to Quick Start. |

---

**Further Reading**

- [Technical Manual](../../technical/index.md) for operational and deployment guidance.
- [Development Manual](../../development/index.md) if you plan to modify or extend SomaBrain.
