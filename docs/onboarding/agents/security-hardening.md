# Security Hardening Guide

**Purpose**: Understand security controls and best practices in SomaBrain.

## Authentication (Code-Verified)

**Implementation**: `somabrain/auth.py`

### Bearer Token Auth

```python
def require_auth(request: Request, cfg: Config) -> None:
    """Validate Bearer token from Authorization header."""
    # Checks: Authorization: Bearer <token>
    # Validates against cfg.api_token or JWT
```

### Admin Auth

```python
def require_admin_auth(request: Request, cfg: Config) -> None:
    """Require admin-level authentication."""
    # Additional checks for admin endpoints
```

### JWT Support

**Config** (from `somabrain/config.py`):

```python
jwt_secret: Optional[str] = None
jwt_public_key_path: Optional[str] = None
jwt_issuer: Optional[str] = None
jwt_audience: Optional[str] = None
```

**Environment Variables**:
```bash
SOMABRAIN_JWT_SECRET="<secret>"
SOMABRAIN_JWT_PUBLIC_KEY_PATH="/path/to/key.pem"
SOMABRAIN_JWT_ISSUER="somabrain"
SOMABRAIN_JWT_AUDIENCE="api"
```

## Tenant Isolation

**Implementation**: `somabrain/tenant.py`

```python
def get_tenant(request: Request, default_namespace: str) -> TenantContext:
    """Extract tenant ID from X-Tenant-ID header or JWT claims."""
    # Returns: TenantContext(tenant_id, namespace)
```

**Headers**:
```
X-Tenant-ID: sandbox
```

**Isolation Guarantees**:
- Working memory is per-tenant (`mt_wm.recall(tenant_id, ...)`)
- HRR context is per-tenant (`mt_ctx.cleanup(tenant_id, ...)`)
- Adaptation state is per-tenant (Redis keys: `adaptation:state:{tenant_id}`)

## Rate Limiting

**Implementation**: `somabrain/ratelimit.py`

**Config** (from `somabrain/config.py`):

```python
rate_rps: float = 50.0      # Requests per second
rate_burst: int = 100       # Burst capacity
```

**Usage** (from `somabrain/app.py`):

```python
if not rate_limiter.allow(ctx.tenant_id):
    raise HTTPException(status_code=429, detail="rate limit exceeded")
```

## Quotas

**Implementation**: `somabrain/quotas.py`

**Config**:

```python
write_daily_limit: int = 10000  # Max writes per tenant per day
```

**Usage**:

```python
if not quotas.allow_write(ctx.tenant_id, 1):
    raise HTTPException(status_code=429, detail="daily write quota exceeded")
```

## OPA Policy Enforcement

**Service**: `somabrain_opa` (Docker Compose)

**Port**: 30104 (host) → 8181 (container)

**Policies**: `ops/opa/policies/`

**Middleware**: `somabrain/api/middleware/opa.py`

**Health Check**:

```python
opa_ok = opa_client.is_ready()  # Required for readiness
```

## Input Validation

**Implementation**: `somabrain/app.py` (CognitiveInputValidator)

### Text Validation

```python
SAFE_TEXT_PATTERN = re.compile(r"^[a-zA-Z0-9\s\.,!?\'\"()/:_@-]+$")
MAX_TEXT_LENGTH = 10000

def validate_text_input(text: str, field_name: str = "text") -> str:
    """Validate text input for cognitive processing."""
    # Checks: length, safe characters
```

### Coordinate Validation

```python
def validate_coordinates(coords: tuple) -> tuple:
    """Validate coordinate tuples for brain processing."""
    # Checks: exactly 3 floats, reasonable magnitude
```

### Query Sanitization

```python
def sanitize_query(query: str) -> str:
    """Sanitize and prepare query for cognitive processing."""
    # Removes: <>, javascript:, data: patterns
```

## Security Middleware

**Implementation**: `somabrain/app.py` (SecurityMiddleware)

**Blocked Patterns**:

```python
suspicious_patterns = [
    re.compile(r"union\s+select", re.IGNORECASE),  # SQL injection
    re.compile(r";\s*drop", re.IGNORECASE),        # SQL injection
    re.compile(r"<script", re.IGNORECASE),         # XSS
    re.compile(r"eval\s*\(", re.IGNORECASE),       # Code injection
]
```

**Response**: 403 Forbidden

## Docker Security (docker-compose.yml)

### Capability Dropping

```yaml
cap_drop: ["ALL"]  # Drop all Linux capabilities
```

### Read-Only Filesystem

```yaml
read_only: true  # Prevent runtime file modifications
```

### No New Privileges

```yaml
security_opt:
  - no-new-privileges:true  # Prevent privilege escalation
```

### Tmpfs Mounts

```yaml
tmpfs:
  - /app/logs  # Writable logs without persistent storage
  - /tmp       # Temporary files
```

## Secrets Management

### Environment Variables (Development)

```bash
# ✅ CORRECT - Use placeholders in docs
SOMABRAIN_MEMORY_HTTP_TOKEN="<YOUR_TOKEN>"

# ❌ WRONG - Never commit real tokens
SOMABRAIN_MEMORY_HTTP_TOKEN="sk-prod-abc123..."
```

### Production Secrets

**Recommended**: Use external secret managers

- AWS Secrets Manager
- HashiCorp Vault
- Kubernetes Secrets

**Never**:
- Hardcode in source code
- Commit to git
- Log to stdout

## Audit Logging

**Implementation**: `somabrain/audit.py`

**Kafka Topic**: `soma.audit`

**Events Logged**:
- Admin actions (`log_admin_action`)
- Authentication failures
- Policy violations

**Example**:

```python
audit.log_admin_action(request, "neuromodulators_set", {
    "tenant": tenant_id,
    "new_state": {...}
})
```

## Network Security (Docker Compose)

**Internal Network**: `somabrain_net` (bridge)

**Exposed Ports** (host access):
- 9696: API (required)
- 30100-30108: Infrastructure (optional, can be removed in prod)

**Internal-Only Services**:
- Kafka broker: `somabrain_kafka:9092` (not exposed to host by default)
- Redis: `somabrain_redis:6379` (exposed for dev, should be internal in prod)

## Security Checklist

### Before Deployment

- [ ] Rotate all default credentials
- [ ] Enable JWT authentication (`SOMABRAIN_JWT_SECRET`)
- [ ] Configure OPA policies
- [ ] Set rate limits per tenant
- [ ] Enable audit logging to Kafka
- [ ] Review exposed ports
- [ ] Use read-only filesystem
- [ ] Drop all capabilities
- [ ] Enable TLS for external endpoints

### Runtime Monitoring

- [ ] Monitor failed auth attempts
- [ ] Track rate limit violations
- [ ] Alert on circuit breaker opens
- [ ] Review audit logs daily
- [ ] Check OPA policy decisions

## Key Files to Read

1. `somabrain/auth.py` - Authentication logic
2. `somabrain/tenant.py` - Tenant isolation
3. `somabrain/ratelimit.py` - Rate limiting
4. `somabrain/quotas.py` - Quota enforcement
5. `somabrain/app.py` - Input validation, security middleware
6. `ops/opa/policies/` - OPA policy definitions
7. `docker-compose.yml` - Container security settings
