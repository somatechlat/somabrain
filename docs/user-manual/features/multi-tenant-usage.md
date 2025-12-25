# Multi-Tenant Usage

**Purpose** Explain how SomaBrain separates tenants, applies quotas, and scopes namespaces.

**Audience** Operators and developers running a single SomaBrain instance for multiple teams or customers.

**Prerequisites** The core API is running and you have at least one tenant credential.

---

## 1. How Tenants Are Identified

`somabrain.tenant.get_tenant` determines the tenant for every request using the following priority:

1. `X-Tenant-ID` header (explicit).
2. The first 16 characters of the bearer token (implicit).
3. Fallback `"public"` tenant when neither is available.

The namespace stored in Redis, Prometheus labels, and response bodies is constructed as `<base_namespace>:<tenant_id>`, where `base_namespace` defaults to `somabrain_ns` (see `.env`).

```bash
curl -sS http://localhost:9696/health \
  -H "Authorization: Bearer dev-token" \
  -H "X-Tenant-ID: org_acme" | jq '.namespace'
```

Output:

```json
"somabrain_ns:org_acme"
```

---

## 2. Isolation Guarantees

| Layer | Mechanism | Notes |
|-------|-----------|-------|
| Working memory | `MultiTenantWM` maintains a per-tenant dictionary keyed by tenant ID. | Redis is optional; the in-process buffer respects namespace separation. |
| Long-term memory | HTTP memory service receives the tenant namespace (client libraries should propagate it). | Configure your backend to honour the namespace; the SomaBrain API does not multiplex responses. |
| Adaptation state | Redis keys prefixed with `adaptation:state:{tenant}`. | Retrieval/utility weights never mix between tenants. |
| Metrics | Prometheus metrics expose `tenant_id` labels (e.g., `somabrain_tau_gauge{tenant_id="org_acme"}`). | Use label filters to derive per-tenant dashboards. |
| Logs | Structured logs include `tenant` and `namespace` fields. | Filter centrally to audit tenant-specific activity. |

---

## 3. Quotas and Rate Limiting

- **Rate limiting** (`somabrain.ratelimit.RateLimiter`): simple leaky bucket enforced per tenant. Violation returns HTTP 429 with `{"detail": "rate limit exceeded"}` and increments the `somabrain_rate_limited_total` metric.
- **Daily write quota** (`somabrain.quotas.QuotaManager`): defaults to 10 000 writes per tenant per day. Configure via `SOMABRAIN_QUOTA_DAILY_WRITES` or by extending `QuotaConfig` in `somabrain.config.Config`. Tenants containing `AGENT_ZERO` are exempt by design.

Check remaining quota programmatically:

```python
from somabrain.quotas import QuotaManager, QuotaConfig

manager = QuotaManager(QuotaConfig(daily_writes=5000))
remaining = manager.remaining("org_acme")
```

In the API, quota enforcement occurs in `somabrain.app.remember` before writes reach the memory service.

---

## 4. Tenant Headers in Practice

Always include `X-Tenant-ID` when running shared environments:

```bash
AUTH="Authorization: Bearer ${SOMABRAIN_API_TOKEN}"
TENANT="X-Tenant-ID: org_acme"

curl -sS http://localhost:9696/remember \
  -H "Content-Type: application/json" \
  -H "$AUTH" -H "$TENANT" \
  -d '{"payload": {"task": "org_acme.memo", "content": "Tenant-specific note."}}'
```

If you omit the header, the request falls back to the token hash or `"public"`. Treat `"public"` as an unscoped sandbox tenant.

---

## 5. Tenant-Specific Configuration

SomaBrain does not ship a tenant registry in this repository. If you need per-tenant limits or feature flags:

1. Extend `common/config/settings.py` (if present in your deployment) to expose tenant metadata.
2. Inject tenant-specific settings via environment variables or a wrapper service before requests hit the API.
3. Use namespaces (e.g., `somabrain_ns:customer_a`) to map tenants to dedicated resources in external systems (memory service, dashboards, storage).

Remember that quota and rate-limiter state is in-memory on each API instance. In horizontally scaled environments back these managers with Redis or another shared store so every replica enforces the same counters.

---

## 6. Observability

Monitor per-tenant health with the following metrics:

| Metric | Description | Example |
|--------|-------------|---------|
| `somabrain_tau_gauge{tenant_id=…}` | Current τ value after duplicate-rate adjustments. | `curl -s http://localhost:9696/metrics \| rg tau_gauge` |
| `somabrain_feedback_total{tenant_id=…}` | Feedback events per tenant. | Track adaptation load. |
| `somabrain_ltm_store_total{tenant_id=…}` | Long-term store attempts per tenant. | Observe ingestion patterns. |
| `somabrain_rate_limited_total{tenant_id=…}` | Count of blocked writes due to rate limiting. | Investigate noisy tenants. |

Use these signals to validate isolation and catch runaway tenants early.

---

## 7. Best Practices

- Reserve uppercase or special marker tenants (e.g., `"AGENT_ZERO"`) for automated agents that need unlimited access.
- Enforce authentication even in dev environments when multiple tenants share the same deployment.
- Surface tenant context in your client logs—matching `trace_id` + `tenant_id` vastly simplifies debugging.
- When decommissioning a tenant, purge or archive associated data in the external memory service; SomaBrain itself does not delete tenant namespaces automatically.
