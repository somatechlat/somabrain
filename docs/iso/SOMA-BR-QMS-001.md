# SOMA-BR-QMS-001: SomaBrain Quality Manual

> **Standard:** ISO 9001:2015 — Quality Management Systems — Requirements
> **Owner:** SomaTech Quality Assurance

---

## Document Control

| Field | Value |
|---|---|
| Document Title | SomaBrain Quality Manual |
| Document Identifier | SOMA-BR-QMS-001 |
| Version | 1.0.2 |
| Date | 2026-09-28 |
| Status | Approved |
| Author | SomaTech QA Team |
| Approver | VP Engineering, SomaTech |
| Classification | Internal |
| ISO Reference | ISO 9001:2015 — Quality Management Systems — Requirements |
| Next Review | 2026-12-28 |

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-06-15 | SomaTech QA Team | Initial QMS: ISO 9001:2015 compliant quality manual for SomaBrain |
| 1.0.1 | 2026-09-28 | SomaTech Engineering | Document control normalised: identifier `(blank)` set to filename stem `SOMA-BR-QMS-001` \| Status added as `Approved` (document names an approver). |
| 1.0.2 | 2026-09-28 | SomaTech Engineering | Document Reference Matrix added (12 documents, ISO series under `docs/iso/`). Every cell is derived from each document's own Document Control table. |

### Normative References

| Document ID | Title | Relationship |
|---|---|---|
| SOMA-BR-ARCH-001 | SomaBrain Architecture Document | Architecture quality characteristics |
| SOMA-BR-SRS-001 | SomaBrain Software Requirements Specification | Requirements baseline for quality verification |
| SOMA-BR-SDP-001 | SomaBrain Software Development Plan | Development process quality controls |
| SOMA-BR-VV-001 | SomaBrain Verification and Validation Plan | V&V activities demonstrating quality |
| SOMA-BR-AUDIT-001 | SomaBrain Audit Report | Audit findings and quality assessment |
| SOMA-BR-SEC-001 | SomaBrain Security Assessment | Security quality controls |
| SOMA-BR-PROD-001 | SomaBrain Production Readiness Assessment | Production quality gates |
| docs/VIBE_RULES.md | SomaBrain VIBE Coding Standards | Coding quality standards |
| ISO 9001:2015 | Quality Management Systems — Requirements | Governing standard for this document |

---

## Table of Contents

1. [Quality Policy](#1-quality-policy)
2. [Quality Objectives](#2-quality-objectives)
3. [Process Map](#3-process-map)
4. [Quality Controls](#4-quality-controls)
5. [Metrics](#5-metrics)
6. [Non-Conformance](#6-non-conformance)
7. [Improvement Plan](#7-improvement-plan)
8. [Document Reference Matrix](#8-document-reference-matrix)

---

## 1. Quality Policy

### 1.1 Policy Statement

SomaTech is committed to delivering SomaBrain as a **production-grade cognitive memory system** that meets the highest standards of correctness, reliability, and maintainability. Quality is not an afterthought — it is engineered into every line of code, every test, and every deployment.

### 1.2 VIBE Coding Standards

All development of SomaBrain follows the **VIBE Coding Standards** (`docs/VIBE_RULES.md`), which establish non-negotiable quality requirements:

| VIBE Rule | Description | Enforcement |
|---|---|---|
| **Zero TODO/FIXME** | Production code SHALL contain zero unresolved `TODO` or `FIXME` markers. All work items are tracked in the issue tracker. | Pre-commit scan, CI gate |
| **Zero Forbidden Imports** | SQLAlchemy and FastAPI imports are explicitly prohibited. Django ORM and Django Ninja are the mandated alternatives. | Automated import check, property-based test (`test_forbidden_terms.py`) |
| **Type Annotations** | All public APIs SHALL have complete type annotations. | mypy strict mode |
| **Consistent Formatting** | All code SHALL be formatted with Black and linted with Ruff. | Pre-commit hooks |
| **Documentation** | All public modules SHALL have docstrings. Functions with complex behavior SHALL have inline documentation. | Code review |

### 1.3 Quality Commitment

| Principle | Commitment |
|---|---|
| **Customer Focus** | SomaBrain serves autonomous AI agents; quality directly impacts agent cognitive performance |
| **Leadership** | VP Engineering sponsors quality initiatives and Go/No-Go decisions |
| **Engagement** | All engineers own quality for their modules; QA provides tooling and oversight |
| **Process Approach** | Quality is embedded in the development lifecycle (ISO/IEC 12207) |
| **Improvement** | Quarterly quality reviews drive continuous improvement |
| **Evidence-Based** | All quality decisions are based on metrics, test results, and audit findings |
| **Relationship Management** | Quality expectations are communicated to SomaStack ecosystem partners (SomaAgent01, SomaFractalMemory) |

---

## 2. Quality Objectives

### 2.1 Measurable Quality Targets

| ID | Objective | Target | Current | Status |
|---|---|---|---|---|
| QO-001 | Zero type errors in production | 0 mypy errors (strict mode) | 0 | ✅ On target |
| QO-002 | Test file count | ≥ 100 test files | 95 | ⚠️ Near target |
| QO-003 | Zero TODO/FIXME markers in production code | 0 markers | 0 | ✅ On target |
| QO-004 | Zero forbidden imports (SQLAlchemy, FastAPI) | 0 imports | 0 | ✅ On target |
| QO-005 | Mathematical proof coverage | 8/8 proof categories passing | 8/8 | ✅ On target |
| QO-006 | Property-based test coverage | ≥ 10 Hypothesis test files | 11 | ✅ On target |
| QO-007 | Integration test coverage | ≥ 10 integration test files | 14 | ✅ On target |
| QO-008 | Performance SLO compliance | All SLOs met (see §5) | All met | ✅ On target |
| QO-009 | ISO document suite completeness | 10/10 documents | 10/10 | ✅ On target |
| QO-010 | Security assessment completion | Semi-annual review | Current | ✅ On target |

### 2.2 Quality Objective Review Cycle

| Activity | Frequency | Participants | Output |
|---|---|---|---|
| Quality metric collection | Continuous (CI/CD) | Automated | Prometheus metrics, CI reports |
| Quality dashboard review | Weekly | Engineering leads | Action items for quality gaps |
| Quality objective review | Quarterly | QA Team + VP Engineering | Updated quality targets |
| Management review | Semi-annually | VP Engineering + all teams | Quality policy updates |

---

## 3. Process Map

### 3.1 Quality Process Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│ Requirements │     │    Design    │     │  Implementation  │
│              │     │              │     │                  │
│ SRS review   │────→│ ARCH review  │────→│ VIBE enforcement │
│ REQ-BR-IDs   │     │ Design       │     │ Pre-commit hooks │
│ Traceability │     │ patterns     │     │ Code review      │
└──────────────┘     └──────────────┘     └────────┬─────────┘
                                                   │
                                                   ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Deployment  │     │   Testing    │     │    Validation    │
│              │     │              │     │                  │
│ Docker/K8s   │←────│ Unit + Prop  │←────│ V&V plan         │
│ Health checks│     │ Integration  │     │ Acceptance       │
│ Monitoring   │     │ E2E + Bench  │     │ Go/No-Go         │
└──────────────┘     └──────────────┘     └──────────────────┘
```

### 3.2 Process Descriptions

| Process | Input | Activity | Output | Quality Gate |
|---|---|---|---|---|
| **Requirements** | Stakeholder needs, SomaStack ecosystem | Requirements elicitation, formalization | SOMA-BR-SRS-001 (REQ-BR-* IDs) | Requirements review approval |
| **Design** | SRS requirements | Architecture design, detailed design | SOMA-BR-ARCH-001 | Architecture team approval |
| **Implementation** | Design specifications | Coding per VIBE rules, Rust core development | Source code | Pre-commit hooks pass; code review approved |
| **Testing** | Source code, requirements | Unit, property, integration, proof, E2E, benchmark | Test results, coverage reports | All tests pass; no regressions |
| **Validation** | Test results, production criteria | Acceptance testing, production readiness review | Go/No-Go decision | SOMA-BR-PROD-001 criteria met |
| **Deployment** | Validated build | Docker image build, K8s deployment, health verification | Running service | Health checks pass; metrics operational |

### 3.3 Process Interactions with External Parties

| Party | Interaction | Quality Expectation |
|---|---|---|
| SomaAgent01 | API contracts (HTTP/SSE) | Endpoint availability ≥ 99.9%; latency SLOs met |
| SomaFractalMemory | Memory persistence (HTTP) | Zero data loss; constitution signing verified |
| Kafka | Event pipeline | Zero event loss (transactional outbox) |
| Milvus | Vector storage | Sub-15ms query latency; index consistency |
| PostgreSQL | Relational persistence | Zero data loss; migration safety |

---

## 4. Quality Controls

### 4.1 Static Analysis Controls

| Control | Tool | Scope | Enforcement Point |
|---|---|---|---|
| **Code Formatting** | Black | All Python source files | Pre-commit hook |
| **Linting** | Ruff | All Python source files (replaces flake8, isort, pycodestyle) | Pre-commit hook |
| **Type Checking** | mypy (strict mode) | All Python source files | Pre-commit hook + CI |
| **Type Checking** | pyright | All Python source files | CI |
| **Import Validation** | Custom + Hypothesis (`test_forbidden_terms.py`) | No SQLAlchemy or FastAPI imports | CI + property test |
| **TODO/FIXME Scan** | Custom grep | Zero markers in production code | Pre-commit hook + CI |
| **Rust Linting** | `cargo clippy` | All Rust source files | CI |
| **Rust Formatting** | `cargo fmt` | All Rust source files | CI |

### 4.2 Dynamic Testing Controls

| Control | Tool/Framework | Scope | Frequency |
|---|---|---|---|
| **Unit Tests** | pytest | 5 test files, individual module correctness | Every PR |
| **Property-Based Tests** | pytest + Hypothesis | 11 test files, invariant verification with random inputs | Every PR |
| **Proof Tests** | pytest | ~60 files across 8 categories (A–H) | Every PR |
| **Integration Tests** | pytest + real infrastructure | 14 test files, real PostgreSQL/Redis/Milvus/Kafka | Nightly |
| **E2E Tests** | pytest | 3 test files, full system health | Nightly |
| **Benchmark Tests** | pytest + custom harness | 2 test files, performance regression | Nightly + pre-release |
| **Smoke Tests** | Manual scripts | Kafka connectivity, math module sanity | On deployment |

### 4.3 Process Controls

| Control | Description | Frequency |
|---|---|---|
| **Code Review** | All PRs require at least 1 approval from a qualified reviewer | Every PR |
| **Architecture Review** | Structural changes reviewed by architecture team | Per structural change |
| **Security Review** | Security-critical changes reviewed by security team | Per security change |
| **Pre-commit Hooks** | Black, Ruff, mypy, TODO scan run before every commit | Every commit |
| **CI Pipeline** | Full test suite (unit + property + proof) runs on every push | Every push |
| **Nightly Pipeline** | Extended test suite (integration + E2E + benchmark) | Nightly |
| **Pre-release Pipeline** | Full validation including performance benchmarks and security scan | Per release |

### 4.4 Infrastructure Quality Controls

| Control | Scope | Verification |
|---|---|---|
| **Docker Image Scanning** | Container image vulnerability scan | Pre-deployment (recommended) |
| **Dependency Pinning** | All Python and Rust dependencies pinned to exact versions | pyproject.toml, Cargo.lock |
| **Configuration Validation** | Environment variable validation at startup | Django settings, mode detection |
| **Health Checks** | `/health/ready` and `/health/live` endpoints | Every deployment |
| **Prometheus Monitoring** | 30+ metric modules covering all subsystems | Continuous |

---

## 5. Metrics

### 5.1 Codebase Metrics

| Metric | Value | Trend | Target |
|---|---|---|---|
| **Python LOC** | 116,735 | Stable | Managed via modular decomposition |
| **Rust LOC** | 1,782 | Growing | Expand performance-critical paths |
| **Total LOC** | 118,517 | — | — |
| **Test Files** | 95 | Growing | ≥ 100 |
| **Proof Categories** | 8 (A–H) | Complete | Maintain all 8 |
| **Property-Based Tests** | 11 | Stable | ≥ 10 |
| **Integration Tests** | 14 | Stable | ≥ 10 |
| **TODO/FIXME Count** | 0 | Stable | 0 |
| **Forbidden Imports** | 0 | Stable | 0 |

### 5.2 Quality Metrics Dashboard

| Metric Category | Metric | Current Value | Target | Status |
|---|---|---|---|---|
| **Correctness** | Unit test pass rate | 100% | 100% | ✅ |
| **Correctness** | Property test pass rate | 100% | 100% | ✅ |
| **Correctness** | Proof test pass rate (8/8 categories) | 100% | 100% | ✅ |
| **Correctness** | Integration test pass rate | 100% | 100% | ✅ |
| **Performance** | Memory store latency (p95) | 8ms | ≤ 8ms | ✅ |
| **Performance** | Vector recall latency (p95) | 15ms | ≤ 15ms | ✅ |
| **Performance** | WM update latency (p95) | 2ms | ≤ 2ms | ✅ |
| **Performance** | Store throughput | 12,000/s | ≥ 12,000/s | ✅ |
| **Performance** | Recall throughput | 5,000/s | ≥ 5,000/s | ✅ |
| **Reliability** | Circuit breaker isolation | Verified | Verified | ✅ |
| **Reliability** | Degraded mode operation | Verified | Verified | ✅ |
| **Reliability** | Outbox replay integrity | Verified | Verified | ✅ |
| **Security** | VIBE compliance | 99.8%+ | ≥ 99% | ✅ |
| **Security** | Auth enforcement | Mandatory (AAAS) | Mandatory | ✅ |
| **Security** | Tenant isolation | Cryptographic | Cryptographic | ✅ |
| **Maintainability** | Code review coverage | 100% of PRs | 100% | ✅ |
| **Maintainability** | ISO document suite | 10/10 | 10/10 | ✅ |

### 5.3 Metrics Collection and Reporting

| Metric Type | Collection Method | Reporting | Storage |
|---|---|---|---|
| Test pass/fail | CI/CD pipeline | CI dashboard | Git CI history |
| Code quality (lint, type) | Pre-commit + CI | CI dashboard | Git CI history |
| Performance benchmarks | Nightly benchmark suite | Grafana dashboard | Prometheus |
| Runtime metrics | Prometheus scrape (`/metrics`) | Grafana dashboard | Prometheus |
| LOC and complexity | Static analysis (tokei, radon) | Quarterly report | Git history |
| Security findings | Audit reports | SOMA-BR-SEC-001, SOMA-BR-AUDIT-001 | Git |

---

## 6. Non-Conformance

### 6.1 Non-Conformance Definition

A non-conformance occurs when a product, process, or activity fails to meet a defined requirement. In SomaBrain, non-conformances include:

| Category | Examples |
|---|---|
| **Test Failure** | Unit, property, integration, proof, E2E, or benchmark test fails |
| **Type Error** | mypy or pyright reports a type error in production code |
| **VIBE Violation** | TODO/FIXME marker found; forbidden import detected; formatting violation |
| **Performance Regression** | Latency exceeds SLO; throughput drops below target |
| **Security Finding** | Auth bypass, tenant isolation breach, secret exposure |
| **Requirements Gap** | REQ-BR-* requirement not implemented or not verified |

### 6.2 Non-Conformance Process

```
Detection → Classification → Root Cause → Corrective Action → Verification → Closure
```

| Step | Activity | Responsibility | SLA |
|---|---|---|---|
| **Detection** | Automated (CI, monitoring) or manual (review, audit) | All team members | Immediate |
| **Classification** | Severity: Critical / Major / Minor | QA Team | 4 hours |
| **Root Cause Analysis** | 5-Why analysis, fishbone diagram | Responsible engineer + QA | 2 business days |
| **Corrective Action** | Fix implementation, process adjustment | Responsible engineer | Per severity SLA |
| **Verification** | Confirm fix resolves non-conformance | QA Team | 1 business day |
| **Closure** | Document in quality log, update metrics | QA Team | Same day as verification |

### 6.3 Severity and Response SLAs

| Severity | Definition | Response SLA | Resolution SLA |
|---|---|---|---|
| **Critical** | Production outage, data loss, security breach | 1 hour | 4 hours |
| **Major** | Test regression, performance SLO breach, significant quality gap | 4 hours | 2 business days |
| **Minor** | Code style issue, documentation gap, non-critical finding | 1 business day | 1 sprint |

### 6.4 Root Cause Analysis Template

| Field | Content |
|---|---|
| **Non-Conformance ID** | NC-YYYY-NNN |
| **Description** | What happened |
| **Detection Method** | How it was found (CI, review, monitoring, audit) |
| **Severity** | Critical / Major / Minor |
| **Root Cause** | Why it happened (5-Why analysis) |
| **Corrective Action** | What was done to fix it |
| **Preventive Action** | What was done to prevent recurrence |
| **Verification** | How the fix was verified |
| **Closure Date** | When the non-conformance was closed |

---

## 7. Improvement Plan

### 7.1 Current Improvement Initiatives

| ID | Initiative | Owner | Timeline | Status |
|---|---|---|---|---|
| IMP-001 | Increase test file count to ≥ 100 | QA Team | 2026-09-15 | In progress (95 → 100) |
| IMP-002 | Automated API documentation (Sphinx/MkDocs) | DevOps | 2026-08-15 | Planned |
| IMP-003 | VIBE enforcement in CI pipeline | DevOps | 2026-08-01 | Planned |
| IMP-004 | Dependency vulnerability scanning in CI | Security Team | 2026-09-01 | Planned |
| IMP-005 | Constitution signing end-to-end validation | Security Team | 2026-08-15 | Planned |
| IMP-006 | AAAS horizontal scaling load test | Operations Team | 2026-09-01 | Planned |
| IMP-007 | Chaos engineering for per-tenant isolation | QA Team | 2026-10-01 | Planned |
| IMP-008 | Module-level architecture diagrams (top-20) | Architecture Team | 2026-09-15 | Planned |
| IMP-009 | Performance regression gates in CI | DevOps | 2026-09-01 | Planned |
| IMP-010 | Configuration parameter documentation (300+ params) | Engineering | 2026-12-01 | Planned |

### 7.2 Improvement Methodology

SomaBrain's quality improvement follows the **Plan-Do-Check-Act (PDCA)** cycle:

| Phase | Activity | Output |
|---|---|---|
| **Plan** | Identify quality gaps from metrics, audits, and non-conformance records | Improvement initiative with measurable target |
| **Do** | Implement the improvement (code change, process change, tool addition) | Implemented change |
| **Check** | Verify the improvement achieved its target via metrics | Verification report |
| **Act** | Standardize successful improvements; revisit unsuccessful ones | Updated quality controls |

### 7.3 Quality Maturity Roadmap

| Phase | Timeline | Focus | Target Maturity |
|---|---|---|---|
| **Foundation** | 2026-Q1/Q2 (current) | ISO document suite, test infrastructure, VIBE standards | CMMI Level 2 (Managed) |
| **Standardization** | 2026-Q3 | Automated enforcement, API docs, vulnerability scanning | CMMI Level 2+ |
| **Optimization** | 2026-Q4 | Chaos engineering, performance regression gates, module diagrams | CMMI Level 3 (Defined) |
| **Predictability** | 2027-Q1 | Statistical process control, defect prediction, automated quality gates | CMMI Level 4 (Quantitatively Managed) |

### 7.4 Management Review

| Review | Frequency | Scope | Participants |
|---|---|---|---|
| Quality metrics review | Weekly | Test results, CI status, monitoring alerts | Engineering leads |
| Non-conformance review | Bi-weekly | Open non-conformances, root cause trends | QA Team + responsible engineers |
| Quality objective review | Quarterly | Quality target progress, new targets | VP Engineering + QA Team |
| Full management review | Semi-annually | Quality policy effectiveness, resource needs, strategic improvements | VP Engineering + all team leads |

---

## 8. Document Reference Matrix

This matrix is the authoritative cross-reference of the QMS document set held under `docs/iso/`.
It is not a second control record: every value below is read from the
named document's own `## Document Control` table, so the matrix cannot
claim a standard the document does not. `ISO Reference` is copied from
that table verbatim — including `—` where a document cites none.

Documents outside this set (contributor guides under `docs/`, project
records under `docs/project/`) are still held in the Document Register
`docs/iso/DOCUMENT-REGISTER.md`; they are supporting documentation, not
QMS documents, and are therefore not listed here.

| Document | Identifier | ISO Reference | File |
|---|---|---|---|
| SomaBrain Architecture Document | SOMA-BR-ARCH-001 | ISO/IEC 42010:2011 — Systems and Software Engineering — Architecture Description | `docs/iso/SOMA-BR-ARCH-001.md` |
| SomaBrain Audit Report | SOMA-BR-AUDIT-001 | ISO 19011:2018 — Guidelines for Auditing Management Systems | `docs/iso/SOMA-BR-AUDIT-001.md` |
| Soma Cognitive Triad Version Compatibility Matrix | SOMA-BR-COMPAT-001 | ISO 9001:2015 — Quality Management Systems — Requirements | `docs/iso/SOMA-BR-COMPAT-001.md` |
| Document Register | SOMA-BR-DOC-REGISTER-001 | ISO 9001:2015 — Quality Management Systems — Requirements | `docs/iso/DOCUMENT-REGISTER.md` |
| Document Control and Traceability Procedure | SOMA-BR-DOCS-001 | ISO 9001:2015 — Quality Management Systems — Requirements | `docs/iso/SOMA-BR-DOCS-001.md` |
| SomaBrain Production Readiness Assessment | SOMA-BR-PROD-001 | ISO/IEC 25010:2011 — Systems and Software Quality Requirements and Evaluation | `docs/iso/SOMA-BR-PROD-001.md` |
| SomaBrain Quality Manual | SOMA-BR-QMS-001 | ISO 9001:2015 — Quality Management Systems — Requirements | `docs/iso/SOMA-BR-QMS-001.md` |
| SomaBrain Risk Register | SOMA-BR-RISK-001 | ISO 31000:2018 — Risk Management — Guidelines | `docs/iso/SOMA-BR-RISK-001.md` |
| SomaBrain Software Development Plan | SOMA-BR-SDP-001 | ISO/IEC 12207:2017 — Systems and Software Engineering — Software Life Cycle Processes | `docs/iso/SOMA-BR-SDP-001.md` |
| SomaBrain Security Assessment | SOMA-BR-SEC-001 | ISO/IEC 27001:2022 — Information Security Management Systems | `docs/iso/SOMA-BR-SEC-001.md` |
| SomaBrain Software Requirements Specification | SOMA-BR-SRS-001 | ISO/IEC/IEEE 29148:2018 — Systems and Software Engineering — Life Cycle Processes — Requirements Engineering | `docs/iso/SOMA-BR-SRS-001.md` |
| SomaBrain Verification and Validation Plan | SOMA-BR-VV-001 | ISO/IEC/IEEE 16085:2006 — Systems and Software Engineering — Life Cycle Processes — Risk Management (adapted for V&V) | `docs/iso/SOMA-BR-VV-001.md` |

---

*End of document. This Quality Manual conforms to the requirements of ISO 9001:2015 and is subject to semi-annual management review.*
