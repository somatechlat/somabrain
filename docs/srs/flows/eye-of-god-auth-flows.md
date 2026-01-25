# Eye of God - Authentication User Journeys & Screen Designs

**Document Version:** 1.0.0  
**Date:** 2025-12-24  
**Status:** DESIGN PHASE  
**Standard:** ISO/IEC/IEEE 29148:2018 Compatible

---

## 1. User Journeys

### 1.1 UJ-AUTH-001: First-Time Platform Admin Login

| Priority | **P0 - CRITICAL** |
|----------|-------------------|
| Actor | Platform Super Admin |
| Goal | Access Eye of God dashboard for first time |

**Journey Steps:**

```mermaid
journey
    title First-Time Platform Admin Login
    section Discovery
      Navigate to Eye of God URL: 5: Admin
      See login screen: 5: Admin
    section Authentication
      Click "Login with Google": 5: Admin
      Redirect to Google OAuth: 3: System
      Enter Google credentials: 5: Admin
      Consent to permissions: 4: Admin
    section Onboarding
      Redirect back to Eye of God: 3: System
      System creates admin user: 3: System
      See welcome dashboard: 5: Admin
```

**Acceptance Criteria:**
- [ ] Login page loads in <2s
- [ ] Google OAuth redirect works
- [ ] User created in database on first login
- [ ] JWT token stored securely (httpOnly cookie)
- [ ] Dashboard displays tenant list

---

### 1.2 UJ-AUTH-002: Returning Admin Login

| Priority | **P0 - CRITICAL** |
|----------|-------------------|
| Actor | Existing Platform Admin |
| Goal | Quick re-authentication |

**Journey Steps:**

```mermaid
journey
    title Returning Admin Login
    section Quick Access
      Navigate to Eye of God: 5: Admin
      Token valid: 3: System
      Auto-redirect to dashboard: 5: Admin
    section Token Expired
      Navigate to Eye of God: 5: Admin
      Token expired: 3: System
      Redirect to login: 3: Admin
      One-click Google login: 5: Admin
      Dashboard displayed: 5: Admin
```

---

### 1.3 UJ-AUTH-003: Tenant Admin Login

| Priority | **P1 - HIGH** |
|----------|---------------|
| Actor | Tenant Administrator |
| Goal | Access tenant-specific admin panel |

**Journey Steps:**

```mermaid
journey
    title Tenant Admin Login
    section Authentication
      Navigate to tenant portal: 5: TenantAdmin
      Click "Login with Google": 5: TenantAdmin
      Complete Google OAuth: 4: TenantAdmin
    section Authorization
      System checks tenant_id claim: 3: System
      System verifies tenant-admin role: 3: System
      Redirect to tenant dashboard: 5: TenantAdmin
    section Access
      View own tenant usage: 5: TenantAdmin
      Manage tenant users: 5: TenantAdmin
      Access denied to other tenants: 3: System
```

---

### 1.4 UJ-AUTH-004: Logout Flow

| Priority | **P1 - HIGH** |
|----------|---------------|
| Actor | Any authenticated user |
| Goal | Securely end session |

```mermaid
journey
    title Secure Logout
    section User Action
      Click logout button: 5: User
    section System Actions
      Clear local tokens: 3: System
      Revoke session in Keycloak: 3: System
      Redirect to login page: 3: System
    section Confirmation
      See logged out message: 5: User
      Cannot access protected routes: 3: System
```

---

## 2. Process Flow Charts

### 2.1 Authentication Flow (OAuth2/PKCE)

```mermaid
flowchart TD
    A[User visits Eye of God] --> B{Has valid token?}
    B -->|Yes| C[Show Dashboard]
    B -->|No| D[Show Login Screen]
    D --> E[User clicks 'Login with Google']
    E --> F[Generate PKCE code_verifier]
    F --> G[Redirect to Keycloak /auth]
    G --> H[Keycloak shows Google IDP]
    H --> I[User authenticates with Google]
    I --> J[Google returns to Keycloak]
    J --> K[Keycloak returns auth_code]
    K --> L[Eye of God exchanges code for tokens]
    L --> M[Store tokens in httpOnly cookie]
    M --> C
```

### 2.2 API Request Authorization Flow

```mermaid
flowchart TD
    A[API Request with Bearer Token] --> B[Django Middleware]
    B --> C{Token present?}
    C -->|No| D[401 Unauthorized]
    C -->|Yes| E[Validate JWT signature]
    E --> F{Signature valid?}
    F -->|No| D
    F -->|Yes| G[Check token expiry]
    G --> H{Expired?}
    H -->|Yes| D
    H -->|No| I[Extract claims]
    I --> J[Attach user + tenant to request]
    J --> K[Proceed to endpoint]
    K --> L{Has required role?}
    L -->|No| M[403 Forbidden]
    L -->|Yes| N[Execute endpoint logic]
```

### 2.3 Token Refresh Flow

```mermaid
flowchart TD
    A[Access token expires] --> B[Eye of God detects 401]
    B --> C{Has refresh token?}
    C -->|No| D[Redirect to login]
    C -->|Yes| E[Call Keycloak /token with refresh_token]
    E --> F{Refresh successful?}
    F -->|No| D
    F -->|Yes| G[Update stored tokens]
    G --> H[Retry original request]
```

---

## 3. UML Diagrams

### 3.1 Class Diagram - Authentication Components

```mermaid
classDiagram
    class KeycloakConfig {
        +String realm
        +String clientId
        +String issuerUrl
        +String jwksUri
        +getOpenIdConfig()
    }
    
    class JWTValidator {
        -KeycloakConfig config
        -JWKS cachedKeys
        +validate(token): Claims
        +refreshJWKS()
    }
    
    class AuthMiddleware {
        -JWTValidator validator
        +process_request(request)
        +extract_token(request): String
    }
    
    class User {
        +UUID id
        +String email
        +String name
        +UUID tenant_id
        +List~String~ roles
    }
    
    class Claims {
        +String sub
        +String email
        +String tenant_id
        +List~String~ roles
        +int exp
    }
    
    KeycloakConfig --> JWTValidator
    JWTValidator --> AuthMiddleware
    AuthMiddleware --> User
    JWTValidator --> Claims
```

### 3.2 Sequence Diagram - Login Flow

```mermaid
sequenceDiagram
    participant U as User Browser
    participant E as Eye of God UI
    participant K as Keycloak
    participant G as Google
    participant A as SomaBrain API
    
    U->>E: Navigate to /login
    E->>E: Generate PKCE verifier
    E->>K: Redirect to /auth (with code_challenge)
    K->>G: Redirect to Google OAuth
    G->>U: Show Google login
    U->>G: Enter credentials
    G->>K: Return with auth code
    K->>E: Redirect with auth_code
    E->>K: POST /token (code + code_verifier)
    K->>E: Return access_token + refresh_token
    E->>E: Store tokens (httpOnly cookie)
    E->>A: GET /api/health (Bearer token)
    A->>A: Validate JWT
    A->>E: 200 OK
    E->>U: Show Dashboard
```

---

## 4. Screen Designs

### 4.1 SCR-AUTH-001: Login Screen

| Priority | **P0 - CRITICAL** |
|----------|-------------------|

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                    ╔═══════════════════╗                    │
│                    ║   👁️ EYE OF GOD   ║                    │
│                    ║   AAAS Admin      ║                    │
│                    ╚═══════════════════╝                    │
│                                                             │
│              ┌─────────────────────────────┐                │
│              │                             │                │
│              │   Welcome to the Platform   │                │
│              │   Admin Control Center      │                │
│              │                             │                │
│              │  ┌─────────────────────┐    │                │
│              │  │  🔵 Login with      │    │                │
│              │  │     Google          │    │                │
│              │  └─────────────────────┘    │                │
│              │                             │                │
│              │  ────── or ──────           │                │
│              │                             │                │
│              │  ┌─────────────────────┐    │                │
│              │  │  🔑 Login with      │    │                │
│              │  │     Keycloak        │    │                │
│              │  └─────────────────────┘    │                │
│              │                             │                │
│              └─────────────────────────────┘                │
│                                                             │
│              © 2025 SomaBrain Platform                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Elements:**
| Element | Type | Action |
|---------|------|--------|
| Logo | Image | Brand identity |
| Login with Google | Button | Redirect to Keycloak→Google |
| Login with Keycloak | Button | Direct Keycloak login |
| Footer | Text | Copyright |

---

### 4.2 SCR-AUTH-002: Dashboard (Post-Login)

| Priority | **P0 - CRITICAL** |
|----------|-------------------|

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ ┌─────────┐                                    ┌─────────┐  │
│ │👁️ EoG   │  Dashboard                         │ 👤 Admin│  │
│ └─────────┘                                    └─────────┘  │
├──────────────┬──────────────────────────────────────────────┤
│              │                                              │
│  📊 Overview │  Welcome, {user.name}                        │
│              │                                              │
│  🏢 Tenants  │  ┌────────────┐ ┌────────────┐ ┌──────────┐  │
│              │  │ 45         │ │ 12         │ │ $12,450  │  │
│  👥 Users    │  │ Tenants    │ │ Active     │ │ MRR      │  │
│              │  └────────────┘ └────────────┘ └──────────┘  │
│  💰 Billing  │                                              │
│              │  Recent Activity                             │
│  📈 Usage    │  ┌─────────────────────────────────────────┐ │
│              │  │ • Tenant "Acme" upgraded to Pro         │ │
│  ⚙️ Settings │  │ • New user joined "TechCorp"            │ │
│              │  │ • Invoice #1234 paid                    │ │
│  🔐 Auth     │  └─────────────────────────────────────────┘ │
│              │                                              │
└──────────────┴──────────────────────────────────────────────┘
```

---

### 4.3 SCR-AUTH-003: User Profile/Logout

| Priority | **P1 - HIGH** |
|----------|---------------|

**Layout:**
```
┌─────────────────────────────────┐
│  👤 Admin User                  │
│  admin@example.com              │
├─────────────────────────────────┤
│  Role: super-admin              │
│  Tenant: Platform               │
├─────────────────────────────────┤
│  ⚙️ Account Settings            │
│  🔑 Security                    │
│  🚪 Logout                      │
└─────────────────────────────────┘
```

---

## 5. Priority Matrix

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| Create Keycloak realm | P0 | Low | None |
| Google IDP setup | P0 | Medium | Realm |
| Eye of God client | P0 | Low | Realm |
| Login screen UI | P0 | Medium | Client |
| JWT middleware | P0 | Medium | Realm |
| Dashboard UI | P0 | High | Login |
| Token refresh | P1 | Medium | Login |
| Logout flow | P1 | Low | Login |
| Role-based access | P1 | Medium | JWT middleware |
| User profile screen | P2 | Low | Dashboard |

---

## 6. Implementation Order

1. **Sprint 1: Foundation** (P0)
   - Create `somabrain` realm
   - Configure Google IDP
   - Create clients

2. **Sprint 2: Backend** (P0)
   - Implement JWT validation middleware
   - Create auth endpoints

3. **Sprint 3: Frontend** (P0)
   - Login screen
   - PKCE auth flow
   - Dashboard skeleton

4. **Sprint 4: Polish** (P1-P2)
   - Token refresh
   - Logout flow
   - User profile
   - Role-based UI

---

*VIBE Coding Rules: ALL 10 PERSONAS applied*
