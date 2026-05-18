"""
Standalone Mode Test Suite.

Tests for single-tenant standalone deployment mode.
These tests verify somabrain works correctly without AAAS multi-tenancy.

Test Categories:
- Config tests: NO database required
- API tests: Require real infrastructure

ALL 10 PERSONAS - VIBE Coding Rules applied.
"""

import importlib

import pytest


class TestStandaloneConfig:
    """
    Test standalone configuration - NO DATABASE REQUIRED.

    These tests verify settings are properly loaded.
    """

    def test_standalone_settings_module_loads(self):
        """Verify Django settings module can be imported."""
        settings_module = importlib.import_module("somabrain.settings.standalone")

        assert settings_module is not None
        assert "somabrain.aaas" not in settings_module.INSTALLED_APPS

    def test_somabrain_mode_setting_exists(self):
        """Verify SOMABRAIN_MODE setting is available."""
        settings_module = importlib.import_module("somabrain.settings.standalone")

        mode = getattr(settings_module, "SOMABRAIN_MODE", None)
        assert mode is not None

    def test_default_tenant_setting_exists(self):
        """Verify default tenant setting is available."""
        settings_module = importlib.import_module("somabrain.settings.standalone")

        default_tenant = getattr(settings_module, "SOMABRAIN_DEFAULT_TENANT", None)
        assert default_tenant == "standalone"

    def test_core_django_settings_available(self):
        """Verify core Django settings are available."""
        settings_module = importlib.import_module("somabrain.settings.standalone")

        assert hasattr(settings_module, "DEBUG")
        assert hasattr(settings_module, "ALLOWED_HOSTS")

    def test_logging_settings_available(self):
        """Verify logging settings are configured."""
        settings_module = importlib.import_module("somabrain.settings.standalone")

        log_level = getattr(settings_module, "SOMABRAIN_LOG_LEVEL", "INFO")
        assert log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


@pytest.mark.django_db(transaction=True)
class TestStandaloneDatabase:
    """
    Test standalone database operations - REQUIRES REAL DATABASE.

    These tests will FAIL (not skip) if PostgreSQL is unavailable.
    This is correct per VIBE Coding Rules.
    """

    def test_database_connection(self):
        """Verify database connection works."""
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1

    def test_database_version(self):
        """Verify PostgreSQL version is accessible."""
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            assert "PostgreSQL" in version


class TestStandaloneImports:
    """
    Test module imports work in standalone mode - NO DATABASE REQUIRED.
    """

    def test_memory_client_importable(self):
        """Verify memory client can be imported."""
        try:
            from somabrain.memory.client import MemoryClient

            assert MemoryClient is not None
        except ImportError as e:
            pytest.fail(f"Failed to import MemoryClient: {e}")

    def test_schemas_importable(self):
        """Verify schemas package can be imported."""
        try:
            from somabrain.schemas import RecallRequest, MemoryPayload

            assert RecallRequest is not None
            assert MemoryPayload is not None
        except ImportError as e:
            pytest.fail(f"Failed to import schemas: {e}")

    def test_api_router_importable(self):
        """Verify API router can be imported."""
        try:
            from somabrain.api.v1 import api

            assert api is not None
        except ImportError as e:
            pytest.fail(f"Failed to import API router: {e}")
