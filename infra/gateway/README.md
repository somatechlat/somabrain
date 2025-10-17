# SomaBrain Gateway Manifests

This directory contains declarative Kong manifests for the SomaBrain v3.0 edge plane. The manifests are designed to be applied with the official `decK` CLI or via GitOps pipelines.

## Files

- `memory-gateway.yaml` — protects the memory data-plane API (`/memory/*`). Enables JWT authentication, per-tenant rate limits, and Prometheus metrics.
- `config-gateway.yaml` — exposes the configuration control-plane (`/memory/config`, `/memory/cutover`) with RBAC enforcement and structured audit logging.
- `values.example.yaml` — sample environment values consumed by the manifests via `{{ env "VAR" }}` templates.

## Usage

1. Export the required environment variables (see `values.example.yaml`).
2. Validate manifests locally:
   ```sh
   deck validate --skip-consumers --state memory-gateway.yaml
   deck validate --skip-consumers --state config-gateway.yaml
   ```
3. Sync to the running Kong cluster:
   ```sh
   deck sync --state memory-gateway.yaml
   deck sync --state config-gateway.yaml
   ```

These manifests intentionally avoid embedding secrets. JWT signing keys and RBAC configuration are referenced via environment variables so they can be managed by the deployment platform.
