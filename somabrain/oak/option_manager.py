"""
Option Manager stub for OAK (Options, Actions, Knowledge) system.

This is a placeholder to allow the Constitution seeding to proceed.
Full implementation will be added in a future iteration.
"""


class OptionManager:
    """Stub Option Manager for OAK system."""

    def create_option(self, tenant_id: str, option_id: str, payload: bytes) -> dict:
        """Create an option (stub)."""
        raise NotImplementedError("OptionManager.create_option is not yet implemented")

    def update_option(self, tenant_id: str, option_id: str, payload: bytes) -> dict:
        """Update an option (stub)."""
        raise NotImplementedError("OptionManager.update_option is not yet implemented")

    def get_option(self, tenant_id: str, option_id: str) -> dict:
        """Get an option (stub)."""
        raise NotImplementedError("OptionManager.get_option is not yet implemented")


# Singleton instance
option_manager = OptionManager()
