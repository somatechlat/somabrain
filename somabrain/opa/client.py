import logging
from typing import Any, Dict
import requests
from somabrain.infrastructure import get_opa_url
from common.logging import logger
from common.config.settings import settings



LOGGER = logging.getLogger("somabrain.opa")

try:
    pass
except Exception as exc:
    logger.exception("Exception caught: %s", exc)
    raise
    settings = None  # type: ignore


def _policy_path_for_mode() -> str:
    """Resolve OPA data path based on centralized mode bundle.

    - dev mode -> somabrain/auth/allow_dev
    - staging/prod -> somabrain/auth/allow
    """
    bundle = None
    if settings is not None:
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            bundle = str(getattr(settings, "mode_opa_policy_bundle", "") or "")
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            bundle = None
    bundle = (bundle or "").strip().lower()
    if bundle == "allow-dev" or bundle == "dev":
        return "somabrain/auth/allow_dev"
    return "somabrain/auth/allow"


class OPAClient:
    """Strict OPA HTTP client (fail-closed by default).

    POSTs ``/v1/data/<policy_path>`` with JSON ``input`` and expects a ``result``
    containing an ``allow`` boolean. Transport or server errors deny by default.
    A permissive allow-on-error alternative is only enabled if environment variable
    ``SOMABRAIN_OPA_ALLOW_ON_ERROR=1`` is explicitly set (temporary escape hatch).
    """

def __init__(self, policy_path: str | None = None) -> None:
        # Use the canonical Settings field for the OPA request timeout.
        # If the Settings instance is unavailable (unlikely), fall back to 2 seconds.
        if settings is not None:
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                self.timeout = float(
                    getattr(settings, "opa_timeout_seconds", 2.0) or 2.0
                )
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                self.timeout = 2.0
        else:
            self.timeout = 2.0

        # Resolve the OPA endpoint via the centralized ``get_opa_url`` helper.
        # This function already respects the ``SOMABRAIN_OPA_URL`` environment
        # variable and returns ``None`` when the service is not configured.
        self.base_url = get_opa_url()
        if not self.base_url:
            # In a strict deployment the OPA service must be reachable; raise a
            # clear error rather than silently falling back to a dev‑only URL.
            raise RuntimeError("OPA URL is not configured; set SOMABRAIN_OPA_URL")

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
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
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
            logger.exception("Exception caught: %s", e)
            raise

def is_ready(self) -> bool:
        """Check OPA readiness via its /health endpoint.

        Returns True if OPA responds with HTTP 200 within the configured timeout.
        """
        health_url = f"{self.base_url}/health"
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            resp = self.session.get(health_url, timeout=self.timeout)
            return resp.status_code == 200
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            return False

def reload_policy(self) -> bool:
        """Trigger OPA to reload its policies.

        OPA provides an admin endpoint ``/-/reload`` that forces the policy
        bundle to be re-read. This method posts to that endpoint and returns
        ``True`` on a 200 response, ``False`` otherwise.
        """
        reload_url = f"{self.base_url}/-/reload"
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            resp = self.session.post(reload_url, timeout=self.timeout)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.exception("Exception caught: %s", e)
            raise


# Export a singleton for easy import elsewhere if desired
opa_client = OPAClient()

__all__ = ["OPAClient", "opa_client"]
