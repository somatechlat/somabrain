the new ``Settings`` attributes.

The project now centralises configuration in ``common.config.settings``
using a ``Settings`` pydantic model.  Existing code still contains calls
such as ``settings.kafka_bootstrap_servers``.  This script scans all
Python files in the repository and rewrites those calls to the appropriate
attribute access (e.g. ``settings.kafka_bootstrap_servers``).

Only known environment variable names are replaced – any unknown ``getenv``
calls are left untouched so that developers can manually address them.

Run the script from the repository root:

```
python scripts/convert_env.py
```

It prints a summary of modified files.
"""

from __future__ import annotations

import pathlib
import re
from typing import Dict, List

ENV_TO_ATTR: Dict[str, str] = {
    "SOMABRAIN_POSTGRES_DSN": "postgres_dsn",
    "SOMABRAIN_REDIS_URL": "redis_url",
    "REDIS_URL": "redis_url",
    "SOMABRAIN_KAFKA_URL": "kafka_bootstrap_servers",
    "KAFKA_BOOTSTRAP_SERVERS": "kafka_bootstrap_servers",
    "SOMABRAIN_REDIS_HOST": "redis_host",
    "REDIS_HOST": "redis_host",
    "SOMABRAIN_REDIS_PORT": "redis_port",
    "REDIS_PORT": "redis_port",
    "SOMABRAIN_REDIS_DB": "redis_db",
    "REDIS_DB": "redis_db",
    "SOMABRAIN_MEMORY_HTTP_HOST": "memory_http_host",
    "MEMORY_HTTP_HOST": "memory_http_host",
    "SOMABRAIN_MEMORY_HTTP_PORT": "memory_http_port",
    "MEMORY_HTTP_PORT": "memory_http_port",
    "SOMABRAIN_MEMORY_HTTP_SCHEME": "memory_http_scheme",
    "MEMORY_HTTP_SCHEME": "memory_http_scheme",
    "SOMABRAIN_KAFKA_HOST": "kafka_host",
    "KAFKA_HOST": "kafka_host",
    "SOMABRAIN_KAFKA_PORT": "kafka_port",
    "KAFKA_PORT": "kafka_port",
    "SOMABRAIN_KAFKA_SCHEME": "kafka_scheme",
    "KAFKA_SCHEME": "kafka_scheme",
    "SOMABRAIN_OPA_HOST": "opa_host",
    "OPA_HOST": "opa_host",
    "SOMABRAIN_OPA_PORT": "opa_port",
    "OPA_PORT": "opa_port",
    "SOMABRAIN_OPA_SCHEME": "opa_scheme",
    "OPA_SCHEME": "opa_scheme",
    "SOMABRAIN_API_URL": "api_url",
    "SOMA_API_URL": "api_url",
    "TEST_SERVER_URL": "api_url",
    "SOMABRAIN_PUBLIC_HOST": "public_host",
    "SOMABRAIN_HOST": "public_host",
    "SOMABRAIN_PUBLIC_PORT": "public_port",
    "SOMABRAIN_HOST_PORT": "public_port",
    "SOMABRAIN_API_SCHEME": "api_scheme",
    "API_SCHEME": "api_scheme",
    "SOMABRAIN_LOG_PATH": "log_path",
    "SUPERVISOR_URL": "supervisor_url",
    "SUPERVISOR_HTTP_USER": "supervisor_http_user",
    "SUPERVISOR_HTTP_PASS": "supervisor_http_pass",
    "RUNNING_IN_DOCKER": "running_in_docker",
    "INTEGRATOR_URL": "integrator_url",
    "SEGMENTATION_URL": "segmentation_url",
    "REWARD_PRODUCER_PORT": "reward_producer_port",
    "REWARD_PRODUCER_HOST_PORT": "reward_producer_host_port",
    "BASE_URL": "api_url",
    # Authentication and security
    "SOMABRAIN_API_TOKEN": "outbox_api_token",
    "SOMA_API_TOKEN": "outbox_api_token",
    "SOMABRAIN_JWT_SECRET": "jwt_secret",
    "SOMABRAIN_JWT_PUBLIC_KEY_PATH": "jwt_public_key_path",
    # Observability
    "OTEL_EXPORTER_OTLP_ENDPOINT": "otel_exporter_otlp_endpoint",
    "OTEL_SERVICE_NAME": "otel_service_name",
    "SERVICE_NAME": "service_name",
    # Testing / CI
    "PYTEST_CURRENT_TEST": "pytest_current_test",
    # OPA policy keys
    "SOMA_OPA_POLICY_KEY": "opa_policy_key",
    "SOMA_OPA_POLICY_SIG_KEY": "opa_policy_sig_key",
    # Miscellaneous defaults
    "BENCH_TIMEOUT": "bench_timeout",
    # Additional configuration fields used throughout the codebase
    "SOMABRAIN_REQUIRE_INFRA": "require_infra",
    "SOMABRAIN_SPECTRAL_CACHE_DIR": "spectral_cache_dir",
    "SOMABRAIN_CONSTITUTION_SNAPSHOT_DIR": "constitution_snapshot_dir",
    "SOMABRAIN_CONSTITUTION_S3_BUCKET": "constitution_s3_bucket",
    "HOSTNAME": "hostname",
    "LEARNING_TENANTS_CONFIG": "learning_tenants_config",
    "SOMABRAIN_LEARNING_TENANTS_FILE": "learning_tenants_file",
    "SOMABRAIN_LEARNING_TENANTS_OVERRIDES": "learning_tenants_overrides",
    "SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS": "require_external_backends",
    "SOMABRAIN_ENABLE_LEARNING_STATE_PERSISTENCE": "enable_learning_state_persistence",
    "SOMABRAIN_TAU_DECAY_ENABLED": "tau_decay_enabled",
    "SOMABRAIN_TAU_DECAY_RATE": "tau_decay_rate",
    "SOMABRAIN_TAU_ANNEAL_MODE": "tau_anneal_mode",
    "SOMABRAIN_MODE": "mode",
    "SOMABRAIN_GRAPH_FILE_AGENT": "graph_file_agent",
    "SOMABRAIN_GRAPH_FILE_STATE": "graph_file_state",
    "SOMABRAIN_PREDICTOR_DIM": "predictor_dim",
    "SOMABRAIN_DIFFUSION_T": "diffusion_t",
    "SOMABRAIN_CONF_ALPHA": "conf_alpha",
    "SOMABRAIN_CHEB_K": "cheb_k",
    "SOMABRAIN_OUTBOX_BATCH_SIZE": "outbox_batch_size",
    "SOMABRAIN_OUTBOX_MAX_RETRIES": "outbox_max_retries",
    "SOMABRAIN_OUTBOX_POLL_INTERVAL": "outbox_poll_interval",
    "SOMABRAIN_OUTBOX_PRODUCER_RETRY_MS": "outbox_producer_retry_ms",
    "SOMABRAIN_JOURNAL_REPLAY_INTERVAL": "journal_replay_interval",
    # Add more mappings as needed.
}


def replace_getenv_calls(content: str) -> str:
    """Replace ``settings.getenv`` calls in *content* using ``ENV_TO_ATTR``.

    The regular expression captures the environment variable name.  If a
    mapping exists, the call is replaced with ``settings.<attr>``; any
    default argument is discarded because the ``Settings`` model already
    provides defaults.
    """

    pattern = re.compile(r"settings\.getenv\(\s*['\"]([^'\"]+)['\"](?:\s*,\s*[^)]+)?\)")

    def repl(match: re.Match) -> str:
        env_name = match.group(1)
        attr = ENV_TO_ATTR.get(env_name)
        if attr:
            return f"settings.{attr}"
        # No mapping – keep the original call.
        return match.group(0)

    return pattern.sub(repl, content)


def process_file(path: pathlib.Path) -> bool:
    """Read *path*, replace env calls, and write back if changed.

    Returns ``True`` if the file was modified.
    """
    original = path.read_text(encoding="utf-8")
    updated = replace_getenv_calls(original)
    if original != updated:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> None:
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    py_files: List[pathlib.Path] = list(repo_root.rglob("*.py"))
    modified: List[pathlib.Path] = []
    for file_path in py_files:
        if process_file(file_path):
            modified.append(file_path)
    if modified:
        print(f"Modified {len(modified)} file(s):")
        for f in modified:
            print(f" - {f.relative_to(repo_root)}")
    else:
        print("No settings.getenv calls were replaced.")


if __name__ == "__main__":
    main()
