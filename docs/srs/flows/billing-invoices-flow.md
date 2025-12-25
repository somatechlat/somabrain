# Billing & Invoices Flow

**Document Version:** 1.0.0  
**Date:** 2025-12-24  
**Type:** End-to-End Flow Documentation

---

## 1. Overview

Complete billing flows: view invoices, download PDFs, update payment, view usage.

---

## 2. View Invoices Flow

```mermaid
flowchart TD
    A[Navigate to /settings/billing] --> B[API: GET /api/billing/invoices]
    B --> C[Fetch from Lago]
    C --> D[Display Invoice List]
    D --> E[Select Invoice]
    E --> F[Show Invoice Detail]
    F --> G{Actions}
    G -->|Download| H[GET PDF URL from Lago]
    G -->|Pay Now| I[Pay Outstanding Invoice]
```

---

## 3. Invoice List Sequence

```mermaid
sequenceDiagram
    participant User
    participant UI
    participant API
    participant Lago
    
    User->>UI: Navigate to Billing
    UI->>API: GET /api/billing/invoices
    API->>Lago: List Invoices (customer_id)
    Lago-->>API: Invoice List
    API-->>UI: Formatted Invoices
    UI->>User: Display Invoice Table
    
    User->>UI: Click 'Download PDF'
    UI->>API: GET /api/billing/invoices/{id}/pdf
    API->>Lago: Get PDF URL
    Lago-->>API: pdf_url
    API-->>UI: Redirect URL
    UI->>User: Download PDF
```

---

## 4. View Usage Dashboard Flow

```mermaid
flowchart TD
    A[Navigate to /settings/usage] --> B[API: GET /api/billing/usage]
    B --> C[Aggregate TokenLedger Data]
    C --> D[Fetch Lago Usage]
    D --> E[Display Usage Dashboard]
    E --> F[API Calls Chart]
    E --> G[Memory Ops Chart]
    E --> H[Embeddings Chart]
    E --> I[Quota Remaining Bar]
```

---

## 5. Update Payment Method Flow

```mermaid
flowchart TD
    A[Click 'Update Payment'] --> B[API: GET /api/billing/portal]
    B --> C[Generate Lago Portal Session]
    C --> D[Open Lago Checkout Portal]
    D --> E[User Updates Card]
    E --> F[Lago Validates Card]
    F --> G{Valid?}
    G -->|No| H[Show Error]
    H --> E
    G -->|Yes| I[Save Payment Method]
    I --> J[Webhook: payment_method.updated]
    J --> K[Redirect Back to App]
    K --> L[Show Success ✓]
```

---

## 6. Usage Tracking State Machine

```mermaid
stateDiagram-v2
    [*] --> BelowQuota
    BelowQuota --> NearQuota: Usage > 80%
    NearQuota --> AtQuota: Usage = 100%
    AtQuota --> Throttled: Request Blocked
    Throttled --> BelowQuota: New Period
    NearQuota --> BelowQuota: New Period
    AtQuota --> BelowQuota: New Period
```

---

## 7. Invoice Status

| Status | Description | Action |
|--------|-------------|--------|
| `draft` | Not yet finalized | View only |
| `finalized` | Ready for payment | Pay now |
| `paid` | Payment received | Download receipt |
| `voided` | Cancelled | N/A |
| `failed` | Payment failed | Update payment |

---

*Document prepared by ALL 7 PERSONAS per VIBE Coding Rules v5.1*
