"""Module conftest."""

from hypothesis import settings as _hypothesis_settings
import os
import sys

if any("tests/standalone" in arg for arg in sys.argv):
    os.environ["DJANGO_SETTINGS_MODULE"] = "somabrain.settings.standalone"
else:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somabrain.settings")

# Set local test infrastructure ports BEFORE loading .env or settings
# These use host-mapped ports from docker-compose
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

# Default local overrides for tests. These intentionally override local .env
# runtime values so pytest uses an explicit, reproducible test target.
test_memory_endpoint = os.environ.get(
    "TEST_MEMORY_HTTP_ENDPOINT",
    "http://localhost:10101",
)
test_pg_user = os.environ.get(
    "TEST_PG_USER", os.environ.get("POSTGRES_USER", "somabrain")
)
test_pg_password = os.environ.get(
    "TEST_PG_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "somabrain")
)
test_pg_host = os.environ.get("TEST_PG_HOST", "localhost")
test_pg_port = os.environ.get("TEST_PG_PORT", "30106")
test_pg_db = os.environ.get("TEST_PG_DB", os.environ.get("POSTGRES_DB", "somabrain"))

if "TEST_PG_DSN" in os.environ:
    test_pg_dsn = os.environ["TEST_PG_DSN"]
elif test_pg_password:
    test_pg_dsn = (
        f"postgresql://{test_pg_user}:{test_pg_password}"
        f"@{test_pg_host}:{test_pg_port}/{test_pg_db}"
    )
else:
    test_pg_dsn = (
        f"postgresql://{test_pg_user}@{test_pg_host}:{test_pg_port}/{test_pg_db}"
    )

test_redis_url = os.environ.get(
    "TEST_REDIS_URL",
    "redis://127.0.0.1:30100/0",
)

os.environ["SOMABRAIN_MEMORY_HTTP_ENDPOINT"] = test_memory_endpoint
os.environ.setdefault("SOMABRAIN_MEMORY_HTTP_TOKEN", "")
os.environ.setdefault("SOMABRAIN_API_URL", "http://localhost:30101")
os.environ["SOMABRAIN_REDIS_URL"] = test_redis_url
os.environ["REDIS_URL"] = test_redis_url
os.environ["TEST_PG_DSN"] = test_pg_dsn
os.environ["DATABASE_URL"] = test_pg_dsn
os.environ["SOMABRAIN_POSTGRES_DSN"] = test_pg_dsn
try:
    from django.conf import settings as _settings

    _settings.postgres_dsn = test_pg_dsn
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
