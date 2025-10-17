# SomaBrain Features

**Purpose**: Provide a curated entry point to every SomaBrain feature area so users can quickly locate deeper guides.

**Audience**: Product managers, application developers, and power users exploring SomaBrain's capabilities.

**Prerequisites**: Complete the [Quick Start Tutorial](../quick-start-tutorial.md) and review the [Installation Guide](../installation.md).

---

## Quick Navigation
- [Core Concepts](#core-concepts)
- [Feature Matrix](#feature-matrix)
- [Why SomaBrain Changes Everything](#why-somabrain-changes-everything)
- [Verification](#verification)
- [Common Errors](#common-errors)
- [References](#references)

---

## Core Concepts

- **Cognitive Memory**: Understand how SomaBrain stores meaning-rich representations that outperform keyword search.
- **Multi-tenancy**: Learn how isolated working-memory spaces keep tenant data separate without sacrificing performance.
- **Cognitive Reasoning**: Explore higher-order reasoning workflows layered on top of memory recall.
- **API Workflows**: See how REST, SDKs, and batch pipelines interact with the platform.

---

## Feature Matrix

| Feature | Description | Dive Deeper |
|---------|-------------|-------------|
| **Memory Operations** | Store, recall, update, and manage memories with semantic guarantees. | [Memory Operations Guide](memory-operations.md) |
| **Cognitive Reasoning** | Chain memories, infer insights, and answer multi-hop questions. | [Cognitive Reasoning Guide](cognitive-reasoning.md) |
| **API Integration** | Integrate SomaBrain workflows into any application stack. | [API Integration Guide](api-integration.md) |
| **Multi-Tenant Usage** | Operate safely across customers, agents, or environments. | [Multi-Tenant Usage](multi-tenant-usage.md) |
| **Use Cases & Scenarios** | Map real-world problems to the correct feature set. | [Use Cases](use-cases.md) |

---

## Why SomaBrain Changes Everything
> *"The first AI memory system that thinks like Einstein but scales like the internet."*

### 🧠 Memory Systems That Never Forget
- **Multi-Tenant Working Memory**: Each user or agent receives an isolated memory space backed by Redis for sub-second recall.
- **Long-Term Memory Integration**: Persistent HTTP-backed storage keeps conversations available weeks later with full audit trails.
- **Salience Detection**: Frequency-domain analysis automatically elevates high-impact memories so relevant information surfaces first.
- **Memory Consolidation**: Background optimisation keeps retrieval fast by reorganising memories during low-traffic windows.

### ⚡ Breakthrough Mathematics That Just Works
- **BHDC Encoding**: Binary hypervectors capture semantic relationships, recognising that “car” and “automobile” share meaning.
- **Permutation Binding**: Role-based bindings connect facts ("Paris" + "capital of" + "France") for relational recall.
- **Quantum Layer Operations**: Superposition and cleanup operators combine partial concepts into precise search targets.
- **Deterministic Encoding**: Seeded randomness ensures consistent embeddings across sessions and environments.

### 📊 Relevance That Reads Your Mind
- **Unified Similarity**: Cosine, frequency, and recency signals combine to generate ranked, context-aware results.
- **Adaptive Weighting**: Configure scoring weights at runtime to prioritise recency, importance, or semantic distance.
- **Context Awareness**: Temporal metadata and task phase keep urgent memories ahead of stale ones.
- **Density Matrix Operations**: Second-order recall finds indirect relationships via the ρ matrix.

### 🏗️ Enterprise Without Compromise
- **Multi-Tenancy**: Hard isolation keeps customers safe while sharing infrastructure.
- **Rate Limiting**: Configurable quotas prevent noisy tenants from starving neighbours.
- **Audit Pipeline**: Structured logs and Kafka topics capture every operation for compliance.
- **Health Monitoring**: `/health`, `/metrics`, and dashboards highlight issues before users notice.

---

## Verification
- Confirm each table link resolves by running the documentation link checker (`markdownlint` and link validation jobs in CI).
- Follow at least one feature link and ensure the destination page contains working examples you can execute locally.
- Refresh this page whenever new modules ship to keep the Feature Matrix in sync with the product roadmap.

---

## Common Errors

| Issue | Symptom | Resolution |
|-------|---------|------------|
| Stale links | Clicking a feature returns 404 | Update the Feature Matrix entry when files move or rename. |
| Missing prerequisites | Readers lack setup context | Ensure installation and quick-start prerequisites remain accurate. |
| Redundant terminology | Features reintroduce deprecated phrases | Align wording with the [Global Glossary](../../glossary.md). |

---

## References
- `docs/user-manual/quick-start-tutorial.md` to complete initial workflow.
- `docs/technical-manual/index.md` for operational considerations behind the features.
- `docs/development-manual/index.md` if you plan to extend or contribute new capabilities.
