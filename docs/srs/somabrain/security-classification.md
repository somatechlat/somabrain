# Document Security Classification

This document defines security classifications for SomaBrain documentation according to ISO/IEC 27001 requirements.

## Classification Levels

| Level | Description | Handling | Examples |
|-------|-------------|----------|----------|
| **PUBLIC** | Information that can be shared openly | No restrictions | API documentation, architecture diagrams, user guides |
| **INTERNAL** | Operational details for team use | Keep in public repo with `<!-- INTERNAL -->` markers | Internal deployment configs, development workflows |
| **CONFIDENTIAL** | Sensitive information | Store in private repo only; use placeholders in public docs | Production credentials, vulnerability details, customer data |

## Current Document Classifications

### PUBLIC Documents

- All files in `docs/user/`
- All files in `docs/technical/` (except security/)
- All files in `docs/development/`
- All files in `docs/onboarding/`
- `README.md`
- `ROADMAP_*.md`

### INTERNAL Documents

- `docs/technical/security/` (operational security procedures)
- `docs/operations/` (deployment checklists, runbooks)

### CONFIDENTIAL Documents

**None in public repository**

All confidential information uses placeholders:
- `<MEMORY_SERVICE_TOKEN>` instead of actual tokens
- `<POSTGRES_PASSWORD>` instead of real passwords
- `<JWT_SECRET>` instead of production secrets

## Credential Handling

### In Documentation

**NEVER include:**
- Real API tokens
- Production passwords
- Private keys
- Customer data
- Internal IP addresses (use `<INTERNAL_IP>` placeholder)

**ALWAYS use:**
- `<YOUR_TOKEN_HERE>` placeholders for all token examples
- `<TOKEN>` placeholders for production documentation
- `localhost` or `127.0.0.1` for local examples
- `somabrain_*` service names for Docker Compose examples

### In Code Examples

```bash
# ✅ CORRECT - Uses placeholder
export SOMABRAIN_MEMORY_HTTP_TOKEN="<YOUR_TOKEN_HERE>"

# ❌ WRONG - Real token
export SOMABRAIN_MEMORY_HTTP_TOKEN="sk-prod-abc123..."
```

## Verification

All documentation commits are scanned for:
- Hardcoded credentials (regex patterns)
- Private IP addresses
- Internal hostnames
- Customer-specific information

## Incident Response

If confidential information is accidentally committed:

1. **Immediately** rotate the exposed credential
2. Remove from git history using `git filter-branch` or BFG Repo-Cleaner
3. Document incident in security log
4. Notify affected parties

## Last Updated

2025-01-XX
