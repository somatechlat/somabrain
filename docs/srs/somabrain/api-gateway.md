# SRS-06: API Gateway & Rate Limiting

**Document Version:** 1.0.0  
**Date:** 2025-12-24  
**Standard:** ISO/IEC/IEEE 29148:2018 Compatible  
**Module:** API Gateway Subsystem

---

## 1. Overview

The API Gateway module manages request processing, per-tenant rate limiting, quota enforcement, and request routing for the SomaBrain AAAS platform.

### 1.1 Scope

| Component | Description |
|-----------|-------------|
| QuotaManager | Daily write quotas per tenant |
| RateLimiter | Request rate limiting |
| API Router | Django Ninja endpoint routing |
| Middleware | Auth, tenant, quota middleware |

---

## 2. Request Processing Pipeline

```mermaid
flowchart TD
    A[HTTP Request] --> B[Django WSGI/ASGI]
    B --> C[Auth Middleware]
    
    C -->|No Token| D{Auth Required?}
    D -->|Yes| E[HTTP 401]
    D -->|No| F[Continue]
    
    C -->|Valid Token| G[Tenant Middleware]
    G --> H[Resolve Tenant ID]
    H --> I{Tenant Valid?}
    I -->|No| J[HTTP 401/403]
    I -->|Yes| K[Quota Middleware]
    
    K --> L{Allow Write?}
    L -->|No| M[HTTP 429 Too Many Requests]
    L -->|Yes| N[Rate Limit Check]
    
    N --> O{Under Rate Limit?}
    O -->|No| M
    O -->|Yes| P[Django Ninja Router]
    
    P --> Q[Endpoint Handler]
    Q --> R[Business Logic]
    R --> S[Response]
    S --> T[Add Rate Limit Headers]
    T --> U[HTTP Response]
```

---

## 3. Rate Limit Enforcement Sequence

```mermaid
sequenceDiagram
    participant Client
    participant Gateway as API Gateway
    participant Quota as QuotaManager
    participant TM as TenantManager
    participant Handler as Endpoint
    
    Client->>Gateway: POST /api/memory/store
    Gateway->>Gateway: Extract Bearer Token
    Gateway->>TM: resolve_tenant_from_request()
    TM-->>Gateway: tenant_id
    
    Gateway->>TM: is_exempt_tenant(tenant_id)?
    TM-->>Gateway: true/false
    
    alt Tenant is Exempt
        Gateway->>Handler: Process Request
    else Tenant has Quotas
        Gateway->>Quota: allow_write(tenant_id, 1)
        
        alt Quota Exhausted
            Quota-->>Gateway: false
            Gateway-->>Client: 429 Too Many Requests
            Note over Client: X-RateLimit-Remaining: 0
        else Quota Available
            Quota-->>Gateway: true
            Gateway->>Handler: Process Request
            Handler-->>Gateway: Response
            Gateway->>Quota: remaining(tenant_id)
            Quota-->>Gateway: N
            Gateway-->>Client: 200 OK
            Note over Client: X-RateLimit-Remaining: N
        end
    end
```

---

## 4. UML Component Diagram

```mermaid
classDiagram
    class QuotaConfig {
        +int daily_writes
        +__post_init__()
    }
    
    class QuotaManager {
        -QuotaConfig cfg
        -Dict _counts
        -TenantManager _tenant_manager
        +allow_write(tenant_id, n) bool
        +remaining(tenant_id) int
        +get_quota_info(tenant_id) QuotaInfo
        +reset_quota(tenant_id) bool
        +adjust_quota_limit(tenant_id, new_limit) bool
        +get_all_quotas() List
    }
    
    class QuotaInfo {
        +str tenant_id
        +int daily_limit
        +int remaining
        +int used_today
        +datetime reset_at
        +bool is_exempt
    }
    
    class RateLimiter {
        +check_rate(tenant_id) bool
        +get_headers(tenant_id) Dict
    }
    
    class NinjaAPI {
        +add_router(prefix, router)
        +exception_handler()
    }
    
    QuotaManager --> QuotaConfig : uses
    QuotaManager --> QuotaInfo : returns
    QuotaManager --> TenantManager : queries
    NinjaAPI --> QuotaManager : enforces
    NinjaAPI --> RateLimiter : enforces
```

---

## 5. Quota Reset Flow

```mermaid
flowchart TD
    subgraph DayStart["Day Boundary (UTC Midnight)"]
        A[Day Key Changes] --> B[New Day Key Calculated]
        B --> C[Check Each Request]
    end
    
    subgraph RequestCheck["Request Processing"]
        C --> D{Current Day Key == Stored Day Key?}
        D -->|No| E[Reset Count to 0]
        E --> F[Update Day Key]
        D -->|Yes| G[Use Existing Count]
        F --> G
        G --> H{count + n > limit?}
        H -->|Yes| I[Reject: 429]
        H -->|No| J[Increment Count]
        J --> K[Allow Request]
    end
```

---

## 6. Functional Requirements

| REQ-ID | Requirement | Priority | Status | Implementation |
|--------|-------------|----------|--------|----------------|
| REQ-QUOTA-001 | Per-tenant rate limits from tier | CRITICAL | ⚠️ PARTIAL | `quotas.py` exists |
| REQ-QUOTA-002 | HTTP 429 response when limit exceeded | HIGH | ⚠️ PARTIAL | Needs middleware |
| REQ-QUOTA-003 | Rate limit headers (X-RateLimit-*) | MEDIUM | ❌ MISSING | To be added |
| REQ-QUOTA-004 | Quota reset on billing cycle | HIGH | ✅ EXISTS | Day key reset |
| REQ-QUOTA-005 | Burst allowance configuration | LOW | ❌ MISSING | Future feature |
| REQ-QUOTA-006 | Exempt tenants bypass quotas | HIGH | ✅ EXISTS | `_is_exempt()` |
| REQ-QUOTA-007 | Tenant-specific quota overrides | MEDIUM | ⚠️ PARTIAL | Via config |

---

## 7. Rate Limit Headers

| Header | Description | Example |
|--------|-------------|---------|
| `X-RateLimit-Limit` | Daily limit for tenant | `10000` |
| `X-RateLimit-Remaining` | Remaining requests today | `9823` |
| `X-RateLimit-Reset` | Unix timestamp of reset | `1703462400` |
| `Retry-After` | Seconds until reset (on 429) | `3600` |

---

## 8. Key Files

| File | Purpose | Lines |
|------|---------|-------|
| [quotas.py](file:///Users/macbookpro201916i964gb1tb/Documents/GitHub/somabrain/somabrain/quotas.py) | Quota management | 246 |
| [ratelimit.py](file:///Users/macbookpro201916i964gb1tb/Documents/GitHub/somabrain/somabrain/ratelimit.py) | Rate limiting | ~60 |
| [api/](file:///Users/macbookpro201916i964gb1tb/Documents/GitHub/somabrain/somabrain/api/) | API endpoints (31 files) | ~5000 |

---

*Document prepared by ALL 7 PERSONAS + Django Architect/Expert/Evangelist*
