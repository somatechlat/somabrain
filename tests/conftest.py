"""Module conftest."""

import httpx
import pytest

# Django setup is handled by pytest-django via pytest.ini

try:  # load .env for convenience
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=".env", override=False)
except Exception:
    pass

from django.conf import settings
import django

django.setup()


# Use centralized Settings for test configuration (Lazy Loaded)
def get_mem_url():
    """Retrieve mem url."""

    return settings.SOMABRAIN_MEMORY_HTTP_ENDPOINT or "http://localhost:9595"


def get_mem_token():
    """Retrieve mem token."""

    return settings.SOMABRAIN_MEMORY_HTTP_TOKEN


def get_api_url():
    """Retrieve api url."""

    return settings.SOMABRAIN_API_URL or "http://localhost:9696"


def _memory_available() -> bool:
    """Execute memory available."""

    mem_url = get_mem_url()
    mem_token = get_mem_token()
    try:
        headers = {"Authorization": f"Bearer {mem_token}"} if mem_token else {}
        url = mem_url.rstrip("/")
        # print(f"DEBUG: Checking Memory Health at {url}/health")
        r = httpx.get(f"{url}/health", timeout=2.0, headers=headers)
        return r.status_code < 500
    except Exception as e:
        print(f"WARNING: Memory Check Failed at {mem_url}: {e}")
        return False


def _api_available() -> bool:
    """Execute api available."""

    try:
        base = get_api_url()
        r = httpx.get(f"{base.rstrip('/')}/health", timeout=2.0)
        if r.status_code < 500:
            return True
        r = httpx.get("http://localhost:9696/health", timeout=2.0)
        return r.status_code < 500
    except Exception:
        return False


@pytest.fixture(scope="session")
def http_client() -> httpx.Client:
    """Execute http client."""

    mem_token = get_mem_token()
    if not mem_token:
        # pytest.skip("SOMABRAIN_MEMORY_HTTP_TOKEN must be set for workbench tests")
        # Making this optional for now to allow partial testing
        pass

    if not _memory_available():
        # Warn but don't fail immediately, allows viewing output
        print("WARNING: Memory service not reachable.")

    if not _api_available():
        print("WARNING: Somabrain API not reachable.")

    base = get_api_url()
    try:
        httpx.get(f"{base.rstrip('/')}/health", timeout=1.0)
    except Exception:
        base = "http://localhost:9696"
    return httpx.Client(base_url=base, timeout=5.0)
