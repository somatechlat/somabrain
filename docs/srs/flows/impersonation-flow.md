# Impersonation Flow

**Document Version:** 1.0.0  
**Date:** 2025-12-24  
**Type:** End-to-End Flow Documentation

---

## 1. Overview

God Mode impersonation flows: start, view as tenant, exit, audit logging.

---

## 2. Start Impersonation Flow

```mermaid
flowchart TD
    A[God Mode: View Tenant] --> B[Click 'Impersonate']
    B --> C[Enter Reason for Impersonation]
    C --> D[Confirm Dialog]
    D --> E{Confirm?}
    E -->|No| F[Cancel]
    E -->|Yes| G[POST /api/admin/impersonate/{tenant_id}]
    G --> H[Generate Impersonation Token]
    H --> I[Log Impersonation Start]
    I --> J[Store Original Admin Session]
    J --> K[Switch to Tenant Context]
    K --> L[Show Impersonation Banner]
    L --> M[Redirect to Tenant Dashboard]
```

---

## 3. Impersonation Sequence

```mermaid
sequenceDiagram
    participant Admin as God Mode Admin
    participant UI
    participant API
    participant Auth
    participant Audit
    
    Admin->>UI: Click 'Impersonate Tenant X'
    UI->>API: POST /api/admin/impersonate/{tenant_id}
    API->>Auth: Verify God Mode Role
    Auth-->>API: Authorized
    
    API->>API: Store Original Session
    API->>API: Generate Temp Token
    Note over API: Token has: tenant_id, impersonator_id, expiry
    
    API->>Audit: Log Impersonation Start
    Audit-->>API: OK
    
    API-->>UI: {temp_token, redirect_url}
    
    UI->>UI: Store Original Token
    UI->>UI: Set Impersonation Token
    UI->>UI: Show Warning Banner
    UI->>Admin: Redirect to /dashboard
    
    Note over Admin: Now viewing as Tenant X
```

---

## 4. Impersonation UI Banner

```mermaid
flowchart LR
    A[Yellow Banner] --> B[⚠️ Impersonating: Acme Corp]
    B --> C[Reason: Support Ticket #1234]
    C --> D[Exit Impersonation Button]
```

---

## 5. Exit Impersonation Flow

```mermaid
flowchart TD
    A[Click 'Exit Impersonation'] --> B[POST /api/admin/impersonate/exit]
    B --> C[Invalidate Impersonation Token]
    C --> D[Log Impersonation End]
    D --> E[Calculate Duration]
    E --> F[Restore Original Admin Session]
    F --> G[Remove Impersonation Banner]
    G --> H[Redirect to /platform/tenants]
```

---

## 6. Impersonation State Machine

```mermaid
stateDiagram-v2
    [*] --> GodMode
    GodMode --> Impersonating: Start Impersonation
    Impersonating --> GodMode: Exit Impersonation
    Impersonating --> GodMode: Session Timeout
    Impersonating --> GodMode: Token Expired
```

---

## 7. Audit Trail

| Event | Details Logged |
|-------|----------------|
| `impersonation.start` | admin_id, tenant_id, reason, timestamp |
| `impersonation.action` | action performed while impersonating |
| `impersonation.end` | duration, timestamp |

---

## 8. Security Constraints

| Constraint | Enforcement |
|------------|-------------|
| Reason Required | Cannot start without reason |
| Session Timeout | Max 1 hour impersonation |
| All Actions Logged | Every API call tagged |
| No Billing Changes | Cannot modify subscription |
| No User Deletion | Cannot delete tenant users |

---

*Document prepared by ALL 7 PERSONAS per VIBE Coding Rules v5.1*
