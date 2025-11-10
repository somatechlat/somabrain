import logging
import os
from typing import Any, Dict

import requests

from somabrain.infrastructure import get_opa_url

LOGGER = logging.getLogger("somabrain.opa")

try:
    from common.config.settings import settings as shared_settings
except Exception:  # pragma: no cover - optional dependency in legacy layouts
    shared_settings = None  # type: ignore


def _policy_path_for_mode() -> str:
    """Resolve OPA data path based on centralized mode bundle.

    - dev mode -> somabrain/auth/allow_dev
    - staging/prod -> somabrain/auth/allow
    """
    bundle = None
    if shared_settings is not None:
        try:
            bundle = str(getattr(shared_settings, "mode_opa_policy_bundle", "") or "")
        except Exception:
            bundle = None
    bundle = (bundle or "").strip().lower()
    if bundle == "allow-dev" or bundle == "dev":
        return "somabrain/auth/allow_dev"
    return "somabrain/auth/allow"


class OPAClient:
    """Strict OPA HTTP client (fail-closed by default).

    POSTs ``/v1/data/<policy_path>`` with JSON ``input`` and expects a ``result``
    containing an ``allow`` boolean. Transport or server errors deny by default.
    A permissive allow-on-error fallback is only enabled if environment variable
    ``SOMABRAIN_OPA_ALLOW_ON_ERROR=1`` is explicitly set (temporary escape hatch).
    """

    def __init__(self, policy_path: str | None = None) -> None:
        if shared_settings is not None:
            try:
                self.timeout = float(
                    getattr(shared_settings, "opa_timeout_seconds", 2.0) or 2.0
                )
            except Exception:
                self.timeout = 2.0
            # Policy path is derived from mode bundle when not explicitly provided
        else:
            self.timeout = float(os.getenv("SOMA_OPA_TIMEOUT", "2"))

        self.base_url = get_opa_url()
        if not self.base_url:
            # Legacy fallback for dev shells without explicit configuration.
            # Prefer explicit host port envs, defaulting to 30004 to align
            # with dev stack mapping.
            host_port = os.getenv("OPA_HOST_PORT") or os.getenv("OPA_PORT") or "30004"
            self.base_url = (
                os.getenv("SOMA_OPA_URL")
                or os.getenv("SOMABRAIN_OPA_FALLBACK")
                or f"http://127.0.0.1:{host_port}"
            )
        effective_path = (policy_path or _policy_path_for_mode()).rstrip("/")
        self.policy_path = effective_path
        self.session = requests.Session()
        LOGGER.debug(
            "OPA client initialized: %s (policy %s)", self.base_url, self.policy_path
        )

    def evaluate(self, input_data: Dict[str, Any]) -> bool:
        """Evaluate policy with ``input_data``.

        Returns True if allowed, False otherwise. Failure denies unless
        explicit override ``SOMABRAIN_OPA_ALLOW_ON_ERROR=1`` present.
        """
        url = f"{self.base_url}/v1/data/{self.policy_path}"
        payload = {"input": input_data}
        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            # Expected shape: {"result": {"allow": true}}
            result = data.get("result", {})
            if isinstance(result, dict):
                return bool(result.get("allow", True))
            # If OPA returns a primitive (e.g., true/false), interpret directly
            return bool(result)
        except Exception as e:
            allow_override = os.getenv("SOMABRAIN_OPA_ALLOW_ON_ERROR") == "1"
            if allow_override:
                LOGGER.warning("OPA evaluation failed (override allow): %s", e)
                return True
            LOGGER.error("OPA evaluation failed (deny): %s", e)
            return False

    def is_ready(self) -> bool:
        """Check OPA readiness via its /health endpoint.

        Returns True if OPA responds with HTTP 200 within the configured timeout.
        """
        health_url = f"{self.base_url}/health"
        try:
            resp = self.session.get(health_url, timeout=self.timeout)
            return resp.status_code == 200
        except Exception:
            return False

    def reload_policy(self) -> bool:
        """Trigger OPA to reload its policies.

        OPA provides an admin endpoint ``/-/reload`` that forces the policy
        bundle to be re-read. This method posts to that endpoint and returns
        ``True`` on a 200 response, ``False`` otherwise.
        """
        reload_url = f"{self.base_url}/-/reload"
        try:
            resp = self.session.post(reload_url, timeout=self.timeout)
            resp.raise_for_status()
            return True
        except Exception as e:
            LOGGER.warning("OPA reload failed: %s", e)
            return False


# Export a singleton for easy import elsewhere if desired
opa_client = OPAClient()

__all__ = ["OPAClient", "opa_client"]
