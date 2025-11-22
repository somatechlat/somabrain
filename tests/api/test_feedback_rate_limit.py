import time

import pytest
from fastapi import HTTPException

from somabrain.api import context_route
from common.config.settings import settings as cfg_settings


def test_feedback_rate_limit_blocks_after_threshold(monkeypatch):
    # Set small limit for test
    monkeypatch.setattr(cfg_settings, "feedback_rate_limit_per_minute", 2)
    tenant = "tenant-test"

    # Clear any prior window state
    context_route._feedback_rate_window.pop(tenant, None)

    # First two calls pass
    context_route._enforce_feedback_rate_limit(tenant)
    context_route._enforce_feedback_rate_limit(tenant)

    # Third within same minute should raise
    with pytest.raises(HTTPException) as exc:
        context_route._enforce_feedback_rate_limit(tenant)
    assert exc.value.status_code == 429

    # After waiting >60s window should clear
    context_route._feedback_rate_window[tenant].clear()
    context_route._feedback_rate_window[tenant].append(time.time() - 61)
    # Should now allow again
    context_route._enforce_feedback_rate_limit(tenant)
