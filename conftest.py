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
