"""Module conftest."""

from hypothesis import settings as _hypothesis_settings
import os

# Set local test infrastructure ports BEFORE loading .env or settings
# These use host-mapped ports from docker-compose
# Clear URL settings to force use of host/port settings
os.environ["SOMABRAIN_REDIS_URL"] = ""
os.environ["REDIS_URL"] = ""
os.environ.setdefault("SOMABRAIN_REDIS_HOST", "127.0.0.1")
os.environ.setdefault("SOMABRAIN_REDIS_PORT", "30100")
os.environ.setdefault("SOMABRAIN_MILVUS_HOST", "127.0.0.1")
os.environ.setdefault("SOMABRAIN_MILVUS_PORT", "30119")
os.environ.setdefault("MILVUS_HOST", "127.0.0.1")
os.environ.setdefault("MILVUS_PORT", "30119")

try:
    from dotenv import load_dotenv

    load_dotenv(".env", override=False)
except Exception:
    pass

# Default local overrides for integration tests (host ports)
os.environ.setdefault("SOMABRAIN_MEMORY_HTTP_ENDPOINT", "http://localhost:9595")
os.environ.setdefault(
    "SOMABRAIN_MEMORY_HTTP_TOKEN", os.environ.get("SOMABRAIN_MEMORY_HTTP_TOKEN", "")
)
os.environ.setdefault("SOMABRAIN_API_URL", "http://localhost:30101")
os.environ.setdefault(
    "TEST_PG_DSN", "postgresql://soma:soma_pass@localhost:30106/somabrain"
)
os.environ.setdefault("DATABASE_URL", os.environ["TEST_PG_DSN"])
os.environ.setdefault("SOMABRAIN_POSTGRES_DSN", os.environ["TEST_PG_DSN"])
try:
    from django.conf import settings as _settings

    _settings.postgres_dsn = os.environ["TEST_PG_DSN"]
    tok = os.environ.get("SOMABRAIN_MEMORY_HTTP_TOKEN")
    if tok:
        _settings.memory_http_token = tok
except Exception:
    pass

# pytest configuration to ignore certain scripts that are not intended to be test modules.
collect_ignore = [
    "tests/smoke/kafka_smoke_test.py",
    "tests/smoke/math_smoke_test.py",
]


def pytest_ignore_collect(path, config):
    """Prevent pytest from collecting the problematic Kafka smoke test script.

    A straightforward substring check is sufficient because the script name is
    unique within the repository.
    """
    return any(
        skip_path in str(path)
        for skip_path in (
            "tests/smoke/kafka_smoke_test.py",
            "tests/smoke/math_smoke_test.py",
        )
    )


# ---------------------------------------------------------------------------
# Hypothesis configuration
# ---------------------------------------------------------------------------
# By default Hypothesis stores a persistent database under the ``.hypothesis``
# directory.  This creates a large number of files that are only useful for
# debugging individual test runs.  The test suite does not rely on the
# persistent database, so we disable it to avoid generating those files.
#
# Setting ``database=None`` tells Hypothesis to keep all generated examples in
# memory only.  This change is safe for CI and local runs because it does not
# affect the correctness of the property‑based tests – it merely removes the
# on‑disk storage side‑effect.

# Apply globally: no persistent storage, keep defaults for other settings.
_hypothesis_settings.register_profile("no_persistent", database=None)
_hypothesis_settings.load_profile("no_persistent")
