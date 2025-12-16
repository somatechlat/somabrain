import httpx
import pytest

try:  # load .env for convenience
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=".env", override=False)
except Exception:
    pass

from common.config.settings import settings


# Use centralized Settings for test configuration
MEM_URL = settings.memory_http_endpoint or "http://localhost:9595"
MEM_TOKEN = settings.memory_http_token
API_URL = settings.api_url or "http://localhost:9696"


def _memory_available() -> bool:
    try:
        headers = {"Authorization": f"Bearer {MEM_TOKEN}"} if MEM_TOKEN else {}
        url = MEM_URL.rstrip("/")
        try:
            r = httpx.get(f"{url}/health", timeout=2.0, headers=headers)
        except Exception:
            # Fallback to localhost if host.docker.internal is unreachable.
            r = httpx.get("http://localhost:9595/health", timeout=2.0, headers=headers)
        return r.status_code < 500
    except Exception:
        return False


def _api_available() -> bool:
    try:
        base = API_URL or "http://localhost:9696"
        r = httpx.get(f"{base.rstrip('/')}/health", timeout=2.0)
        if r.status_code < 500:
            return True
        r = httpx.get("http://localhost:9696/health", timeout=2.0)
        return r.status_code < 500
    except Exception:
        return False


@pytest.fixture(scope="session")
def http_client() -> httpx.Client:
    if not MEM_TOKEN:
        pytest.skip("SOMABRAIN_MEMORY_HTTP_TOKEN must be set for workbench tests")
    if not _memory_available():
        pytest.skip("Memory service not reachable for workbench tests")
    if not _api_available():
        pytest.skip("Somabrain API not reachable for workbench tests")
    base = API_URL
    try:
        httpx.get(f"{base.rstrip('/')}/health", timeout=1.0)
    except Exception:
        base = "http://localhost:9696"
    return httpx.Client(base_url=base, timeout=5.0)
