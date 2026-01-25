"""
SSO and Identity Provider Package.

Django Ninja API for enterprise SSO configuration.
"""

from .endpoints import router
from .schemas import IdPCreate, IdPDetailOut, IdPOut, IdPStatus, IdPType, IdPUpdate, SSOSettings

__all__ = ["router", "IdPType", "IdPStatus", "IdPCreate", "IdPUpdate", "IdPOut", "IdPDetailOut", "SSOSettings"]
