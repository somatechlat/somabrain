# Software Requirements Specification (SRS)
# SomaBrain SaaS Platform

**Document Version:** 1.0.0  
**Date:** 2025-12-24  
**Status:** DRAFT - Pending User Approval  
**Standard:** ISO/IEC/IEEE 29148:2018 Compatible

---

## 1. Introduction

### 1.1 Purpose
This SRS defines the functional and non-functional requirements for transforming SomaBrain into a fully SaaS-oriented cognitive platform with Lago billing integration.

### 1.2 Scope
| Item | Description |
|------|-------------|
| Product Name | SomaBrain SaaS Platform |
| Product Version | 2.0.0 |
| Target Framework | Django 5.x / Django Ninja |
| Billing Engine | Lago (self-hosted) |
| Identity Provider | Keycloak |
| Permissions | SpiceDB (ReBAC) |

### 1.3 Definitions and Acronyms
| Term | Definition |
|------|------------|
| SaaS | Software as a Service |
| Lago | Open-source billing/metering platform |
| ReBAC | Relationship-Based Access Control |
| Tenant | A billable customer organization |
| God Mode | Platform administrator (Tier 0) |
| VIBE | Verification, Implementation, Behavior, Execution (coding standard) |

### 1.4 7 Personas Perspective

| Persona | SaaS Feature Focus |
|---------|-------------------|
| 🎓 PhD Developer | Clean architecture, production-grade billing code |
| 🔍 PhD Analyst | Usage analytics, revenue metrics, data flow |
| ✅ PhD QA | Billing test automation, subscription edge cases |
| 📚 ISO Documenter | Audit trails, compliance records, invoicing |
| 🔒 Security Auditor | Payment PCI compliance, credential isolation |
| ⚡ Performance Engineer | Meter efficiency, DB query optimization |
| 🎨 UX Consultant | Billing UX, upgrade flows, usage dashboards |
| 🏗️ Django Architect | Django patterns for SaaS, middleware design |
| ⚙️ Django Expert | ORM for billing models, migrations |
| ⛪ Django Evangelist | NO non-Django billing libraries |

---

## 2. Complete SaaS Feature Requirements

### 2.1 Multi-Tenancy (CORE)

| REQ-ID | Requirement | Priority | Status |
|--------|-------------|----------|--------|
| REQ-MT-001 | All data MUST be isolated by `tenant_id` | CRITICAL | ✅ EXISTS |
| REQ-MT-002 | Tenant CRUD via Admin API | HIGH | ✅ EXISTS |
| REQ-MT-003 | Tenant metadata (name, contact, billing_email) | HIGH | ⚠️ PARTIAL |
| REQ-MT-004 | Tenant suspension/activation capability | HIGH | ❌ MISSING |
| REQ-MT-005 | Tenant soft-delete with data retention policy | MEDIUM | ❌ MISSING |

---

### 2.2 Subscription & Tier Management

| REQ-ID | Requirement | Priority | Status |
|--------|-------------|----------|--------|
| REQ-SUB-001 | Define subscription tiers (Free, Starter, Pro, Enterprise) | CRITICAL | ❌ MISSING |
| REQ-SUB-002 | Each tier MUST define feature flags and limits | CRITICAL | ❌ MISSING |
| REQ-SUB-003 | TenantSubscription model linking tenant to tier | CRITICAL | ❌ MISSING |
| REQ-SUB-004 | Subscription status (active, past_due, cancelled, trial) | HIGH | ❌ MISSING |
| REQ-SUB-005 | Trial period support with expiration | HIGH | ❌ MISSING |
| REQ-SUB-006 | Tier upgrade/downgrade API | HIGH | ❌ MISSING |
| REQ-SUB-007 | Proration handling on mid-cycle changes | MEDIUM | ❌ MISSING |

**Tier Structure:**

| Tier | API Calls/mo | Memory Ops/mo | Embeddings/mo | Price/mo |
|------|-------------|---------------|---------------|----------|
| Free | 1,000 | 500 | 100 | $0 |
| Starter | 10,000 | 5,000 | 1,000 | $49 |
| Pro | 100,000 | 50,000 | 10,000 | $199 |
| Enterprise | Unlimited | Unlimited | Unlimited | Custom |

---

### 2.3 Billing Integration (Lago)

| REQ-ID | Requirement | Priority | Status |
|--------|-------------|----------|--------|
| REQ-BILL-001 | Lago API client for Python/Django | CRITICAL | ❌ MISSING |
| REQ-BILL-002 | Customer creation in Lago on tenant creation | CRITICAL | ❌ MISSING |
| REQ-BILL-003 | Subscription assignment in Lago | CRITICAL | ❌ MISSING |
| REQ-BILL-004 | Usage event ingestion to Lago | CRITICAL | ❌ MISSING |
| REQ-BILL-005 | Invoice retrieval from Lago | HIGH | ❌ MISSING |
| REQ-BILL-006 | Webhook receiver for Lago events | HIGH | ❌ MISSING |
| REQ-BILL-007 | Billing settings in `settings.py` | HIGH | ❌ MISSING |

**Lago Events:**
- `customer.created` → Create local tenant billing record
- `subscription.started` → Activate tenant
- `subscription.terminated` → Suspend tenant
- `invoice.paid` → Update payment status
- `invoice.payment_failed` → Trigger payment failure flow

---

### 2.4 Usage Metering

| REQ-ID | Requirement | Priority | Status |
|--------|-------------|----------|--------|
| REQ-METER-001 | UsageRecord Django model | CRITICAL | ⚠️ PARTIAL (`TokenLedger`) |
| REQ-METER-002 | Real-time usage capture on API requests | CRITICAL | ❌ MISSING |
| REQ-METER-003 | Batch sync to Lago (configurable interval) | HIGH | ❌ MISSING |
| REQ-METER-004 | Metrics: `api_calls`, `memory_ops`, `embeddings`, `tokens` | HIGH | ⚠️ PARTIAL |
| REQ-METER-005 | Usage reporting API for tenants | HIGH | ❌ MISSING |
| REQ-METER-006 | Usage alerts (80%, 100% of limit) | MEDIUM | ❌ MISSING |
| REQ-METER-007 | Overage handling (block vs charge) | MEDIUM | ❌ MISSING |

---

### 2.5 Rate Limiting & Quotas

| REQ-ID | Requirement | Priority | Status |
|--------|-------------|----------|--------|
| REQ-QUOTA-001 | Per-tenant rate limits from tier | CRITICAL | ⚠️ PARTIAL (`quotas.py`) |
| REQ-QUOTA-002 | HTTP 429 response when limit exceeded | HIGH | ⚠️ PARTIAL |
| REQ-QUOTA-003 | Rate limit headers (X-RateLimit-*) | MEDIUM | ❌ MISSING |
| REQ-QUOTA-004 | Quota reset on billing cycle | HIGH | ❌ MISSING |
| REQ-QUOTA-005 | Burst allowance configuration | LOW | ❌ MISSING |

---

### 2.6 Self-Service Portal

| REQ-ID | Requirement | Priority | Status |
|--------|-------------|----------|--------|
| REQ-PORTAL-001 | Tenant admin can view subscription | HIGH | ❌ MISSING |
| REQ-PORTAL-002 | Tenant admin can view usage dashboard | HIGH | ❌ MISSING |
| REQ-PORTAL-003 | Tenant admin can view/download invoices | HIGH | ❌ MISSING |
| REQ-PORTAL-004 | Tenant admin can update payment method | MEDIUM | ❌ MISSING (Lago portal) |
| REQ-PORTAL-005 | Tenant admin can request upgrade | HIGH | ❌ MISSING |

---

### 2.7 Platform Admin (God Mode)

| REQ-ID | Requirement | Priority | Status |
|--------|-------------|----------|--------|
| REQ-ADMIN-001 | View all tenants with subscription status | CRITICAL | ⚠️ PARTIAL |
| REQ-ADMIN-002 | Revenue dashboard (MRR, ARR, churn) | HIGH | ❌ MISSING |
| REQ-ADMIN-003 | Create/suspend/delete tenants | HIGH | ⚠️ PARTIAL |
| REQ-ADMIN-004 | Override subscription tier manually | MEDIUM | ❌ MISSING |
| REQ-ADMIN-005 | View aggregated usage metrics | HIGH | ❌ MISSING |
| REQ-ADMIN-006 | Audit log of all billing events | HIGH | ⚠️ PARTIAL (`audit.py`) |

---

### 2.8 Authentication & SSO (Keycloak + Multi-Provider OAuth)

| REQ-ID | Requirement | Priority | Status |
|--------|-------------|----------|--------|
| REQ-AUTH-001 | Keycloak SSO integration | CRITICAL | ⚠️ PARTIAL |
| REQ-AUTH-002 | Google OAuth via Keycloak IDP | HIGH | ❌ MISSING |
| REQ-AUTH-003 | Facebook OAuth via Keycloak IDP | MEDIUM | ❌ MISSING |
| REQ-AUTH-004 | GitHub OAuth via Keycloak IDP | MEDIUM | ❌ MISSING |
| REQ-AUTH-005 | User-to-tenant assignment via JWT claims | CRITICAL | ⚠️ PARTIAL |
| REQ-AUTH-006 | Role-based access (super-admin, tenant-admin, tenant-user) | HIGH | ⚠️ PARTIAL |
| REQ-AUTH-007 | JWT validation for API requests | CRITICAL | ✅ EXISTS |
| REQ-AUTH-008 | Eye of God admin client (PKCE SPA) | CRITICAL | ❌ MISSING |
| REQ-AUTH-009 | SomaBrain API bearer-only client | CRITICAL | ⚠️ PARTIAL |
| REQ-AUTH-010 | Custom `somabrain-roles` client scope | HIGH | ❌ MISSING |
| REQ-AUTH-011 | `tenant_id` claim in JWT tokens | CRITICAL | ⚠️ PARTIAL |
| REQ-AUTH-012 | Realm roles: super-admin, tenant-admin, tenant-user, api-access | HIGH | ❌ MISSING |
| REQ-AUTH-013 | Identity Provider admin screen (CRUD) | CRITICAL | ❌ MISSING |
| REQ-AUTH-014 | OAuth secrets stored in Vault (NEVER env/DB) | CRITICAL | ❌ MISSING |
| REQ-AUTH-015 | Field-level granular permissions | HIGH | ❌ MISSING |
| REQ-AUTH-016 | User management admin screen | CRITICAL | ❌ MISSING |
| REQ-AUTH-017 | Role/Permission editor screen | HIGH | ❌ MISSING |

**OAuth Identity Providers (All Secrets in Vault):**

| Provider | Fields Required | Vault Path |
|----------|-----------------|------------|
| **Google** | client_id, client_secret, project_id, auth_uri, token_uri, certs_url, redirect_uris, javascript_origins | `vault://secrets/oauth/google/*` |
| **Facebook** | app_id, app_secret, graph_api_version, redirect_uris, scopes | `vault://secrets/oauth/facebook/*` |
| **GitHub** | client_id, client_secret, redirect_uris, scopes | `vault://secrets/oauth/github/*` |
| **Keycloak** | server_url, realm, client_id, client_secret | `vault://secrets/oauth/keycloak/*` |

**Keycloak Configuration:**

| Component | Configuration |
|-----------|---------------|
| Realm | `somabrain` |
| Eye of God Client | `eye-of-god-admin` (public, PKCE) |
| API Client | `somabrain-api` (bearer-only) |
| Google IDP | `google` (secrets from vault) |
| Facebook IDP | `facebook` (secrets from vault) |
| GitHub IDP | `github` (secrets from vault) |

**Design Documents:**
- [eye-of-god-auth-flows.md](./flows/eye-of-god-auth-flows.md) - User journeys & screen designs
- [admin-permissions-design.md](./flows/admin-permissions-design.md) - Permissions & admin screens

---

### 2.9 API Design (SaaS Patterns)

| REQ-ID | Requirement | Priority | Status |
|--------|-------------|----------|--------|
| REQ-API-001 | All endpoints require tenant context | CRITICAL | ✅ EXISTS |
| REQ-API-002 | OpenAPI 3.0 documentation | HIGH | ✅ EXISTS |
| REQ-API-003 | API versioning (v1, v2) | MEDIUM | ❌ MISSING |
| REQ-API-004 | Deprecation headers for old endpoints | LOW | ❌ MISSING |
| REQ-API-005 | Consistent error response schema | HIGH | ⚠️ PARTIAL |

---

### 2.10 Audit & Compliance

| REQ-ID | Requirement | Priority | Status |
|--------|-------------|----------|--------|
| REQ-AUDIT-001 | All billing events logged with timestamp | HIGH | ⚠️ PARTIAL |
| REQ-AUDIT-002 | User actions logged with actor ID | HIGH | ⚠️ PARTIAL |
| REQ-AUDIT-003 | Audit log retention (7 years for billing) | MEDIUM | ❌ MISSING |
| REQ-AUDIT-004 | Export audit logs API | LOW | ❌ MISSING |
| REQ-AUDIT-005 | GDPR data export for tenants | MEDIUM | ❌ MISSING |

---

### 2.11 Notifications

| REQ-ID | Requirement | Priority | Status |
|--------|-------------|----------|--------|
| REQ-NOTIF-001 | Email on subscription created | MEDIUM | ❌ MISSING |
| REQ-NOTIF-002 | Email on invoice generated | MEDIUM | ❌ MISSING (Lago) |
| REQ-NOTIF-003 | Email on payment failure | HIGH | ❌ MISSING (Lago) |
| REQ-NOTIF-004 | Email on tier upgrade/downgrade | MEDIUM | ❌ MISSING |
| REQ-NOTIF-005 | Usage alert notifications | MEDIUM | ❌ MISSING |

---

## 3. Non-Functional Requirements

### 3.1 Performance

| REQ-ID | Requirement | Metric |
|--------|-------------|--------|
| NFR-PERF-001 | API response time < 200ms p95 | Latency |
| NFR-PERF-002 | Usage metering overhead < 5ms | Overhead |
| NFR-PERF-003 | Lago sync batch < 1s for 1000 records | Throughput |
| NFR-PERF-004 | 10,000 concurrent tenants supported | Scalability |

### 3.2 Security

| REQ-ID | Requirement | Compliance |
|--------|-------------|------------|
| NFR-SEC-001 | All Lago API keys in Vault | SOC2 |
| NFR-SEC-002 | No PCI data stored locally (Lago handles) | PCI-DSS |
| NFR-SEC-003 | Tenant data isolation enforced at DB level | SOC2 |
| NFR-SEC-004 | Webhook signature verification | Security |

### 3.3 Availability

| REQ-ID | Requirement | Target |
|--------|-------------|--------|
| NFR-AVAIL-001 | Billing API uptime | 99.9% |
| NFR-AVAIL-002 | Graceful degradation if Lago unavailable | Resilience |
| NFR-AVAIL-003 | Usage sync retry with backoff | Reliability |

---

## 4. Summary: Feature Gap Analysis

| Category | Exists | Partial | Missing | Total |
|----------|--------|---------|---------|-------|
| Multi-Tenancy | 2 | 1 | 2 | 5 |
| Subscriptions | 0 | 0 | 7 | 7 |
| Billing (Lago) | 0 | 0 | 7 | 7 |
| Usage Metering | 0 | 2 | 5 | 7 |
| Rate Limits | 0 | 2 | 3 | 5 |
| Self-Service | 0 | 0 | 5 | 5 |
| Admin (God) | 0 | 3 | 3 | 6 |
| Auth/SSO | 1 | 3 | 1 | 5 |
| API Design | 2 | 1 | 2 | 5 |
| Audit | 0 | 2 | 3 | 5 |
| Notifications | 0 | 0 | 5 | 5 |
| **TOTAL** | **5** | **14** | **43** | **62** |

**Completion: 8% Exists, 23% Partial, 69% Missing**

---

## 5. Next Steps

1. **User Review**: Approve this SRS document
2. **Merge with task.md**: Add SaaS phases (22-27) to existing task list
3. **Lago Setup**: Confirm Lago Docker container is running
4. **Implementation**: Begin Phase 22 (Lago Client)

---

*Document prepared by ALL 7 PERSONAS in accordance with VIBE Coding Rules v5.1*
