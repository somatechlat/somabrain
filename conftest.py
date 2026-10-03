"""Module conftest."""

import os
import pathlib
import sys

from hypothesis import settings as _hypothesis_settings

# Tests whose subject package is deliberately Django-free. When the run
# contains only these, ``DJANGO_SETTINGS_MODULE`` is left unset so the
# pytest-django plugin stays dormant and the memory-HTTP credential gate is
# never imported. Booting settings for them would couple a pure transport test
# to a credential it does not use and cannot obtain.
#
# Membership is declared where it is decided: on the test itself, as
# ``pytest.mark.no_django``. The run is treated as Django-free exactly when
# every test file named on the command line carries that marker. A hand-kept
# path list here would silently rot the moment someone wrote the next pure
# suite and forgot to register it — and mixing one unregistered file into the
# run would quietly boot settings for the registered ones too.
_MARK_NO_DJANGO = "pytest.mark.no_django"


def _declares_no_django(path: str) -> bool:
    """True when the file marks itself as covering a Django-free package."""
    try:
        source = pathlib.Path(path).read_text(encoding="utf-8")
    except OSError:
        return False
    return _MARK_NO_DJANGO in source


def _running_only_django_free(argv: list[str]) -> bool:
    """True when every test path on the command line opts out of Django.

    Flags and options are ignored, and node ids are reduced to their file part
    (``tests/x.py::test_y`` -> ``tests/x.py``). A bare ``pytest`` run with no
    paths is never treated as Django-free, so the full suite keeps booting
    settings exactly as it did before.
    """
    paths = []
    for arg in argv[1:]:
        if arg.startswith("-"):
            continue
        file_part = arg.split("::", 1)[0].replace(os.sep, "/")
        if file_part.endswith(".py"):
            paths.append(file_part)
    if not paths:
        return False
    return all(_declares_no_django(p) for p in paths)


if _running_only_django_free(sys.argv):
    # Deliberately leave DJANGO_SETTINGS_MODULE unset.
    pass
elif any("tests/standalone" in arg for arg in sys.argv):
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
test_pg_host = os.environ.get("TEST_PG_HOST", "localhost")
test_pg_port = os.environ.get("TEST_PG_PORT", "30106")
test_pg_db = os.environ.get("TEST_PG_DB", os.environ.get("POSTGRES_DB", "somabrain"))

# VIBE secret contract: the test DB password is a credential, so it is never a
# literal in this file and never defaulted. It is resolved from Vault
# (secret/agent/credentials/postgres_password via get_db_credentials) exactly as
# production does. The test runner may inject it explicitly through
# TEST_PG_PASSWORD; there is deliberately no fallback value — a baked-in default
# would be a dummy credential past a real auth gate.
test_pg_password = os.environ.get("TEST_PG_PASSWORD")
if not test_pg_password:
    try:
        from somabrain.core.security.vault_client import get_db_credentials

        test_pg_password = (get_db_credentials() or {}).get("password")
    except Exception:
        test_pg_password = None

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
# No empty-string default for the memory HTTP token: an empty token is a shim
# that lets a service authenticate as nobody. The test runner supplies the real
# value (from Vault) or the call fails closed.
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
