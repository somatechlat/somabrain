"""Centralized Error Codes and Messages — I18N Ready.

VIBE RULE 11: All user-facing text MUST use get_message().
This module is the SINGLE SOURCE OF TRUTH for all SomaBrain messages.
"""

from enum import Enum
from django.utils.translation import gettext_lazy as _

class ErrorCode(str, Enum):
    """Error codes for SomaBrain modules."""
    INTERNAL_ERROR = "internal_error"
    INVALID_REQUEST = "invalid_request"
    PERMISSION_DENIED = "permission_denied"

    # Brain Settings
    BRAIN_SETTING_NOT_FOUND = "brain_setting_not_found"
    BRAIN_SETTING_INVALID_TYPE = "brain_setting_invalid_type"
    BRAIN_INITIALIZATION_FAILED = "brain_initialization_failed"

class SuccessCode(str, Enum):
    """Success codes for confirmations."""
    HEALTH_OK = "health_ok"
    BRAIN_INITIALIZED = "brain_initialized"
    SETTING_UPDATED = "setting_updated"

MESSAGES = {
    ErrorCode.INTERNAL_ERROR: _("An unexpected error occurred in SomaBrain"),
    ErrorCode.INVALID_REQUEST: _("Invalid request"),
    ErrorCode.PERMISSION_DENIED: _("Permission denied"),

    ErrorCode.BRAIN_SETTING_NOT_FOUND: _("Brain setting '{key}' not found for tenant '{tenant}'. Run initialize_defaults() first."),
    ErrorCode.BRAIN_SETTING_INVALID_TYPE: _("Invalid value type '{value_type}' for setting '{key}'"),
    ErrorCode.BRAIN_INITIALIZATION_FAILED: _("Failed to initialize brain defaults: {error}"),

    SuccessCode.HEALTH_OK: _("SomaBrain is healthy"),
    SuccessCode.BRAIN_INITIALIZED: _("Brain defaults initialized successfully"),
    SuccessCode.SETTING_UPDATED: _("Setting '{key}' updated successfully"),
}

def get_message(code: ErrorCode | SuccessCode | str, **kwargs: object) -> str:
    """Get formatted, translated message for code."""
    msg = MESSAGES.get(code, _("Unknown error"))
    try:
        if kwargs:
            return str(msg).format(**kwargs)
        return str(msg)
    except KeyError as e:
        return f"{msg} (missing parameter: {e})"
