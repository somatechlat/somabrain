import logging
import os
from typing import Any, Dict

import requests

LOGGER = logging.getLogger("somabrain.opa")


class OPAClient:
    """Simple OPA HTTP client.

    Reads the OPA endpoint from the ``SOMA_OPA_URL`` environment variable.
    The ``evaluate`` method sends a POST request to ``/v1/data/<policy_path>``
    with a JSON ``input`` payload and expects a ``result`` containing an ``allow``
    boolean. If OPA is unreachable or returns an error, the client falls back to
    ``True`` (allow) and logs the incident – this mirrors the current development
    stance where OPA enforcement is optional.
    """

    def __init__(self, policy_path: str = "somabrain/auth/allow") -> None:
        self.base_url = os.getenv("SOMA_OPA_URL", "http://localhost:8181")
        self.policy_path = policy_path.rstrip("/")
        self.session = requests.Session()
        # Optional: configure timeouts globally
        self.timeout = float(os.getenv("SOMA_OPA_TIMEOUT", "2"))
        LOGGER.debug(
            "OPA client initialized: %s (policy %s)", self.base_url, self.policy_path
        )

    def evaluate(self, input_data: Dict[str, Any]) -> bool:
        """Evaluate the OPA policy with the given ``input_data``.

        Returns ``True`` if the policy permits the request, ``False`` otherwise.
        Any transport or server error results in a safe ``True`` (allow) fallback.
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
            # In testing or when OPA is unavailable, default to allow (fail‑open).
            LOGGER.warning("OPA evaluation failed (fallback allow): %s", e)
            return True

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
