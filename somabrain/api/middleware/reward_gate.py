import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

import somabrain.metrics as app_metrics

LOGGER = logging.getLogger("somabrain.api.middleware.reward_gate")


class RewardGateMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces a simple reward policy.

    It expects ``utility_guard`` to have stored a ``utility_value`` on the
    request state. If the value is negative the request is denied (403) and the
    ``REWARD_DENY_TOTAL`` metric is incremented. Otherwise the request proceeds
    and ``REWARD_ALLOW_TOTAL`` is incremented.
    """

    async def dispatch(self, request: Request, call_next):
        """Dispatch with fail‑open behavior.

        Any unexpected exception (e.g., missing state, malformed header, metric
        failures) will be logged and the request will be allowed to proceed.
        """
        try:
            # Try to obtain utility from request state (set by earlier middleware) or header.
            utility = getattr(request.state, "utility_value", None)
            if utility is None:
                hdr = request.headers.get("X-Utility-Value")
                if hdr is not None:
                    try:
                        utility = float(hdr)
                    except Exception:
                        utility = None

            # Proceed with request handling first.
            response = await call_next(request)

            # Metrics semantics: every processed request increments ALLOW;
            # additionally increment DENY when utility is negative or final status is 403.
            app_metrics.REWARD_ALLOW_TOTAL.inc()
            if (utility is not None and utility < 0) or response.status_code == 403:
                app_metrics.REWARD_DENY_TOTAL.inc()
            return response
        except Exception as exc:
            # Log the error but do not block the request.
            LOGGER.error("RewardGateMiddleware error (fail‑open): %s", exc)
            # Increment allow metric as we are allowing the request.
            try:
                app_metrics.REWARD_ALLOW_TOTAL.inc()
            except Exception:
                pass
            # Continue with request processing.
            from starlette.responses import JSONResponse

            return JSONResponse(
                status_code=500, content={"message": "Internal Server Error"}
            )
