# SomaBrain Standalone Mode Architecture Audit

Original file date: 2026-02-03  
Manual refresh: 2026-04-01  
Scope refreshed in this pass: standalone settings, Vault bootstrap, runtime
startup comments, and the current standalone Docker stack.

---

## Executive Summary

The earlier version of this document overstated certainty. After re-reading the
current code and compose manifests, the more accurate verdict is:

- Standalone mode is intentionally single-tenant at runtime.
- Standalone compose is now Vault-first, not plain-env-only.
- The compose stack has grown beyond the previously documented 16 services.
- Documentation drift existed and has been corrected in the nearby deployment
  guide and docs index.
- The runtime still depends on an external memory endpoint by default.

This is a useful standalone profile, but it is not accurately described by the
older “zero violations found / 100% compliant” framing.

---

## 1. Settings and bootstrap path

Relevant files:

- `somabrain/settings/django_core.py`
- `somabrain/settings/infra.py`
- `somabrain/settings/standalone.py`
- `somabrain/core/security/vault_client.py`

Current behavior:

1. `django_core.py` loads the shared Django settings and performs an early Vault
   bootstrap when Vault coordinates are present.
2. `infra.py` resolves connection settings after that bootstrap and applies
   Docker-aware defaults when explicit env vars are missing.
3. `standalone.py` imports the shared settings, removes AAAS apps/middleware,
   and forces the tenant identity to `standalone`.

Important nuance:

- Standalone is Vault-first in the compose deployment, but the Python settings
  still deliberately fall back to plain environment variables when Vault is not
  configured. That fallback is necessary for CI and local non-Vault workflows.

---

## 2. Standalone isolation

The current isolation model is runtime isolation, not repository-wide deletion.

What the code does:

- Removes `somabrain.aaas` from `INSTALLED_APPS`
- Filters AAAS middleware from `MIDDLEWARE`
- Forces `SOMABRAIN_DEFAULT_TENANT` and `SOMABRAIN_TENANT_ID` to `standalone`

What it does not do:

- Remove AAAS code from the repository
- Prevent shared modules from importing code that exists outside standalone
- Eliminate every multi-tenant concept from the codebase

So the precise claim should be: standalone strips AAAS behavior from the active
runtime configuration, but the repo remains a mixed-mode codebase.

---

## 3. Compose architecture as of 2026-04-01

Relevant file:

- `infra/standalone/docker-compose.yml`

The compose file currently defines 19 services:

1. `somabrain_standalone_redis`
2. `somabrain_standalone_kafka`
3. `somabrain_standalone_kafka_exporter`
4. `somabrain_standalone_schema_registry`
5. `somabrain_standalone_opa`
6. `somabrain_standalone_prometheus`
7. `somabrain_standalone_jaeger`
8. `somabrain_standalone_postgres`
9. `somabrain_standalone_vault`
10. `somabrain_standalone_vault_init`
11. `somabrain_standalone_db_migrate` (optional `dev` profile)
12. `somabrain_standalone_postgres_exporter`
13. `somabrain_standalone_app`
14. `somabrain_standalone_cog`
15. `somabrain_standalone_outbox_publisher`
16. `somabrain_standalone_etcd`
17. `somabrain_standalone_minio`
18. `somabrain_standalone_milvus`
19. `somabrain_standalone_integrator_triplet`

Notable operational facts:

- Vault now sits on host port `30200`
- Kafka exposes its external listener on host port `30102`
- Milvus depends on the bundled etcd and MinIO services
- The app and worker containers use Vault bootstrap variables rather than raw
  DSNs for their primary secrets
- The memory service is still external by default and resolves to
  `http://host.docker.internal:10101`

---

## 4. Documentation drift corrected in this pass

Stale claims found in the older documentation included:

- “16 services” for the standalone compose stack
- plain-environment quick-start instructions that ignored the Vault bootstrap
- docs index references to many files that do not exist in `docs/`

Updated alongside this audit:

- `infra/standalone/DEPLOYMENT_GUIDE.md`
- `docs/README.md`

---

## 5. Remaining audit limits

This refresh was grounded in the currently changed standalone/runtime/settings
surface area. It did not re-validate every historical quantitative claim in the
older report, including counts such as “145 brain parameters” or broad claims
like “zero code duplication across modules.”

Those statements should be treated as unverified unless re-audited directly
against the current codebase.
