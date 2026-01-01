# SomaBrain Global Glossary

**Purpose**: Provide a single source of truth for SomaBrain terminology so every manual uses consistent, approved language.

**Audience**: All SomaBrain contributors, reviewers, auditors, and automation that reference documentation vocabulary.

**Prerequisites**: Familiarity with SomaBrain's four-manual structure and high-level platform capabilities.

---

## Quick Navigation
- [Core Concepts](#core-concepts)
- [Architecture Components](#architecture-components)
- [Operations & Reliability](#operations--reliability)
- [Security & Compliance](#security--compliance)
- [Acronyms & Abbreviations](#acronyms--abbreviations)
- [Verification](#verification)
- [Common Errors](#common-errors)
- [References](#references)

---

## Core Concepts

### Cognitive Memory
**Definition**: SomaBrain's semantic memory system that stores and recalls information based on meaning instead of literal string matching.
**Usage**: "Cognitive memory enables AI assistants to recall context-aware conversations."
**See also**: [Memory Operations Guide](user/features/memory-operations.md)

### Hyperdimensional Computing (HDC)
**Definition**: Mathematical framework using high-dimensional vectors (hypervectors) to represent and manipulate information.
**Usage**: "Hyperdimensional computing powers SomaBrain's semantic similarity scoring."
**See also**: [Cognitive Reasoning Guide](user/features/cognitive-reasoning.md)

### Strict Real Mode
**Definition**: Deployment configuration that prohibits stubs, mocks, or dummy data paths and enforces end-to-end realism.
**Usage**: "Enable strict real mode in CI to prevent silent fallback to placeholder services."
**See also**: [Security Policies](technical/security/secrets-policy.md)

### Multi-Tenant Working Memory
**Definition**: In-memory layer that isolates active memories per tenant for sub-second retrieval.
**Usage**: "Each tenant receives an isolated working memory namespace managed by Redis."
**See also**: [Multi-Tenant Usage](user/features/multi-tenant-usage.md)

---

## Architecture Components

### SomaBrain API
**Definition**: FastAPI service exposing memory, reasoning, and health endpoints.
**Ownership**: Platform Engineering.
**References**: [Technical Architecture](technical/architecture.md)

### Density Matrix (ρ)
**Definition**: Matrix that preserves relationships among memories to enable second-order recall.
**Invariant**: `abs(trace(ρ) - 1) < 1e-4`.
**References**: [Development Manual](development/index.md)

### Unified Scorer
**Definition**: Component that combines cosine similarity, recency, and frequency signals to rank memories.
**Configuration**: Adjust weights in `config/sandbox.tenants.yaml`.

### Neuromodulators
**Definition**: Control signals that modulate recall behaviour (e.g., salience boosts for critical items).
**Usage**: "Neuromodulators bias the scorer toward safety-critical memories during incidents."

---

## Operations & Reliability

### Runbook
**Definition**: Operational playbook containing verified troubleshooting and recovery procedures.
**Location**: `docs/technical/runbooks/`.

### Release Health Gating
**Definition**: Operational checks (metrics, smoke tests, security gates) required before promoting a release.
**Location**: `docs/technical/runbooks/release-health-gating.md`.

### Disaster Recovery (DR)
**Definition**: Tested process for restoring service after catastrophic failure, including RTO/RPO commitments.
**Location**: `docs/technical/backup-and-recovery.md`.

### Golden Dataset
**Definition**: Curated dataset used to validate memory and reasoning invariants before release.
**Location**: [Testing Guidelines](development/testing-guidelines.md).

---

## Security & Compliance

### Secrets Policy
**Definition**: Requirements for generating, storing, rotating, and auditing secrets across SomaBrain environments.
**Location**: `docs/technical/security/secrets-policy.md`.

### RBAC Matrix
**Definition**: Role-based access definitions mapping duties to explicit permissions and approval workflows.
**Location**: `docs/technical/security/rbac-matrix.md`.

### Compliance Bundle
**Definition**: Consolidated evidence package containing penetration tests, formal proofs, SLO results, and signed attestations.
**Location**: `docs/technical/security/compliance-and-proofs.md`.

### Audit Trail
**Definition**: Immutable log of operations (memory APIs, admin changes) used for forensic analysis and regulatory inquiries.
**Location**: [Monitoring Guide](technical/monitoring.md).

---

## Acronyms & Abbreviations

| Acronym | Definition | Notes |
|---------|------------|-------|
| API | Application Programming Interface | Exposed via FastAPI (`/remember`, `/recall`, `/reason`). |
| BHDC | Binary Hyperdimensional Computing | SomaBrain's encoding approach for semantic vectors. |
| DR | Disaster Recovery | See backup-and-recovery procedures for RTO/RPO. |
| MFA | Multi-Factor Authentication | Mandatory for elevated roles per RBAC matrix. |
| Retrieval | Unified retrieval pipeline | Consolidated surface for recall across vector/graph/WM/lexical. |
| SLA | Service-Level Agreement | Contractual uptime/latency commitments cited in release health gating. |
| SLO | Service-Level Objective | Measurable performance targets validated in monitoring dashboards. |

---

## Verification
- Confirm new terms appear in this glossary before referencing them in manuals.
- Cross-check definitions against owning manual (`user`, `technical`, `development`, `onboarding`) during quarterly doc audits.
- Run `markdownlint` and the documentation link checker to ensure anchors resolve to the referenced files.

---

## Common Errors

| Issue | Symptom | Resolution |
|-------|---------|------------|
| Terminology drift | Docs introduce synonyms (e.g., "AI memory") | Replace with canonical terms listed here (`cognitive memory`). |
| Broken references | Glossary links point to moved or renamed docs | Update link targets when filing PRs that relocate documentation. |
| Missing ownership | Term lacks responsible team | Add ownership note to glossary entry and notify doc maintainers. |

---

## References
- `docs/style-guide.md` for formatting and terminology rules.
- `docs/onboarding/resources/glossary.md` for extended domain-specific definitions.
- `docs/technical/index.md` for system-level references supporting glossary terms.
- `docs/development/index.md` for contributor-focused concepts.
