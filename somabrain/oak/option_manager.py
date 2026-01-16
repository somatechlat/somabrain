"""
Option Manager for OAK (Options, Actions, Knowledge) system.

This module provides the core option management interface for the OAK system.
Full implementation will be added in a future iteration.
"""


class OptionManager:
    """Option Manager for OAK system."""

    def create_option(self, tenant_id: str, option_id: str, payload: bytes) -> dict:
        """Create an option in the OAK system."""
        raise NotImplementedError("OptionManager.create_option is not yet implemented")

    def update_option(self, tenant_id: str, option_id: str, payload: bytes) -> dict:
        """Update an option in the OAK system."""
        raise NotImplementedError("OptionManager.update_option is not yet implemented")

    def get_option(self, tenant_id: str, option_id: str) -> dict:
        """Get an option from the OAK system."""
        raise NotImplementedError("OptionManager.get_option is not yet implemented")


# Singleton instance
option_manager = OptionManager()
