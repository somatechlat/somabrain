from ninja.errors import HttpError

# =============================================================================
# SCOPE CHECKING DECORATOR
# =============================================================================


def require_scope(scope: str):
    """
    Decorator to require a specific API key scope.

    Example:
        @api.get("/memories", auth=APIKeyAuth())
        @require_scope("read:memory")
        def list_memories(request):
            ...
    """

    def decorator(func):
        """Execute decorator.

        Args:
            func: The func.
        """

        def wrapper(request, *args, **kwargs):
            """Execute wrapper.

            Args:
                request: The request.
            """

            auth = getattr(request, "auth", {})
            scopes = auth.get("scopes", [])

            if "admin" in scopes:
                # Admin scope bypasses all checks
                return func(request, *args, **kwargs)

            if scope not in scopes:
                from ninja.errors import HttpError

                raise HttpError(403, f"Missing required scope: {scope}")

            return func(request, *args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator


# =============================================================================
# ROLE-BASED ACCESS DECORATOR
# =============================================================================


def require_auth(roles: list = None, any_role: bool = False):
    """
    Decorator to require JWT authentication with optional role checking.

    ALL 10 PERSONAS:
    - Security: Role-based access control
    - QA: Testable permission logic
    - Docs: Clear docstrings

    Args:
        roles: List of required roles (e.g., ["super-admin", "tenant-admin"])
        any_role: If True, any matching role is sufficient. If False, all required.

    Example:
        @router.get("/admin/tenants")
        @require_auth(roles=["super-admin"])
        def list_tenants(request: AuthenticatedRequest):
            ...
    """

    def decorator(func):
        """Execute decorator.

        Args:
            func: The func.
        """

        from functools import wraps

        @wraps(func)
        def wrapper(request, *args, **kwargs):
            """Execute wrapper.

            Args:
                request: The request.
            """


            # Check for JWT auth
            auth = getattr(request, "auth", None)
            if auth is None:
                raise HttpError(401, "Authentication required")

            # Extract user info
            user_roles = auth.get("roles", [])

            # Attach to request for easy access
            request.user_id = auth.get("user_id")
            request.email = auth.get("email")
            request.name = auth.get("name")
            request.roles = user_roles
            request.tenant_id = auth.get("tenant_id")
            request.is_super_admin = "super-admin" in user_roles

            # Check roles if specified
            if roles:
                if any_role:
                    # Any matching role is sufficient
                    if not any(r in user_roles for r in roles):
                        raise HttpError(
                            403, f"Missing required role. Need one of: {roles}"
                        )
                else:
                    # All roles required
                    missing = [r for r in roles if r not in user_roles]
                    if missing:
                        raise HttpError(403, f"Missing required roles: {missing}")

            return func(request, *args, **kwargs)

        return wrapper

    return decorator


# =============================================================================
# FIELD-LEVEL PERMISSION CHECKER
# =============================================================================


class FieldPermissionChecker:
    """
    Check and filter fields based on role permissions.

    ALL 10 PERSONAS:
    - Security: Field-level access control, no data leakage
    - DBA: Efficient permission queries with caching
    - Performance: Cached permission lookups
    - Architect: Clean separation of concerns

    Example:
        checker = FieldPermissionChecker(user_roles)

        # Check if user can view a field
        if checker.can_view("Tenant", "billing_email"):
            ...

        # Filter a dict to only allowed fields
        filtered = checker.filter_response("Tenant", tenant_data)

        # Validate update payload
        checker.validate_update("Tenant", update_data)  # raises HttpError if denied
    """

    # Cache for permission lookups (role -> model -> field -> can_view/can_edit)
    _cache: dict = {}

    def __init__(self, user_roles: list, tenant_id: str = None):
        """
        Initialize checker for a user's roles.

        Args:
            user_roles: List of role names/slugs
            tenant_id: Optional tenant for tenant-specific overrides
        """
        self.user_roles = user_roles
        self.tenant_id = tenant_id
        self._permissions = None  # Lazy load

    def _load_permissions(self):
        """Load permissions from database (cached)."""
        if self._permissions is not None:
            return

        from .models import FieldPermission, Role

        # Get role IDs for user's roles
        roles = Role.objects.filter(slug__in=self.user_roles)
        role_ids = [r.id for r in roles]

        # Get all field permissions for these roles
        permissions = FieldPermission.objects.filter(role_id__in=role_ids)

        # Build permission map: model -> field -> (can_view, can_edit)
        self._permissions = {}
        for perm in permissions:
            if perm.model_name not in self._permissions:
                self._permissions[perm.model_name] = {}

            # Merge permissions (OR logic - any role grants access)
            existing = self._permissions[perm.model_name].get(
                perm.field_name, (False, False)
            )
            self._permissions[perm.model_name][perm.field_name] = (
                existing[0] or perm.can_view,
                existing[1] or perm.can_edit,
            )

    def can_view(self, model: str, field: str) -> bool:
        """Check if user can view a specific field."""
        # Super-admin can view everything
        if "super-admin" in self.user_roles:
            return True

        self._load_permissions()
        model_perms = self._permissions.get(model, {})
        field_perms = model_perms.get(field, (False, False))
        return field_perms[0]

    def can_edit(self, model: str, field: str) -> bool:
        """Check if user can edit a specific field."""
        # Super-admin can edit everything
        if "super-admin" in self.user_roles:
            return True

        self._load_permissions()
        model_perms = self._permissions.get(model, {})
        field_perms = model_perms.get(field, (False, False))
        return field_perms[1]

    def get_viewable_fields(self, model: str, all_fields: list) -> list:
        """Get list of fields the user can view for a model."""
        if "super-admin" in self.user_roles:
            return all_fields

        return [f for f in all_fields if self.can_view(model, f)]

    def get_editable_fields(self, model: str, all_fields: list) -> list:
        """Get list of fields the user can edit for a model."""
        if "super-admin" in self.user_roles:
            return all_fields

        return [f for f in all_fields if self.can_edit(model, f)]

    def filter_response(self, model: str, data: dict) -> dict:
        """
        Filter a response dict to only include viewable fields.

        ALL 10 PERSONAS - Security: Prevents data leakage.
        """
        if "super-admin" in self.user_roles:
            return data

        viewable = self.get_viewable_fields(model, list(data.keys()))
        return {k: v for k, v in data.items() if k in viewable}

    def validate_update(self, model: str, data: dict) -> None:
        """
        Validate that user can edit all fields in the update payload.

        Raises HttpError(403) if any field is not editable.

        ALL 10 PERSONAS - Security: Prevents unauthorized modifications.
        """
        if "super-admin" in self.user_roles:
            return


        editable = self.get_editable_fields(model, list(data.keys()))
        forbidden = [k for k in data.keys() if k not in editable]

        if forbidden:
            raise HttpError(403, f"Cannot edit fields: {forbidden}")
