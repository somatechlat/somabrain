from hypothesis import settings as _hypothesis_settings

# pytest configuration to ignore certain scripts that are not intended to be test modules.
collect_ignore = [
    "scripts/kafka_smoke_test.py",
]


def pytest_ignore_collect(path, config):
    """Prevent pytest from collecting the problematic Kafka smoke test script.

    A straightforward substring check is sufficient because the script name is
    unique within the repository.
    """
    return "scripts/kafka_smoke_test.py" in str(path)


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
