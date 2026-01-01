# SomaBrain + SomaFractalMemory - Master SRS Catalog

**Version:** 2.0.0  
**Date:** 2025-12-24  
**Status:** Pre-Implementation Complete

---

## 1. Document Classification

### 1.1 SRS Core Documents (docs/srs/somabrain/)

| # | Document | Lines | Coverage |
|---|----------|-------|----------|
| 1 | `platform-administration-complete.md` | 320 | ✅ Server settings, roles, deployment |
| 2 | `permission-matrix-complete.md` | 280 | ✅ 55 permissions, 6 roles |
| 3 | `multi-tenancy.md` | 250 | ✅ Tenant isolation, quotas |
| 4 | `subscription-billing.md` | 270 | ✅ Lago integration, tiers |
| 5 | `authentication-sso.md` | 200 | ✅ Keycloak, JWT |
| 6 | `api-gateway.md` | 180 | ✅ Rate limiting, routing |
| 7 | `memory-cognitive.md` | 170 | ✅ Cognitive architecture |
| 8 | `memory_management.md` | 220 | ✅ Working memory, promotion |
| 9 | `god-mode-admin.md` | 200 | ✅ Eye of God interface |
| 10 | `observability.md` | 130 | ✅ Metrics, logging |
| 11 | `security-classification.md` | 80 | ✅ RBAC |
| 12 | `settings-reference.md` | 360 | ✅ 300+ settings |
| 13 | `traceability-matrix.md` | 120 | ✅ Requirements tracing |

### 1.2 SRS SomaFractalMemory (docs/srs/somafractalmemory/)

| # | Document | Lines | Coverage |
|---|----------|-------|----------|
| 1 | `somafractalmemory-complete.md` | 342 | ✅ Models, API, graphs |
| 2 | `settings-reference.md` | 200 | ✅ 70+ settings |

### 1.3 SRS Unified (docs/srs/unified/)

| # | Document | Lines | Coverage |
|---|----------|-------|----------|
| 1 | `unified-memory-platform.md` | 280 | ✅ Integration architecture |
| 2 | `docker-deployment.md` | 200 | ✅ Full Docker stack |

### 1.4 SRS Admin UI (docs/srs/admin-ui/)

| # | Document | Lines | Coverage |
|---|----------|-------|----------|
| 1 | `god-mode-screen-map.md` | 280 | ✅ 18 screens |
| 2 | `user-journey-screens.md` | 360 | ✅ 38 screens, 20 use cases |

### 1.5 SRS API Specs (docs/srs/api-specs/)

| # | Document | Lines | Coverage |
|---|----------|-------|----------|
| 1 | `api-key-authentication.md` | 200 | ✅ Token auth flow |

### 1.6 SRS Flows (docs/srs/flows/) - 19 Documents

| # | Flow Document | Screens | Status |
|---|---------------|---------|--------|
| 1 | `eye-of-god-tenant-creation-flow.md` | 9 | ✅ |
| 2 | `eye-of-god-system-monitoring-flow.md` | 4 | ✅ |
| 3 | `eye-of-god-memory-administration-flow.md` | 4 | ✅ |
| 4 | `eye-of-god-billing-management-flow.md` | 4 | ✅ |
| 5 | `eye-of-god-user-administration-flow.md` | 4 | ✅ |
| 6 | `integrated-memory-operations-flow.md` | 3 | ✅ |
| 7 | `developer-api-integration-flow.md` | 5 | ✅ |
| 8 | `platform-onboarding-flow.md` | 6 | ✅ |
| 9 | `impersonation-flow.md` | 3 | ✅ |
| 10 | `tenant-creation-flow.md` | 4 | ✅ |
| 11 | `tenant-suspension-flow.md` | 3 | ✅ |
| 12 | `memory-operations-flow.md` | 4 | ✅ |
| 13 | `user-authentication-flow.md` | 3 | ✅ |
| 14 | `user-management-flow.md` | 3 | ✅ |
| 15 | `subscription-management-flow.md` | 4 | ✅ |
| 16 | `billing-invoices-flow.md` | 3 | ✅ |
| 17 | `audit-log-flow.md` | 3 | ✅ |
| 18 | `settings-configuration-flow.md` | 3 | ✅ |
| 19 | `README.md` | - | Index |

---

## 2. All User Journeys - Complete Catalog

### 2.1 Platform Administration (Super Admin)

| Journey | Document | Status |
|---------|----------|--------|
| Platform First-Time Setup | `platform-onboarding-flow.md` | ✅ |
| Server Settings Configuration | `settings-configuration-flow.md` | ✅ |
| Platform Health Monitoring | `eye-of-god-system-monitoring-flow.md` | ✅ |
| View Platform Metrics | `eye-of-god-system-monitoring-flow.md` | ✅ |
| Configure Alerts | `eye-of-god-system-monitoring-flow.md` | ✅ |
| Add Platform Admin | `eye-of-god-user-administration-flow.md` | ✅ |
| Remove Platform Admin | `eye-of-god-user-administration-flow.md` | ✅ |
| View Admin Activity Log | `eye-of-god-user-administration-flow.md` | ✅ |

### 2.2 Tenant Management (Platform Admin)

| Journey | Document | Status |
|---------|----------|--------|
| Create New Tenant | `eye-of-god-tenant-creation-flow.md` | ✅ |
| View All Tenants | `eye-of-god-tenant-creation-flow.md` | ✅ |
| Edit Tenant Details | `tenant-creation-flow.md` | ✅ |
| Suspend Tenant | `tenant-suspension-flow.md` | ✅ |
| Reactivate Tenant | `tenant-suspension-flow.md` | ✅ |
| Delete Tenant | `tenant-suspension-flow.md` | ✅ |
| Impersonate Tenant | `impersonation-flow.md` | ✅ |
| Exit Impersonation | `impersonation-flow.md` | ✅ |
| Override Tenant Quotas | `eye-of-god-tenant-creation-flow.md` | ✅ |

### 2.3 Billing & Revenue (Platform Admin)

| Journey | Document | Status |
|---------|----------|--------|
| View Revenue Dashboard | `eye-of-god-billing-management-flow.md` | ✅ |
| View All Subscriptions | `eye-of-god-billing-management-flow.md` | ✅ |
| Change Tenant Subscription | `subscription-management-flow.md` | ✅ |
| Apply Credit to Tenant | `eye-of-god-billing-management-flow.md` | ✅ |
| View All Invoices | `billing-invoices-flow.md` | ✅ |
| Export Invoice | `billing-invoices-flow.md` | ✅ |
| Configure Subscription Plans | `eye-of-god-billing-management-flow.md` | ✅ |

### 2.4 Memory Administration (Platform Admin)

| Journey | Document | Status |
|---------|----------|--------|
| Browse All Memories | `eye-of-god-memory-administration-flow.md` | ✅ |
| View Memory Details | `eye-of-god-memory-administration-flow.md` | ✅ |
| Delete Memory | `eye-of-god-memory-administration-flow.md` | ✅ |
| Platform Graph Explorer | `eye-of-god-memory-administration-flow.md` | ✅ |
| Purge Tenant Data | `eye-of-god-memory-administration-flow.md` | ✅ |
| Cleanup Stale Memories | `eye-of-god-memory-administration-flow.md` | ✅ |
| Cleanup Orphaned Links | `eye-of-god-memory-administration-flow.md` | ✅ |

### 2.5 Tenant User Journeys (Tenant Admin)

| Journey | Document | Status |
|---------|----------|--------|
| Tenant Login (SSO) | `user-authentication-flow.md` | ✅ |
| View Tenant Dashboard | `user-journey-screens.md` | ✅ |
| Invite Team Member | `user-management-flow.md` | ✅ |
| Remove Team Member | `user-management-flow.md` | ✅ |
| Change Member Role | `user-management-flow.md` | ✅ |
| Create API Key | `developer-api-integration-flow.md` | ✅ |
| Revoke API Key | `developer-api-integration-flow.md` | ✅ |
| Rotate API Key | `developer-api-integration-flow.md` | ✅ |
| View Usage Dashboard | `subscription-management-flow.md` | ✅ |
| View Billing History | `billing-invoices-flow.md` | ✅ |
| Change Subscription | `subscription-management-flow.md` | ✅ |

### 2.6 Memory Operations (Tenant User)

| Journey | Document | Status |
|---------|----------|--------|
| Store Memory | `integrated-memory-operations-flow.md` | ✅ |
| Recall Memory | `integrated-memory-operations-flow.md` | ✅ |
| Search Memories | `memory-operations-flow.md` | ✅ |
| Browse Memory Graph | `memory-operations-flow.md` | ✅ |
| Delete Memory | `memory-operations-flow.md` | ✅ |
| Link Memories | `somafractalmemory-complete.md` | ✅ |
| Find Memory Path | `somafractalmemory-complete.md` | ✅ |

### 2.7 Developer Journeys (API User)

| Journey | Document | Status |
|---------|----------|--------|
| Get API Key | `developer-api-integration-flow.md` | ✅ |
| Install SDK | `developer-api-integration-flow.md` | ✅ |
| First API Call | `developer-api-integration-flow.md` | ✅ |
| Handle Rate Limits | `developer-api-integration-flow.md` | ✅ |
| Handle Quota Exceeded | `developer-api-integration-flow.md` | ✅ |
| Debug API Errors | `developer-api-integration-flow.md` | ✅ |

### 2.8 Audit & Compliance (Platform Admin)

| Journey | Document | Status |
|---------|----------|--------|
| View Audit Log | `audit-log-flow.md` | ✅ |
| Filter Audit Events | `audit-log-flow.md` | ✅ |
| Export Audit Log | `audit-log-flow.md` | ✅ |

---

## 3. Document Statistics

| Category | Count |
|----------|-------|
| SRS Core Docs | 13 |
| SRS SomaFractalMemory | 2 |
| SRS Unified | 2 |
| SRS Admin UI | 2 |
| SRS API Specs | 1 |
| SRS Flows | 19 |
| **Total SRS Documents** | **39** |
| User Journeys Documented | **58** |
| UI Screens Documented | **56** |

---

## 4. Integration Architecture (Both Repos)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SHARED SERVICES (Docker)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  PostgreSQL :5432  │  Redis :6379  │  Milvus :19530  │  Kafka :9092       │
│  Keycloak :8080    │  Lago :3000   │  etcd :2379     │  MinIO :9000       │
└─────────────────────────────────────────────────────────────────────────────┘
                     │                               │
     ┌───────────────┴───────────────┐ ┌─────────────┴────────────────┐
     │                               │ │                              │
     ▼                               │ │                              ▼
┌─────────────────────────────────┐  │ │  ┌──────────────────────────────┐
│        SOMABRAIN                │  │ │  │     SOMAFRACTALMEMORY        │
│        Port: 9696               │  │ │  │     Port: 9595               │
├─────────────────────────────────┤  │ │  ├──────────────────────────────┤
│ Django + Django Ninja           │  │ │  │ Django + Django Ninja        │
│                                 │  │ │  │                              │
│ Features:                       │  │ │  │ Features:                    │
│ • ShortTerm Cache (WorkingMem)  │◄─┼─┼──│ • LongTerm Storage           │
│ • Multi-tenancy Management      │  │ │  │ • Graph Links                │
│ • Billing / Subscription        │──┼─┼──►• Vector Search (Milvus)     │
│ • API Key Authentication        │  │ │  │ • Coordinate-based Recall    │
│ • Rate Limiting / Quotas        │  │ │  │ • Namespace Isolation        │
│ • Eye of God Admin UI           │  │ │  │                              │
│ • Keycloak SSO                  │  │ │  │ Multi-tenancy: tenant field  │
│ • Lago Billing                  │  │ │  │                              │
└─────────────────────────────────┘  │ │  └──────────────────────────────┘
     │                               │ │                              │
     │         ┌─────────────────────┘ └─────────────────────┐        │
     │         │                                             │        │
     ▼         ▼                                             ▼        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UNIFIED WHEN TOGETHER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. SomaBrain manages tenants, billing, auth                                 │
│ 2. SomaBrain forwards LTM operations to SomaFractalMemory                  │
│ 3. Both share: PostgreSQL, Redis, Milvus, Kafka                            │
│ 4. Both use same tenant_id for isolation                                   │
│ 5. SomaFractalMemory can run STANDALONE with own auth                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Non-SRS Documentation (Reference)

### 5.1 Operational Docs (docs/operations/)

| Document | Purpose |
|----------|---------|
| `deployment-checklist.md` | Pre-deploy steps |
| `kafka-topic-naming.md` | Topic conventions |
| `retrieval-observability.md` | Metrics |
| `learner-and-planner.md` | AI components |
| `playbooks/*.md` (5 files) | Runbooks |

### 5.2 User Manual (docs/user/)

| Document | Purpose |
|----------|---------|
| `quick-start-tutorial.md` | Getting started |
| `installation.md` | Install guide |
| `features/*.md` (8 files) | Feature docs |
| `faq.md` | FAQ |

### 5.3 Technical Manual (docs/technical/)

| Directory | Files | Purpose |
|-----------|-------|---------|
| `api/` | 15+ | API reference |
| `memory/` | 5+ | Memory internals |
| `concepts/` | 10+ | Architecture concepts |

---

## 6. Coverage Summary

| Requirement | Status |
|-------------|--------|
| All user journeys documented | ✅ 58 journeys |
| All UI screens documented | ✅ 56 screens |
| Permission matrix complete | ✅ 55 permissions |
| Settings references complete | ✅ 370+ settings |
| Integration architecture | ✅ Unified diagram |
| Both repos can run independently | ✅ Documented |
| Both repos can run together | ✅ Documented |

**SRS IS COMPLETE. READY FOR IMPLEMENTATION.**

---

*Last Updated: 2025-12-24*
