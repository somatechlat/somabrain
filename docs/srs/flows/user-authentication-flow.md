# User Authentication Flow

**Document Version:** 1.0.0  
**Date:** 2025-12-24  
**Type:** End-to-End Flow Documentation

---

## 1. Overview

Complete authentication flows for SomaBrain AAAS platform: login, logout, SSO, password reset.

---

## 2. Login Methods

```mermaid
flowchart TB
    A[User Visits /login] --> B{Choose Method}
    B -->|Email/Password| C[Local Auth]
    B -->|Google| D[OAuth via Keycloak]
    B -->|Enterprise SSO| E[Keycloak SSO]
```

---

## 3. Email/Password Login Flow

```mermaid
flowchart TD
    A[Enter Email] --> B[Enter Password]
    B --> C[Click 'Sign In']
    C --> D[POST /api/auth/login]
    D --> E{Credentials Valid?}
    E -->|No| F[Show Error]
    F --> A
    E -->|Yes| G[Generate JWT]
    G --> H[Store in Session]
    H --> I[Redirect to /dashboard]
```

---

## 4. Google OAuth Sequence

```mermaid
sequenceDiagram
    participant User
    participant UI
    participant KC as Keycloak
    participant Google
    participant API
    
    User->>UI: Click "Sign in with Google"
    UI->>KC: /auth?kc_idp_hint=google
    KC->>Google: OAuth Request
    Google->>User: Consent Screen
    User->>Google: Approve
    Google->>KC: Auth Code
    KC->>Google: Exchange for Tokens
    KC->>UI: Callback with Code
    UI->>KC: Exchange for KC Tokens
    KC-->>UI: Access + Refresh Token
    UI->>API: GET /api/me
    API-->>UI: User Profile
    UI->>User: Redirect to Dashboard
```

---

## 5. Logout Flow

```mermaid
flowchart TD
    A[User Clicks 'Logout'] --> B[Clear Local Session]
    B --> C[POST /api/auth/logout]
    C --> D[Invalidate Server Session]
    D --> E[Redirect to Keycloak Logout]
    E --> F[Clear Keycloak Session]
    F --> G[Redirect to /login]
```

---

## 6. Password Reset Flow

```mermaid
flowchart TD
    A[Click 'Forgot Password'] --> B[Enter Email]
    B --> C[POST /api/auth/password-reset]
    C --> D[Generate Reset Token]
    D --> E[Send Email with Link]
    E --> F[User Clicks Link]
    F --> G[Verify Token]
    G --> H{Token Valid?}
    H -->|No| I[Show Expiry Error]
    H -->|Yes| J[Enter New Password]
    J --> K[POST /api/auth/password-reset/confirm]
    K --> L[Update Password in Keycloak]
    L --> M[Redirect to Login]
```

---

## 7. Session State Machine

```mermaid
stateDiagram-v2
    [*] --> Unauthenticated
    Unauthenticated --> Authenticating: Login Attempt
    Authenticating --> Authenticated: Success
    Authenticating --> Unauthenticated: Failure
    Authenticated --> Unauthenticated: Logout
    Authenticated --> Authenticated: Token Refresh
    Authenticated --> SessionExpired: Token Expired
    SessionExpired --> Authenticating: Re-login
    SessionExpired --> Unauthenticated: Timeout
```

---

## 8. Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `401 Unauthorized` | Invalid credentials | Re-enter password |
| `403 Forbidden` | Account disabled | Contact admin |
| `429 Too Many Requests` | Rate limit | Wait and retry |

---

*Document prepared by ALL 7 PERSONAS per VIBE Coding Rules v5.1*
