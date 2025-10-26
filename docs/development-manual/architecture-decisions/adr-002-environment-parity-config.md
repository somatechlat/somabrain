# ADR-002: Enforce Environment Parity via Cached Configuration and Locked Dependencies

- **Status**: Accepted (Sprint A0)
- **Deciders**: Architecture Guild, Platform Engineering, Observability
- **Date**: 2025-10-13

## Context

SomaBrain previously allowed configuration files and dependency resolution to drift between developer workstations, CI, and production images. Multiple modules loaded YAML configuration directly, bypassing overrides and caching, while dependency installation depended on `pip` resolving transitive packages at runtime. This produced inconsistent behaviour, increased cold-start latency, and obscured regressions.

## Decision

1. Adopt `somabrain.config.get_config()` as the single entry point for all configuration access. The helper caches data on first read and honours environment overrides and reload triggers.
2. Treat `uv.lock` as the canonical dependency manifest. All environments (local, CI, production) install via `uv pip sync uv.lock` to guarantee deterministic versions.
3. Record the duration of dependency installation in CI and export the metric (`dependency_install_duration_seconds`) for observability dashboards.

## Consequences

- **Positive**
  - Eliminates repeated YAML parsing and divergent configuration state.
  - Ensures all environments resolve identical packages, reducing "works on my machine" incidents.
  - Provides objective timing data to track dependency drift and performance.
- **Negative**
  - Requires developers to install `uv` 0.8+ and use it for lock maintenance.
  - Initial metric capture adds ~1–2 seconds to CI as the timing wrapper runs.

## Implementation Plan

1. Migrate all modules to `somabrain.config.get_config()` and expose `reload_config()` for administrative overrides (complete).
2. Update development documentation with the `uv` bootstrap workflow (complete).
3. Add `scripts/ci/record_dependency_install_metrics.py` and call it from CI to emit JSON metrics under `artifacts/bench_logs/` (complete).
4. Visualise install duration trends via Prometheus queries (no external dashboards).

## Alternatives Considered

- Ad-hoc YAML loads – rejected; retains duplication and stale caches.
- `pip-tools` without `uv` – rejected; `uv` provides faster sync and a single tool for installs and execution.
- Shell `time` metrics – rejected; structured metrics are required for dashboards.

## Follow-up Tasks

- Add CI alerting when `dependency_install_duration_seconds` exceeds 120 seconds.
- Evaluate pruning unused dependencies (`psycopg2-binary`, `requests`) once migration plans are complete.
- Expand metrics to capture runtime cache hit rate for `get_config()` (observability backlog).
