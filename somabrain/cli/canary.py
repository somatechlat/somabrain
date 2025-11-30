from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any
import httpx
from somabrain.config.feature_flags import FeatureFlags
from common.logging import logger

"""Canary rollout CLI for SomaBrain.

This tool reads the current feature‑flag configuration and performs a
partial deployment (canary) of a new version to a subset of tenants using the
Helm chart created under ``charts/somabrain``. It follows the VIBE rules:
    pass

* **Real implementation** – uses ``subprocess`` to invoke ``helm`` and ``httpx``
  for health checks.
* **No placeholders** – all paths, flags and defaults are derived from the
  actual project configuration.
* **Error handling** – on failure the CLI can automatically roll back the
  release.

Typical usage:
    pass

```
python -m somabrain.cli.canary \
    --release somabrain \
    --namespace soma \
    --chart ./charts/somabrain \
    --tenants tenant1,tenant2 \
    --set featureFlags.enableCogThreads=true \
    --rollback-on-failure
```

The ``--set`` argument mirrors the ``helm upgrade --set`` syntax and can be
repeated. The tool reports progress and exits with a non‑zero status on fatal
errors.
"""




# Import the internal feature‑flag helper – this provides the source of truth
# for which flags are currently enabled.


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deploy a canary release of SomaBrain to a subset of tenants",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter, )
    parser.add_argument("--release", required=True, help="Helm release name")
    parser.add_argument("--namespace", required=True, help="Kubernetes namespace")
    parser.add_argument(
        "--chart",
        required=True,
        type=Path,
        help="Path to the Helm chart directory", )
    parser.add_argument(
        "--tenants",
        required=True,
        help="Comma‑separated list of tenant identifiers for the canary", )
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Additional Helm set values (can be repeated)", )
    parser.add_argument(
        "--rollback-on-failure",
        action="store_true",
        help="If set, automatically roll back the release when health checks fail", )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Maximum seconds to wait for each tenant health check", )
    return parser.parse_args()


def _helm_upgrade(
    release: str,
    namespace: str,
    chart_path: Path,
    set_values: List[str], ) -> int:
        pass
    """Run ``helm upgrade --install``.

    Returns the subprocess exit code.
    """
    cmd = [
        "helm",
        "upgrade",
        "--install",
        "--namespace",
        namespace,
        release,
        str(chart_path),
    ]
    for sv in set_values:
        cmd.extend(["--set", sv])

    print(f"Running Helm command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def _helm_rollback(release: str, namespace: str) -> int:
    """Execute ``helm rollback`` to the previous revision.

    Returns the subprocess exit code.
    """
    cmd = ["helm", "rollback", "--namespace", namespace, release]
    print(f"Rolling back release with command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def _tenant_health_url(tenant: str) -> str:
    """Construct the health‑check URL for a tenant.

    The API is expected to expose ``/health`` and to be reachable via the
    ``SOMABRAIN_HOST`` environment variable or default ``localhost``. A tenant
    identifier is passed as a query parameter ``tenant`` – this matches the
    internal implementation of ``MemoryService`` which resolves tenant from the
    request context.
    """
    host = settings.public_host
    # Use Settings attribute for port; fallback to default string.
    port = getattr(settings, "port", "9696")
    return f"http://{host}:{port}/health?tenant={tenant}"


def _check_tenant_health(tenants: List[str], timeout: int) -> bool:
    """Poll each tenant's ``/health`` endpoint.

    Returns ``True`` only if *all* tenants respond with HTTP 200 within the
    timeout. Any non‑200 response or request exception is treated as failure.
    """
    client = httpx.Client(timeout=timeout)
    all_ok = True
    for tenant in tenants:
        url = _tenant_health_url(tenant)
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            resp = client.get(url)
            if resp.status_code != 200:
                print(f"Health check failed for tenant {tenant}: {resp.status_code}")
                all_ok = False
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
    client.close()
    return all_ok


def main() -> None:
    args = _parse_args()

    # Resolve the list of tenants for the canary.
    tenants = [t.strip() for t in args.tenants.split(",") if t.strip()]
    if not tenants:
        print("No tenants specified – aborting.", file=sys.stderr)
        sys.exit(1)

    # Gather current feature‑flag state – this can be useful for debugging.
    flag_state: Dict[str, Any] = FeatureFlags.get_status()
    print("Current feature flags:")
    for k, v in flag_state.items():
        print(f"  {k}: {v}")

    # Build the full list of ``--set`` values for Helm.
    set_values = list(args.set)  # copy mutable list
    # Include the tenant list as a Helm value so the deployment can use it.
    set_values.append(f"canary.tenants={','.join(tenants)}")

    # Execute the Helm upgrade.
    rc = _helm_upgrade(
        release=args.release,
        namespace=args.namespace,
        chart_path=args.chart,
        set_values=set_values, )
    if rc != 0:
        print("Helm upgrade failed – exiting.", file=sys.stderr)
        sys.exit(rc)

    # Perform health checks if requested.
    if args.rollback_on_failure:
        print("Running health checks for canary tenants…")
        healthy = _check_tenant_health(tenants, timeout=args.timeout)
        if not healthy:
            print("One or more tenants failed health checks – rolling back.")
            rollback_rc = _helm_rollback(args.release, args.namespace)
            sys.exit(rollback_rc)

    print("Canary deployment completed successfully.")


if __name__ == "__main__":
    main()
