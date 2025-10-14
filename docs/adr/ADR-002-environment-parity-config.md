# ADR-002: Enforce Environment Parity via Cached Configuration and Locked Dependencies

- **Status:** Accepted (Sprint A0)
- **Deciders:** Architecture Guild, Platform Engineering, Observability
- **Date:** 2025-10-13

## Context

SomaBrain previously allowed configuration files and dependency resolution to drift between developer workstations, CI, and production images. Multiple modules loaded YAML configuration directly, bypassing overrides and caching, while dependency installation depended on `pip` resolving transitive packages at runtime. This produced inconsistent behavior, increased cold-start latency, and obscured regressions.

## Decision

1. Adopt `somabrain.config.get_config()` as the single entry point for all configuration access. The helper caches data on first read and honors environment overrides and reload triggers.
2. Treat `uv.lock` as the canonical dependency manifest. All environments (local, CI, production) install via `uv pip sync uv.lock` to guarantee deterministic versions.
3. Record the duration of dependency installation in CI and export the metric (`dependency_install_duration_seconds`) for observability dashboards.

## Consequences

- **Positive**
  - Eliminates repeated YAML parsing and divergent configuration state.
  - Ensures all environments resolve identical packages, reducing "works on my machine" discrepancies.
  - Provides objective timing data to track dependency drift and performance.
- **Negative**
  - Requires developers to install `uv` 0.8+ and use it for lock maintenance.
  - Initial metric capture adds a minor overhead (~1–2 seconds) to CI as the timing wrapper runs.

## Implementation Plan

1. Migrate all modules to `somabrain.config.get_config()` and expose `reload_config()` for administrative overrides (complete).
2. Update `DEVELOPMENT_GUIDE.md` and `docs/DEVELOPMENT_SETUP.md` with the `uv` bootstrap workflow (complete).
3. Add `scripts/ci/record_dependency_install_metrics.py` and call it from CI to emit JSON metrics under `artifacts/bench_logs/` (complete).
4. Import `observability/dependency_install_panel.json` into Grafana to visualize install duration trends (planned for Sprint A1).

## Alternatives Considered

- **Keep ad-hoc YAML loads:** rejected; retains duplication and stale caches.
- **Use `pip-tools` without `uv`:** rejected; `uv` provides faster sync and a single tool for installs and execution.
- **Measure install time via shell `time`:** rejected; hard to capture structured metrics for dashboards.

## Follow-up Tasks

- Add CI alerting when `dependency_install_duration_seconds` exceeds 120s.
- Evaluate pruning unused dependencies (`psycopg2-binary`, `requests`) once migration plans are complete.
- Expand metrics to capture cache hit rate for `get_config()` at runtime (observability backlog).
