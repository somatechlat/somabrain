# SRS-ARCHITECTURAL-PATTERNS

## Software Requirements Specification
### Modular Design Patterns for SOMA Stack

| **Document ID** | SRS-ARCH-PATTERNS-2026-001 |
|-----------------|----------------------------|
| **Version** | 1.0.0 |
| **Date** | 2026-01-21 |
| **Status** | APPROVED |
| **Standard** | ISO/IEC 25010:2023 |

---

## 1. Purpose

This document defines the **architectural patterns** enforced across all SOMA repositories to ensure maintainable, testable, and scalable code.

---

## 2. Core Patterns

### 2.1 Layered Separation Pattern

```
┌─────────────────────────────────────┐
│  API Layer (endpoints/*.py)         │
│  HTTP routing, auth, serialization  │
├─────────────────────────────────────┤
│  Schema Layer (schemas.py)          │
│  Pydantic models, validation        │
├─────────────────────────────────────┤
│  Service Layer (services/*.py)      │
│  Business logic, orchestration      │
├─────────────────────────────────────┤
│  Model Layer (models/*.py)          │
│  SQLAlchemy ORM, persistence        │
└─────────────────────────────────────┘
```

**Rule:** Dependencies flow downward only.

---

### 2.2 Modular Service Decomposition

Large modules are decomposed into focused sub-modules:

```
somabrain/
├── app.py              # FastAPI application setup
├── app/
│   ├── opa.py              # OPA integration
│   ├── error_handler.py    # Error handling
│   ├── middleware.py       # Middleware stack
│   └── routes.py           # Route registration
```

---

### 2.3 Schema-Endpoint Separation

**Rule:** Data contracts in `schemas.py`, HTTP handlers in `endpoints/*.py`.

---

### 2.4 Domain Model Segregation

Models split by **bounded context**:

```
saas/
├── models.py      → Split to:
│   ├── tenant.py          # Tenant domain
│   ├── subscription.py    # Billing domain
│   └── user.py            # User domain
```

---

### 2.5 Enum Extraction Pattern

Enums and constants in dedicated modules to avoid circular imports.

---

## 3. Quality Requirements

| Metric | Target |
|--------|--------|
| Max lines per file | 650 (VIBE Rule 245) |
| Cyclomatic complexity | ≤10 per function |
| Test coverage | ≥80% |

---

## 4. Applies To

All `api/`, `saas/`, and `common/` modules in SomaBrain.
