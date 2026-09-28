"""
User Management API Package.

Django Ninja router for tenant user CRUD and role management.
"""

from .endpoints import router
from .schemas import (
    RoleAssignment,
    UserCreate,
    UserFilters,
    UserInvite,
    UserListOut,
    UserOut,
    UserUpdate,
)

__all__ = [
    "RoleAssignment",
    "UserCreate",
    "UserFilters",
    "UserInvite",
    "UserListOut",
    "UserOut",
    "UserUpdate",
    "router",
]
