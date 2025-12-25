# Tenant Creation Complete Flow

**Document Version:** 1.0.0  
**Date:** 2025-12-24  
**Type:** End-to-End Flow Documentation

---

## 1. Overview

This document describes the **complete flow** for creating tenants in the SomaBrain SaaS platform, covering:
- God Mode Admin creating tenants
- Self-signup tenant registration
- Backend processing and integrations

---

## 2. Tenant Creation Methods

```mermaid
flowchart TB
    subgraph Methods["Two Paths to Create Tenant"]
        A[God Mode Admin] -->|Manual| B[Admin Dashboard]
        C[End User] -->|Self-Service| D[Public Signup]
    end
    
    B --> E[Tenant Created]
    D --> E
```

---

## 3. God Mode Admin: Create Tenant Flow

### 3.1 Complete UI Flow

```mermaid
flowchart TD
    A[Admin Navigates to /platform] --> B[Login via Keycloak SSO]
    B --> C{Authenticated?}
    C -->|No| D[Redirect to Login]
    D --> B
    C -->|Yes| E[Load Platform Dashboard]
    
    E --> F[Click 'Tenants' in Sidebar]
    F --> G[View All Tenants Table]
    G --> H[Click '+ Create Tenant' Button]
    
    H --> I[Modal Opens: Tenant Creation Form]
    
    subgraph Form["Tenant Creation Form"]
        I --> J[Step 1: Basic Info]
        J --> K["Organization Name (required)"]
        K --> L["Billing Email (required)"]
        L --> M["Contact Person (optional)"]
        
        M --> N[Step 2: Subscription]
        N --> O[Select Tier: Free/Starter/Pro/Enterprise]
        O --> P["Trial Days (0-30)"]
        P --> Q[Enable Auto-Billing?]
        
        Q --> R[Step 3: Configuration]
        R --> S[Custom Quota Limits?]
        S --> T[Mark as Exempt?]
        T --> U[Exempt Reason if Yes]
        
        U --> V[Step 4: Admin User]
        V --> W["Admin Email (required)"]
        W --> X["Admin Name (optional)"]
    end
    
    X --> Y[Click 'Create Tenant']
    Y --> Z{Form Valid?}
    Z -->|No| AA[Show Validation Errors]
    AA --> I
    Z -->|Yes| AB[Submit to API]
```

### 3.2 Backend Processing Sequence

```mermaid
sequenceDiagram
    participant Admin as God Mode Admin
    participant UI as SaaS UI (5173)
    participant API as SomaBrain API (9696)
    participant TM as TenantManager
    participant TR as TenantRegistry
    participant Redis
    participant Lago as Lago Billing
    participant KC as Keycloak
    participant Email as Email Service
    
    Admin->>UI: Click 'Create Tenant'
    UI->>UI: Validate Form
    UI->>API: POST /api/v1/admin/tenants
    
    Note over API: Authenticate Admin Token
    API->>API: Verify God Mode Role
    
    API->>TM: create_tenant(display_name, tier, ...)
    TM->>TM: Validate tier permissions
    TM->>TM: Generate tenant_id (UUID)
    
    TM->>TR: register_tenant(metadata)
    TR->>TR: Validate ID format
    TR->>Redis: SET tenant:{id} {metadata}
    Redis-->>TR: OK
    TR->>TR: Update caches
    TR->>Redis: LPUSH audit:tenant:{date} {event}
    TR-->>TM: tenant_id
    
    Note over API: Billing Integration
    API->>Lago: POST /api/v1/customers
    Note over Lago: external_id = tenant_id
    Lago-->>API: customer_id
    
    API->>Lago: POST /api/v1/subscriptions
    Note over Lago: plan_code = tier_slug
    Lago-->>API: subscription_id
    
    Note over API: Create Admin User
    API->>KC: POST /admin/realms/.../users
    KC-->>API: user_id
    
    API->>KC: POST /admin/.../users/{id}/role-mappings
    Note over KC: Assign tenant_admin role
    
    Note over API: Notifications
    API->>Email: Send Welcome Email
    Email-->>API: OK
    
    API-->>UI: 201 Created {tenant}
    UI->>UI: Show Success Toast
    UI->>UI: Redirect to Tenant Detail
```

### 3.3 UI State Diagram

```mermaid
stateDiagram-v2
    [*] --> TenantList: Navigate to /platform/tenants
    
    TenantList --> FormOpen: Click 'Create'
    FormOpen --> Step1_BasicInfo: Form Opens
    
    Step1_BasicInfo --> Step2_Subscription: Next
    Step2_Subscription --> Step3_Config: Next
    Step3_Config --> Step4_AdminUser: Next
    
    Step4_AdminUser --> Validating: Submit
    
    Validating --> ValidationError: Invalid
    ValidationError --> Step1_BasicInfo: Fix Errors
    
    Validating --> Processing: Valid
    Processing --> Success: API Success
    Processing --> APIError: API Error
    
    APIError --> FormOpen: Retry
    Success --> TenantDetail: Redirect
    
    TenantDetail --> [*]: Complete
```

---

## 4. Self-Service Signup Flow

### 4.1 Public Registration Flow

```mermaid
flowchart TD
    A[User Visits /signup] --> B[View Pricing Page]
    B --> C{Select Plan}
    
    C -->|Free| D[Basic Signup Form]
    C -->|Starter/Pro| E[Full Signup + Payment]
    C -->|Enterprise| F[Contact Sales Form]
    
    subgraph FreeSignup["Free Tier Signup"]
        D --> G[Enter Email]
        G --> H[Enter Password]
        H --> I[Enter Organization Name]
        I --> J[Agree to Terms]
        J --> K[Click 'Create Account']
    end
    
    subgraph PaidSignup["Paid Tier Signup"]
        E --> L[Organization Info]
        L --> M[Admin User Info]
        M --> N[Redirect to Lago Checkout]
        N --> O[Enter Payment Details]
        O --> P{Payment Valid?}
        P -->|No| Q[Show Error, Retry]
        Q --> O
        P -->|Yes| R[Return to App]
    end
    
    K --> S[Create Tenant + User]
    R --> S
    S --> T[Send Verification Email]
    T --> U[User Clicks Verification Link]
    U --> V[Account Activated]
    V --> W[Redirect to /dashboard]
```

### 4.2 Self-Signup Backend Sequence

```mermaid
sequenceDiagram
    participant User
    participant UI as Signup UI
    participant API as SomaBrain API
    participant TM as TenantManager
    participant Lago
    participant KC as Keycloak
    participant Email
    
    User->>UI: Fill Signup Form
    UI->>API: POST /api/v1/auth/signup
    
    Note over API: Validate Input
    API->>API: Check email not exists
    
    API->>TM: create_tenant(display_name, tier=FREE)
    TM-->>API: tenant_id
    
    API->>KC: Create User Account
    KC-->>API: user_id
    
    API->>Lago: Create Customer
    Lago-->>API: customer_id
    
    alt Paid Plan
        API->>Lago: Create Subscription
        Lago-->>API: checkout_url
        API-->>UI: {redirect: checkout_url}
        UI->>Lago: Redirect to Checkout
        User->>Lago: Enter Payment
        Lago->>API: Webhook: payment.success
        API->>TM: Activate Tenant
    else Free Plan
        API->>TM: Activate Tenant (no payment)
    end
    
    API->>Email: Send Verification Email
    API-->>UI: 201 Created
    UI->>UI: Show "Check Email" Message
    
    User->>Email: Click Verification Link
    Email->>API: GET /api/v1/auth/verify?token=xxx
    API->>KC: Verify User
    API-->>User: Redirect to /dashboard
```

---

## 5. Tenant Data Model

```mermaid
erDiagram
    TENANT {
        uuid tenant_id PK
        string display_name
        string billing_email
        string contact_person
        enum tier
        enum status
        datetime created_at
        datetime expires_at
        boolean is_exempt
        string exempt_reason
        json config
    }
    
    TENANT_USER {
        uuid user_id PK
        uuid tenant_id FK
        string email
        string name
        enum role
        datetime created_at
    }
    
    TENANT_SUBSCRIPTION {
        int id PK
        uuid tenant_id FK
        string tier_id FK
        string lago_subscription_id
        string lago_customer_id
        enum status
        datetime started_at
        datetime trial_ends_at
    }
    
    AUDIT_LOG {
        uuid event_id PK
        uuid tenant_id FK
        string action
        string actor_id
        json details
        datetime timestamp
    }
    
    TENANT ||--o{ TENANT_USER : has
    TENANT ||--|| TENANT_SUBSCRIPTION : has
    TENANT ||--o{ AUDIT_LOG : generates
```

---

## 6. Post-Creation Checklist

```mermaid
flowchart LR
    A[Tenant Created] --> B{Checklist}
    
    B --> C[✓ TenantMetadata in Redis]
    B --> D[✓ Customer in Lago]
    B --> E[✓ Subscription in Lago]
    B --> F[✓ Admin User in Keycloak]
    B --> G[✓ Welcome Email Sent]
    B --> H[✓ Audit Log Entry]
    
    C --> I[Tenant Ready]
    D --> I
    E --> I
    F --> I
    G --> I
    H --> I
```

---

## 7. Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `409 Conflict` | Tenant name already exists | Change organization name |
| `400 Bad Request` | Invalid email format | Fix email address |
| `402 Payment Required` | Payment failed (paid tier) | Update payment method |
| `503 Service Unavailable` | Lago/Keycloak down | Retry later, check health |

---

## 8. Related Documents

- [SRS-01: Multi-Tenancy](./01-multi-tenancy.md) - Tenant architecture details
- [SRS-02: Subscription & Billing](./02-subscription-billing.md) - Lago integration
- [SRS-03: Authentication & SSO](./03-authentication-sso.md) - Keycloak/OAuth setup
- [SRS-04: God Mode Admin](./04-god-mode-admin.md) - Admin dashboard

---

*Document prepared by ALL 7 PERSONAS per VIBE Coding Rules v5.1*
