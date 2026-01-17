"""Centralized Error Codes and Messages — I18N Ready.

VIBE RULE 11: All user-facing text MUST use get_message().
This module is the SINGLE SOURCE OF TRUTH for all SomaBrain messages.
"""

from enum import Enum

from django.utils.translation import gettext_lazy as _


class ErrorCode(str, Enum):
    """Error codes for SomaBrain modules."""

    # Generic
    INTERNAL_ERROR = "internal_error"
    INVALID_REQUEST = "invalid_request"

    # Config
    CONFIG_MISSING = "config_missing"
    CONFIG_INVALID = "config_invalid"

    # Memory Operations
    MEMORY_RECALL_FAILED = "memory_recall_failed"
    MEMORY_STORE_FAILED = "memory_store_failed"
    MEMORY_DELETE_FAILED = "memory_delete_failed"
    MEMORY_NOT_FOUND = "memory_not_found"

    # Cognitive
    COGNITIVE_LEARN_FAILED = "cognitive_learn_failed"
    COGNITIVE_ASK_FAILED = "cognitive_ask_failed"
    COGNITIVE_ACT_FAILED = "cognitive_act_failed"

    # Embedding
    EMBEDDING_FAILED = "embedding_failed"
    EMBEDDING_MODEL_UNAVAILABLE = "embedding_model_unavailable"

    # External Services
    MILVUS_UNAVAILABLE = "milvus_unavailable"
    POSTGRES_UNAVAILABLE = "postgres_unavailable"
    REDIS_UNAVAILABLE = "redis_unavailable"
    KAFKA_UNAVAILABLE = "kafka_unavailable"


class SuccessCode(str, Enum):
    """Success codes for confirmations."""

    MEMORY_STORED = "memory_stored"
    MEMORY_RECALLED = "memory_recalled"
    MEMORY_DELETED = "memory_deleted"
    LEARNED = "learned"


# I18N-Ready Messages using Django gettext_lazy
MESSAGES: dict[str | ErrorCode | SuccessCode, str] = {
    # Generic
    ErrorCode.INTERNAL_ERROR: _("An unexpected error occurred in SomaBrain"),
    ErrorCode.INVALID_REQUEST: _("Invalid request to cognitive engine"),
    # Config
    ErrorCode.CONFIG_MISSING: _("Required configuration '{key}' is missing"),
    ErrorCode.CONFIG_INVALID: _("Configuration '{key}' is invalid: {reason}"),
    # Memory
    ErrorCode.MEMORY_RECALL_FAILED: _("Failed to recall memories for query"),
    ErrorCode.MEMORY_STORE_FAILED: _("Failed to store memory"),
    ErrorCode.MEMORY_DELETE_FAILED: _("Failed to delete memory"),
    ErrorCode.MEMORY_NOT_FOUND: _("Memory with id '{id}' not found"),
    # Cognitive
    ErrorCode.COGNITIVE_LEARN_FAILED: _("Failed to learn from interaction"),
    ErrorCode.COGNITIVE_ASK_FAILED: _("Failed to process brain query"),
    ErrorCode.COGNITIVE_ACT_FAILED: _("Failed to execute cognitive action"),
    # Embedding
    ErrorCode.EMBEDDING_FAILED: _("Failed to generate embeddings"),
    ErrorCode.EMBEDDING_MODEL_UNAVAILABLE: _("Embedding model is unavailable"),
    # External Services
    ErrorCode.MILVUS_UNAVAILABLE: _("Vector store (Milvus) is temporarily unavailable"),
    ErrorCode.POSTGRES_UNAVAILABLE: _("Database is temporarily unavailable"),
    ErrorCode.REDIS_UNAVAILABLE: _("Cache (Redis) is temporarily unavailable"),
    ErrorCode.KAFKA_UNAVAILABLE: _("Event bus (Kafka) is temporarily unavailable"),
    # Success
    SuccessCode.MEMORY_STORED: _("Memory stored successfully"),
    SuccessCode.MEMORY_RECALLED: _("Memories recalled successfully"),
    SuccessCode.MEMORY_DELETED: _("Memory deleted successfully"),
    SuccessCode.LEARNED: _("Learning completed successfully"),
}


def get_message(code: ErrorCode | SuccessCode | str, **kwargs: object) -> str:
    """Get formatted, translated message for code.

    Args:
        code: Error or success code from enum
        **kwargs: Format arguments for message template

    Returns:
        Formatted, translated message string
    """
    msg = MESSAGES.get(code, _("Unknown error"))
    if kwargs:
        return str(msg).format(**kwargs)
    return str(msg)
