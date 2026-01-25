# SRS-01: Multi-Tenancy Module

**Document Version:** 1.0.0  
**Date:** 2025-12-24  
**Standard:** ISO/IEC/IEEE 29148:2018 Compatible  
**Module:** Multi-Tenancy Subsystem

---

## 1. Overview

The Multi-Tenancy module provides complete tenant isolation, lifecycle management, and quota enforcement for the SomaBrain AAAS platform.

### 1.1 Scope

| Component | Description |
|-----------|-------------|
| TenantRegistry | UUID-based tenant storage in Redis |
| TenantManager | High-level tenant operations |
| TenantContext | Request-scoped tenant resolution |
| QuotaManager | Per-tenant write quotas |

---

## 2. UML Class Diagram

```mermaid
classDiagram
    class TenantContext {
        +str tenant_id
        +str namespace
    }
    
    class TenantManager {
        -TenantRegistry registry
        -str _default_tenant_id
        -Dict _system_tenant_ids
        -bool _initialized
        +initialize()
        +resolve_tenant_from_request(request) str
        +create_tenant(display_name, tier, ...) str
        +suspend_tenant(tenant_id, reason) bool
        +activate_tenant(tenant_id) bool
        +delete_tenant(tenant_id) bool
        +list_tenants(tier, status) List
        +get_tenant_metadata(tenant_id) TenantMetadata
        +is_exempt_tenant(tenant_id) bool
        +cleanup_expired_tenants() int
    }
    
    class TenantRegistry {
        -str redis_url
        -Redis _redis
        -Dict _tenant_cache
        -Set _exempt_cache
        -Dict _system_tenant_ids
        +initialize()
        +register_tenant(...) str
        +get_tenant(tenant_id) TenantMetadata
        +tenant_exists(tenant_id) bool
        +is_exempt(tenant_id) bool
        +update_tenant_status(tenant_id, status) bool
        +delete_tenant(tenant_id) bool
        +update_tenant_activity(tenant_id)
        +get_all_tenants(tier) List
        +get_tenant_stats() Dict
        +cleanup_expired_tenants() int
    }
    
    class TenantMetadata {
        +str tenant_id
        +str display_name
        +datetime created_at
        +TenantStatus status
        +TenantTier tier
        +Dict config
        +bool is_exempt
        +str exempt_reason
        +datetime last_activity
        +str created_by
        +datetime expires_at
        +to_dict() Dict
        +from_dict(data) TenantMetadata
    }
    
    class TenantTier {
        <<enumeration>>
        SYSTEM
        ENTERPRISE
        PUBLIC
        SANDBOX
    }
    
    class TenantStatus {
        <<enumeration>>
        ACTIVE
        SUSPENDED
        DISABLED
    }
    
    class QuotaManager {
        -QuotaConfig cfg
        -Dict _counts
        -TenantManager _tenant_manager
        +allow_write(tenant_id, n) bool
        +remaining(tenant_id) int
        +get_quota_info(tenant_id) QuotaInfo
        +reset_quota(tenant_id) bool
    }
    
    TenantManager --> TenantRegistry : uses
    TenantManager --> TenantMetadata : returns
    TenantRegistry --> TenantMetadata : stores
    TenantMetadata --> TenantTier : has
    TenantMetadata --> TenantStatus : has
    QuotaManager --> TenantManager : queries
    TenantContext ..> TenantManager : resolved by
```

---

## 3. Tenant Lifecycle Flowchart

```mermaid
flowchart TD
    subgraph Creation["Tenant Creation"]
        A[Admin/System Request] --> B{Tenant ID Provided?}
        B -->|No| C[Generate UUID-based ID]
        B -->|Yes| D[Validate ID Format]
        C --> E[Create TenantMetadata]
        D --> E
        E --> F[Store in Redis]
        F --> G[Update Caches]
        G --> H[Audit Log Entry]
        H --> I[Tenant ACTIVE]
    end
    
    subgraph Operations["Tenant Operations"]
        I --> J{Operation Type}
        J -->|Suspend| K[Set Status SUSPENDED]
        J -->|Reactivate| L[Set Status ACTIVE]
        J -->|Disable| M[Set Status DISABLED]
        J -->|Delete| N{Is System Tenant?}
        N -->|Yes| O[Reject: Cannot Delete System]
        N -->|No| P[Remove from Redis]
        P --> Q[Clear Caches]
        Q --> R[Audit Log]
        R --> S[Tenant Deleted]
    end
    
    subgraph Expiration["Automatic Cleanup"]
        T[Scheduled Job] --> U[Get All Tenants]
        U --> V{Expires At < Now?}
        V -->|Yes| W{Is System Tenant?}
        W -->|No| X[Delete Tenant]
        W -->|Yes| Y[Skip]
        V -->|No| Y
    end
```

---

## 4. Tenant Resolution Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant API as Django/Ninja API
    participant TM as TenantManager
    participant TR as TenantRegistry
    participant Redis
    
    Client->>API: HTTP Request (X-Tenant-ID header)
    API->>TM: resolve_tenant_from_request(request)
    
    alt Has X-Tenant-ID Header
        TM->>TR: tenant_exists(header_tenant_id)
        TR->>Redis: GET tenant:{id}
        Redis-->>TR: Tenant data
        TR-->>TM: True
        TM->>TR: update_tenant_activity(tenant_id)
        TR->>Redis: SET tenant:{id} (updated)
        TM-->>API: tenant_id
    else Has Bearer Token
        TM->>TM: _hash_token(token)
        TM->>TR: tenant_exists(token_hash)
        TR-->>TM: Result
        alt Token-based Tenant Exists
            TM-->>API: token_hash_tenant_id
        else No Token Tenant
            TM->>TM: Use Default Tenant
        end
    else No Credentials
        alt Anonymous Allowed
            TM->>TM: create_temporary_tenant()
            TM->>TR: register_tenant(temp)
            TR->>Redis: SET tenant:{temp_id} EX {ttl}
            TM-->>API: temp_tenant_id
        else Anonymous Disabled
            TM-->>API: HTTP 401 Error
        end
    end
    
    API-->>Client: Response with Tenant Context
```

---

## 5. Tenant Onboarding Flow (God Mode)

```mermaid
flowchart TD
    A[God Mode Admin] --> B[Login via Keycloak]
    B --> C[Navigate to /platform/tenants]
    C --> D[Click 'Create Tenant']
    D --> E[Enter Tenant Details Form]
    
    subgraph Form["Tenant Creation Form"]
        E --> F[Display Name]
        F --> G[Select Tier: Free/Starter/Pro/Enterprise]
        G --> H[Configure Quota Limits]
        H --> I[Set Expiration if temporary]
        I --> J[Mark as Exempt? Why?]
    end
    
    J --> K[POST /api/v1/admin/tenants]
    K --> L[TenantManager.create_tenant]
    L --> M[TenantRegistry.register_tenant]
    M --> N[Store in Redis]
    N --> O[Sync to Lago as Customer]
    O --> P[Create Initial Admin User]
    P --> Q[Send Welcome Email]
    Q --> R[Tenant ACTIVE ✓]
```

---

## 6. Functional Requirements

| REQ-ID | Requirement | Priority | Status | Source |
|--------|-------------|----------|--------|--------|
| REQ-MT-001 | All data MUST be isolated by `tenant_id` | CRITICAL | ✅ EXISTS | `models.py` - all models have tenant_id |
| REQ-MT-002 | Tenant CRUD via Admin API | HIGH | ✅ EXISTS | `tenant_manager.py` lines 156-241 |
| REQ-MT-003 | Tenant metadata (name, contact, billing_email) | HIGH | ⚠️ PARTIAL | `TenantMetadata` lacks billing_email |
| REQ-MT-004 | Tenant suspension/activation capability | HIGH | ✅ EXISTS | `suspend_tenant()`, `activate_tenant()` |
| REQ-MT-005 | Tenant soft-delete with data retention policy | MEDIUM | ⚠️ PARTIAL | Hard delete exists, soft-delete missing |
| REQ-MT-006 | UUID-based tenant ID generation | HIGH | ✅ EXISTS | `_generate_dynamic_tenant_id()` |
| REQ-MT-007 | Tenant expiration and auto-cleanup | MEDIUM | ✅ EXISTS | `cleanup_expired_tenants()` |
| REQ-MT-008 | System tenant exemption from quotas | HIGH | ✅ EXISTS | `is_exempt()` method |
| REQ-MT-009 | Tenant activity tracking | MEDIUM | ✅ EXISTS | `update_tenant_activity()` |
| REQ-MT-010 | Audit logging for all tenant operations | HIGH | ✅ EXISTS | `_audit_log()` in registry |

---

## 7. System Tenant Configuration

```mermaid
flowchart LR
    subgraph SystemTenants["Pre-configured System Tenants"]
        A[agent_zero_xxx]
        B[public_xxx]
        C[sandbox_xxx]
    end
    
    A -->|SYSTEM tier| D[Exempt from Quotas]
    A -->|Unlimited Access| E[Internal Operations]
    
    B -->|PUBLIC tier| F[Default Fallback]
    B -->|Standard Quotas| G[Anonymous Users]
    
    C -->|SANDBOX tier| H[Development Mode]
    C -->|Relaxed Limits| I[Testing/Dev]
```

---

## 8. Non-Functional Requirements

| NFR-ID | Requirement | Target | Implementation |
|--------|-------------|--------|----------------|
| NFR-MT-001 | Tenant resolution < 5ms | Latency | Redis cache lookup |
| NFR-MT-002 | Support 10,000+ concurrent tenants | Scalability | Redis + in-memory cache |
| NFR-MT-003 | Tenant data isolation at DB level | Security | All queries filtered by tenant_id |
| NFR-MT-004 | Audit log retention 7 years | Compliance | Redis LTRIM to 1000 entries/day |

---

## 9. Key Files Reference

| File | Purpose | Lines |
|------|---------|-------|
| [tenant.py](file:///Users/macbookpro201916i964gb1tb/Documents/GitHub/somabrain/somabrain/tenant.py) | TenantContext helper | 51 |
| [tenant_manager.py](file:///Users/macbookpro201916i964gb1tb/Documents/GitHub/somabrain/somabrain/tenant_manager.py) | High-level tenant operations | 408 |
| [tenant_registry.py](file:///Users/macbookpro201916i964gb1tb/Documents/GitHub/somabrain/somabrain/tenant_registry.py) | Redis-backed tenant storage | 500 |
| [tenant_types.py](file:///Users/macbookpro201916i964gb1tb/Documents/GitHub/somabrain/somabrain/tenant_types.py) | TenantTier, TenantStatus, TenantMetadata | ~60 |
| [tenant_validation.py](file:///Users/macbookpro201916i964gb1tb/Documents/GitHub/somabrain/somabrain/tenant_validation.py) | ID validation and normalization | ~100 |

---

*Document prepared by ALL 7 PERSONAS: 🎓 PhD Developer, 🔍 PhD Analyst, ✅ PhD QA, 📚 ISO Documenter, 🔒 Security Auditor, ⚡ Performance Engineer, 🎨 UX Consultant + Django Architect/Expert/Evangelist*
