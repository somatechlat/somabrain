> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

Stub & Fallback Audit
======================

This document enumerates locations in the codebase that implement fallbacks,
in-process mirrors, or stub behaviour. It assigns a priority and recommended
fix/action so the team can eliminate silent fallbacks and enforce strict‑real
behaviour (`SOMABRAIN_STRICT_REAL=1`).

How to read this document
-------------------------
- File: path to file
- Context: short excerpt / description of fallback
- Severity: High | Medium | Low
- Recommendation: concrete change to remove stub or make strict (code/infra)

> Note: local in-process mirrors can now be disabled globally by setting
> `SOMABRAIN_ALLOW_LOCAL_MIRRORS=0` (propagated through `common.config.settings`).
> Strict-real mode (`SOMABRAIN_STRICT_REAL=1`) continues to raise via
> `stub_audit.record_stub` regardless of this flag.

1) `somabrain/memory_client.py`
--------------------------------
Context:
- Still writes to `_GLOBAL_PAYLOADS/_GLOBAL_LINKS` for mirrors (guarded with `record_stub`). HTTP fallback paths now honour shared strict-real settings instead of direct env checks.
Severity: Medium
Recommendation:
- Mirrors are now gated by `SOMABRAIN_ALLOW_LOCAL_MIRRORS` (default `1`). Set it to `0` in staging/prod or strict integration runs to disable mirrors entirely.

2) `somabrain/services/memory_service.py`
-----------------------------------------
Context:
- Service still uses MemoryClient mirrors; strict-real already guarded.
Severity: Medium
Recommendation:
- Acceptable until mirror removal project; ensure tests seed data via fixtures.

3) `somabrain/services/rag_pipeline.py`
---------------------------------------
Context:
- The RAG pipeline falls back to in-process mirroring and stub retrievers when real adapters are not available. Some code intentionally appends to `_GLOBAL_PAYLOADS` for visibility.
Severity: High
Recommendation:
- Convert fallback stubs to raise `RuntimeError` or `StubUsageError` under strict-real. Provide a developer mode that explicitly allows these mirrors only when `SOMABRAIN_STRICT_REAL_BYPASS` is set.

4) `tests/conftest.py`
----------------------
Context:
- The test harness uses `_GLOBAL_PAYLOADS` and fixture-controlled mirrors for tests. There are environment variables that control auto-starting local servers and the memory stub.
Severity: Medium
Recommendation:
- Keep test mirrors and fixtures but document clearly how to run tests under strict-real (disable test autostart and start real infra). Add test markers to separate strict vs dev tests.

5) `somabrain/opa/client.py` and `api/middleware/opa.py`
-----------------------------------------------------
Context:
- OPA client falls back to `allow` on RPC errors (safe default) to avoid blocking traffic.
Severity: Medium
Recommendation:
- In strict-real integration runs, fail closed (deny) or mark policy failures as test failures depending on the scenario. Add a runtime config `OPA_FALLBACK_ALLOW` to control this behaviour.

6) Misc fallbacks and resilience code (lower priority)
----------------------------------------------------
- Observability: `observability/provider.py` falls back to console export.
- Storage: `storage/db.py` supports SQLite fallback for dev.
- Audit: `audit/producer.py` uses JSONL fallback if Kafka unreachable.
Severity: Low/Medium
Recommendation:
- Keep these fallbacks for developer convenience, but ensure CI strict-real tests either disable fallbacks or run with real infra. Document which fallbacks are dev-only.

Next steps (actionable)
-----------------------
1. Create a CI job `integration-kind` that runs full integration tests with `SOMABRAIN_STRICT_REAL=1`. Fail the job if `record_stub` is invoked (the `stub_audit` module will raise in strict-real).
2. Open PRs for the high-severity files (`memory_client.py`, `memory_service.py`, `rag_pipeline.py`) converting mirror writes to either explicit errors or guarded by dev flags. Use the audit file to guide changes.
3. Update tests so they do not rely on runtime mirror writes; instead use fixture seeding (existing `tests/conftest.py` already supports this pattern).
4. Document strict-real developer workflow in `docs/ROAMACP_CANONICAL.md` and `README.md` (how to run tests with `DISABLE_START_SERVER=1` and how to bring up dev infra via `scripts/start_dev_infra.sh`).

Audit generated: automated grep run (high-confidence); follow-up manual review recommended for code paths that intentionally use mirrors for performance or replication reasons.
