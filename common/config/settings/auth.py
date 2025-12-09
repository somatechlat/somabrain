"""Authentication and security settings for SomaBrain.

This module contains configuration for:
- JWT authentication
- OPA policy enforcement
- Provenance verification
- Constitution/Vault integration
"""

from __future__ import annotations

from typing import Optional

from common.config.settings.base import (
    BaseSettings,
    Field,
    _bool_env,
    _int_env,
    _str_env,
)


class AuthSettingsMixin(BaseSettings):
    """Authentication and security settings mixin."""

    # API authentication
    auth_required: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_AUTH_REQUIRED", False)
    )
    api_token: Optional[str] = Field(default=_str_env("SOMABRAIN_API_TOKEN"))
    auth_service_url: Optional[str] = Field(
        default=_str_env("SOMABRAIN_AUTH_SERVICE_URL")
    )
    auth_service_api_key: Optional[str] = Field(
        default=_str_env("SOMABRAIN_AUTH_SERVICE_API_KEY")
    )

    # JWT configuration
    jwt_secret: Optional[str] = Field(default=_str_env("SOMABRAIN_JWT_SECRET"))
    jwt_public_key_path: Optional[str] = Field(
        default=_str_env("SOMABRAIN_JWT_PUBLIC_KEY_PATH")
    )

    # OPA key paths
    opa_privkey_path: Optional[str] = Field(default=_str_env("SOMA_OPA_PRIVKEY_PATH"))
    opa_pubkey_path: Optional[str] = Field(default=_str_env("SOMA_OPA_PUBKEY_PATH"))

    # Provenance / audit
    provenance_secret: Optional[str] = Field(
        default=_str_env("SOMABRAIN_PROVENANCE_SECRET")
    )
    provenance_strict_deny: bool = Field(
        default_factory=lambda: _bool_env("PROVENANCE_STRICT_DENY", False)
    )
    require_provenance: bool = Field(
        default_factory=lambda: _bool_env("REQUIRE_PROVENANCE", False)
    )

    # Vault integration
    vault_addr: Optional[str] = Field(default=_str_env("VAULT_ADDR"))
    vault_token: Optional[str] = Field(default=_str_env("VAULT_TOKEN"))
    vault_pubkey_path: Optional[str] = Field(
        default=_str_env("SOMABRAIN_VAULT_PUBKEY_PATH")
    )

    # Constitution configuration
    constitution_pubkeys: Optional[str] = Field(
        default=_str_env("SOMABRAIN_CONSTITUTION_PUBKEYS")
    )
    constitution_pubkey_path: Optional[str] = Field(
        default=_str_env("SOMABRAIN_CONSTITUTION_PUBKEY_PATH")
    )
    constitution_privkey_path: Optional[str] = Field(
        default=_str_env("SOMABRAIN_CONSTITUTION_PRIVKEY_PATH")
    )
    constitution_threshold: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_CONSTITUTION_THRESHOLD", 1)
    )
    constitution_signer_id: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_CONSTITUTION_SIGNER_ID", "default")
        or "default"
    )

    # Feature flags
    minimal_public_api: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_MINIMAL_PUBLIC_API", False)
    )
    allow_anonymous_tenants: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_ALLOW_ANONYMOUS_TENANTS", False)
    )
    block_ua_regex: str = Field(default=_str_env("SOMABRAIN_BLOCK_UA_REGEX", ""))
    kill_switch: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_KILL_SWITCH", False)
    )
    allow_tiny_embedder: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_ALLOW_TINY_EMBEDDER", False)
    )

    # Feature overrides
    feature_overrides_path: Optional[str] = Field(
        default=_str_env("SOMABRAIN_FEATURE_OVERRIDES", "./data/feature_overrides.json")
    )

    # Cognitive threads
    enable_cog_threads: bool = Field(
        default=False, description="Enable Cognitive Threads v2"
    )
    COGNITIVE_THREAD_DEFAULT_CURSOR: int = 0

    # Orchestrator configuration
    orchestrator_consumer_group: str = Field(
        default_factory=lambda: _str_env(
            "SOMABRAIN_ORCH_CONSUMER_GROUP", "orchestrator-service"
        )
        or "orchestrator-service"
    )
    orchestrator_namespace: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_ORCH_NAMESPACE", "cog") or "cog"
    )
    orchestrator_routing: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_ORCH_ROUTING", "") or ""
    )

    # Teach feedback processor
    teach_feedback_proc_port: int = Field(
        default_factory=lambda: _int_env("TEACH_FEEDBACK_PROC_PORT", 8086)
    )
    teach_feedback_proc_group: str = Field(
        default_factory=lambda: _str_env("TEACH_PROC_GROUP", "teach-feedback-proc")
        or "teach-feedback-proc"
    )
    teach_dedup_cache_size: int = Field(
        default_factory=lambda: _int_env("TEACH_DEDUP_CACHE_SIZE", 512)
    )

    # Feature flags service
    feature_flags_port: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_FEATURE_FLAGS_PORT", 9697)
    )

    # Universe
    universe: Optional[str] = Field(default=_str_env("SOMA_UNIVERSE"))

    # Reward port
    reward_port: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_REWARD_PORT", 8083)
    )
    reward_producer_port: int = Field(
        default_factory=lambda: _int_env("REWARD_PRODUCER_PORT", 30183)
    )
    reward_producer_host_port: int = Field(
        default_factory=lambda: _int_env("REWARD_PRODUCER_HOST_PORT", 30183)
    )

    # Benchmark timeout
    bench_timeout: float = Field(
        default_factory=lambda: _float_env("BENCH_TIMEOUT", 90.0)
    )


def _float_env(name: str, default: float) -> float:
    """Import helper for float env parsing."""
    from common.config.settings.base import _float_env as _fe
    return _fe(name, default)
