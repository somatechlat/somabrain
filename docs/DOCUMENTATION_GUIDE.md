# SomaBrain Documentation Guide

**Standard Operating Procedure (SOP) for creating, maintaining, and publishing the SomaBrain documentation suite.**

---

## 1. Scope & Audience

| Audience | What they need from the docs | How this template helps them |
|----------|-----------------------------|------------------------------|
| New engineers / interns | Quick onboarding, local dev setup, architecture | Provides a **Quick‑Start** guide, architecture overview, and glossary. |
| Platform & SRE teams | Runbooks, incident response, SLO/SLA monitoring | Supplies **Process / System docs** (runbooks, security, observability). |
| Product & Delivery leads | Release checklists, rollback procedures, compliance evidence | Gives **Release & Change‑Management** documentation. |
| External partners / auditors | Compliance evidence, security controls, data‑classification | Delivers **Security & Compliance** docs, change logs, audit trails. |
| Automation bots (CI/CD, doc generators) | Structured source files, predictable naming, machine‑readable metadata | Enforces **file layout, naming conventions, CI linting, auto‑generation hooks**. |

---

## 2. The Four Core Manuals

All documentation is organized into four primary manuals, each serving a distinct audience.

| Manual | Audience | Purpose | File Location (Root) |
|---|---|---|---|
| **User Manual** | End-Users, Product Managers | Explains how to *use* SomaBrain to accomplish tasks. | `docs/user-manual/` |
| **Technical Manual** | System Administrators, SREs, DevOps | Explains how to *deploy, operate, and manage* the system. | `docs/technical-manual/` |
| **Development Manual** | Software Engineers, Contributors | Explains how to *build, modify, and contribute* to the codebase. | `docs/development-manual/` |
| **Onboarding Manual** | Agent Coders, New Team Members | Explains how to *quickly become productive* on the project. | `docs/onboarding-manual/` |

---

## 3. File‑Structure & Naming Conventions

```
/docs/
│
├─ user-manual/
│   ├─ index.md                     # Landing page
│   ├─ installation.md
│   ├─ quick-start-tutorial.md
│   ├─ features/
│   │   ├─ memory-operations.md
│   │   ├─ cognitive-reasoning.md
│   │   ├─ multi-tenant-usage.md
│   │   ├─ api-integration.md
│   │   └─ use-cases.md
│   └─ faq.md
│
├─ technical-manual/
│   ├─ index.md                     # Landing page
│   ├─ architecture.md              # C4 system overview
│   ├─ deployment.md                # Docker/K8s deployment
│   ├─ configuration.md             # Centralized config
│   ├─ monitoring.md                # Prometheus/Grafana
│   ├─ backup-and-recovery.md
│   ├─ runbooks/
│   │   ├─ api-service.md
│   │   ├─ memory-service.md
│   │   ├─ kafka-operations.md
│   │   └─ postgres-operations.md
│   └─ security/
│       ├─ secrets-policy.md
│       ├─ strict-mode.md
│       ├─ data-classification.md
│       └─ compliance-and-proofs.md
│
├─ development-manual/
│   ├─ index.md                     # Landing page
│   ├─ local-setup.md               # Dev environment
│   ├─ coding-standards.md
│   ├─ testing-guidelines.md
│   ├─ api-reference.md
│   ├─ contribution-process.md
│   ├─ learning-loop.md             # BHDC adaptive learning
│   └─ architecture-decisions/
│       └─ adr-template.md
│
├─ onboarding-manual/
│   ├─ index.md                     # Welcome
│   ├─ project-context.md           # Mission & goals
│   ├─ codebase-walkthrough.md      # Architecture tour
│   ├─ environment-setup.md         # Setup guide
│   ├─ first-contribution.md        # First PR guide
│   ├─ team-collaboration.md        # Communication
│   ├─ domain-knowledge.md          # Business logic
│   ├─ resources/
│   │   ├─ useful-links.md
│   │   ├─ troubleshooting.md
│   │   ├─ glossary.md
│   │   └─ roadmap.md
│   └─ checklists/
│       ├─ setup-checklist.md
│       ├─ pre-commit-checklist.md
│       └─ pr-checklist.md
│
├─ DOCUMENTATION_GUIDE.md         # This file
├─ style-guide.md                 # Global formatting rules
├─ changelog.md                   # Version history
└─ glossary.md                    # Global terminology
```

### Naming Rules

| Rule | Example | Rationale |
|------|---------|-----------|
| **kebab‑case** for file names | `memory-operations.md` | URL‑friendly, deterministic. |
| **singular** for directories | `runbooks/` | Keeps path depth shallow. |
| **prefixes** for related groups | `adr-`, `runbook-` | Logical grouping for search. |
| **Versioned files** use `vX.Y.Z` suffix only for release notes | `v0.2.0.md` | Chronological sorting. |

---

## 4. Content Blueprint

### 4.1 The User Manual (`docs/user-manual/`)

| Section | Content |
|---|---|
| **1. Introduction** | High-level overview of SomaBrain's cognitive memory capabilities. |
| **2. Installation** | Docker Compose and Kubernetes deployment instructions. |
| **3. Quick-Start Tutorial** | First `/remember` and `/recall` API calls. |
| **4. Core Features** | Memory operations, cognitive reasoning, multi-tenant usage, API integration, use cases. |
| **5. FAQ & Troubleshooting** | Common questions and solutions. |

### 4.2 The Technical Manual (`docs/technical-manual/`)

| Section | Content |
|---|---|
| **1. System Architecture** | C4 diagrams, BHDC math stack, service dependencies. |
| **2. Deployment** | Docker Compose (ports 9696, 20001-20007), Kubernetes (LoadBalancer 20020-20027), persistent volumes. |
| **3. Configuration** | Centralized .env (126 vars), ConfigMap (96 vars), secrets management. |
| **4. Monitoring & Health** | Prometheus metrics, Grafana dashboards, health endpoints. |
| **5. Operational Runbooks** | API service, memory service, Kafka, PostgreSQL procedures. |
| **6. Backup & Recovery** | Volume snapshots, disaster recovery procedures. |
| **7. Security** | Secrets policy, strict mode, RBAC, compliance. |

### 4.3 The Development Manual (`docs/development-manual/`)

| Section | Content |
|---|---|
| **1. Local Environment Setup** | Python venv, dependencies, IDE configuration. |
| **2. Codebase Overview** | Repository structure (somabrain/, tests/, benchmarks/), key modules. |
| **3. Coding Standards** | PEP 8, Ruff, MyPy, formatting rules. |
| **4. API Reference** | FastAPI endpoints, schemas, authentication. |
| **5. Testing Guidelines** | Pytest suite (168 tests), fixtures, mocking strategies. |
| **6. Contribution Process** | Branching strategy, PR process, code review. |
| **7. Learning Loop** | BHDC implementation, AdaptationEngine, coordinated parameter updates. |

### 4.4 The Onboarding Manual (`docs/onboarding-manual/`)

| Section | Content |
|---|---|
| **1. Project Context & Mission** | Long-horizon cognitive agents, research platform goals. |
| **2. Codebase Walkthrough** | 164 Python files in somabrain/, 168 tests, 36 benchmarks. |
| **3. Development Environment Setup** | Step-by-step setup with verification commands. |
| **4. First Contribution Guide** | Pick starter issue, make changes, test, submit PR. |
| **5. Team Collaboration Patterns** | Communication channels, code review process. |
| **6. Domain Knowledge Transfer** | BHDC, UnifiedScorer, neuromodulators, working memory. |
| **7. Resources & Checklists** | Quick reference materials, troubleshooting guides. |

---

## 5. Review, Approval & Maintenance Process

1. **Pull‑Request (PR) Workflow**
   - Docs‑only PR must have the label `documentation`.
   - At least **one reviewer** from the owning team.
   - CI runs **markdownlint**, **link‑checker**.
   - PR cannot be merged if any lint error persists.

2. **Quarterly Documentation Audit**
   - Owner runs `scripts/audit-docs.py` which:
     - Checks for stale links.
     - Flags sections not updated in >90days.
     - Generates a **Documentation Health Report**.

3. **Feedback Loop**
   - Add a **"Was this page helpful?"** widget (simple star rating).
   - Export ratings weekly; if <4/5, open a "Doc‑Improvement" ticket.

4. **Retention & Archiving**
   - When a service is **deprecated**, move its runbook to `archive/` and add a deprecation notice.

---

## 6. Check‑list for Every New Documentation Piece

| ✅Item | Description |
|--------|-------------|
| **Purpose statement** | One sentence why the doc exists. |
| **Audience** | Who will read it. |
| **Prerequisites** | Tools or knowledge needed before reading. |
| **Step‑by‑step instructions** | Each command in a fenced code block, with expected output. |
| **Verification** | How to confirm success (e.g., `curl http://localhost:9696/health`). |
| **Common errors** | A table of symptoms → fixes. |
| **References** | Links to related docs, diagrams, API specs. |
| **Version badge** | Auto‑generated from git tag. |
| **Linter pass** | markdownlint CI succeeds. |
| **Link check** | All internal links resolve. |

---

## 7. Automation Hooks

| Hook | Tool | What it does |
|------|------|--------------|
| Markdown lint | `markdownlint-cli2` (GitHub Action) | Enforces style‑guide rules. |
| Link checker | `remark-validate-links` (GitHub Action) | Fails PR if any dead link. |
| Changelog validator | Custom Python script (`scripts/validate-changelog.py`) | Ensures version bump matches git tag. |

---

## 8. Glossary of Key Terms

| Term | Definition |
|------|------------|
| BHDC | Binary Hyperdimensional Computing – SomaBrain's encoding approach using permutation-based binding via elementwise multiplication. |
| UnifiedScorer | Component combining cosine similarity, FD salience, and recency signals to rank memories. |
| Neuromodulators | Control signals (dopamine, serotonin, noradrenaline, acetylcholine) that modulate recall behaviour. |
| Working Memory (WM) | In-memory layer (MultiTenantWM or MultiColumnWM) for sub-second retrieval. |
| Long-Term Memory (LTM) | Persistent memory backend accessed via HTTP endpoint. |
| Strict Real Mode | Deployment configuration that prohibits stubs/mocks and enforces end-to-end realism. |
| Runbook | Step‑by‑step operational guide for a specific service or incident. |
| SLO | Service‑Level Objective – a measurable performance target. |
| RBAC | Role‑Based Access Control – Kubernetes permission model. |

---

## 9. Final Remarks

- **Consistency is the KPI:** Every new doc must pass the *Check‑list* above.
- **Automation over manual:** Use the listed CI jobs to keep the docs *always* in sync with the codebase.
- **Living documentation:** Treat each markdown file as source code – version it, review it, test it.

> **When every team member follows this *Documentation Guide*, the entire SomaBrain knowledge base will be complete, searchable, up‑to‑date, and auditable – a true "single source of truth" for developers, operators, auditors, and automated tooling.**

---

**Version**: 0.2.0
**Last Updated**: 2025-01-18
**Owner**: SomaBrain Documentation Team
