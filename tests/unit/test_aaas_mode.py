"""Unit tests for AAAS Mode (Direct Memory Backend).

These tests verify the AAAS mode infrastructure WITHOUT requiring the full
infrastructure stack. For full integration tests, use test_aaas_integration.py.

VIBE Compliance: These are unit tests, so mocking is acceptable here.
"""

import os
import pytest
from unittest.mock import MagicMock, patch


class TestMemoryModeSettings:
    """Test SOMABRAIN_MEMORY_MODE setting detection."""

    def test_default_mode_is_http(self, monkeypatch):
        """Default mode should be 'http'."""
        monkeypatch.delenv("SOMABRAIN_MEMORY_MODE", raising=False)

        # Clear cached modules
        import sys
        for mod in list(sys.modules.keys()):
            if 'somabrain.settings' in mod:
                del sys.modules[mod]

        from somabrain.memory.backends import get_memory_mode
        assert get_memory_mode() == "http"

    def test_direct_mode_detected(self, monkeypatch):
        """Setting SOMABRAIN_MEMORY_MODE=direct should enable AAAS mode."""
        monkeypatch.setenv("SOMABRAIN_MEMORY_MODE", "direct")

        # Clear cached modules
        import sys
        for mod in list(sys.modules.keys()):
            if 'somabrain.settings' in mod:
                del sys.modules[mod]

        from somabrain.memory.backends import get_memory_mode, is_aaas_mode
        assert get_memory_mode() == "direct"
        assert is_aaas_mode() is True

    def test_http_mode_not_aaas(self, monkeypatch):
        """HTTP mode should return is_aaas_mode() = False."""
        monkeypatch.setenv("SOMABRAIN_MEMORY_MODE", "http")

        # Clear cached modules
        import sys
        for mod in list(sys.modules.keys()):
            if 'somabrain.settings' in mod:
                del sys.modules[mod]

        from somabrain.memory.backends import is_aaas_mode
        assert is_aaas_mode() is False


class TestKeyToCoordinate:
    """Test the deterministic key to coordinate conversion."""

    def test_key_to_coord_deterministic(self):
        """Same key should always produce same coordinate."""
        from somabrain.memory.direct_backend import _key_to_coord

        coord1 = _key_to_coord("test_key")
        coord2 = _key_to_coord("test_key")

        assert coord1 == coord2
        assert len(coord1) == 3

    def test_key_to_coord_bounds(self):
        """Coordinates should be in [-1, 1] range."""
        from somabrain.memory.direct_backend import _key_to_coord

        for key in ["a", "test", "very_long_key_name_12345", "unicode_Ω_测试"]:
            coord = _key_to_coord(key)
            assert len(coord) == 3
            for c in coord:
                assert -1.0 <= c <= 1.0

    def test_different_keys_different_coords(self):
        """Different keys should produce different coordinates."""
        from somabrain.memory.direct_backend import _key_to_coord

        coord1 = _key_to_coord("key1")
        coord2 = _key_to_coord("key2")

        assert coord1 != coord2


class TestDirectMemoryBackendClass:
    """Test DirectMemoryBackend class structure (without instantiation)."""

    def test_class_exists(self):
        """DirectMemoryBackend class should be importable."""
        from somabrain.memory.direct_backend import DirectMemoryBackend
        assert DirectMemoryBackend is not None

    def test_class_has_required_methods(self):
        """Class should have all MemoryBackend Protocol methods."""
        from somabrain.memory.direct_backend import DirectMemoryBackend

        required_methods = [
            "remember",
            "aremember",
            "recall",
            "arecall",
            "coord_for_key",
            "fetch_by_coord",
            "delete",
            "health",
        ]

        for method in required_methods:
            assert hasattr(DirectMemoryBackend, method), f"Missing method: {method}"
            assert callable(getattr(DirectMemoryBackend, method))

    def test_class_has_graph_extension_methods(self):
        """Class should have graph extension methods."""
        from somabrain.memory.direct_backend import DirectMemoryBackend

        graph_methods = ["link", "alink", "links_from", "k_hop", "payloads_for_coords"]

        for method in graph_methods:
            assert hasattr(DirectMemoryBackend, method), f"Missing graph method: {method}"


class TestBackendFactory:
    """Test get_memory_backend factory function."""

    @patch("somabrain.memory.backends.MemoryClient")
    def test_http_mode_returns_memory_client(self, mock_client, monkeypatch):
        """HTTP mode should return MemoryClient."""
        monkeypatch.setenv("SOMABRAIN_MEMORY_MODE", "http")

        # Clear cached modules
        import sys
        for mod in list(sys.modules.keys()):
            if 'somabrain.settings' in mod:
                del sys.modules[mod]

        from somabrain.memory.backends import get_memory_backend

        mock_client.return_value = MagicMock()
        backend = get_memory_backend(namespace="test")

        mock_client.assert_called_once()

    def test_direct_mode_import_error_without_sfm(self, monkeypatch):
        """Direct mode without somafractalmemory should raise ImportError."""
        monkeypatch.setenv("SOMABRAIN_MEMORY_MODE", "direct")

        # Clear cached modules
        import sys
        for mod in list(sys.modules.keys()):
            if 'somabrain.settings' in mod:
                del sys.modules[mod]

        from somabrain.memory.backends import get_memory_backend

        # This should raise ImportError because somafractalmemory is not properly installed
        with pytest.raises(ImportError) as exc_info:
            get_memory_backend(namespace="test")

        assert "somafractalmemory" in str(exc_info.value).lower()


class TestLazyImports:
    """Test that memory/__init__.py lazy imports work."""

    def test_lazy_get_memory_backend(self):
        """get_memory_backend should be available from main module."""
        from somabrain.memory import get_memory_backend
        assert callable(get_memory_backend)

    def test_lazy_is_aaas_mode(self):
        """is_aaas_mode should be available from main module."""
        from somabrain.memory import is_aaas_mode
        assert callable(is_aaas_mode)

    def test_lazy_get_memory_mode(self):
        """get_memory_mode should be available from main module."""
        from somabrain.memory import get_memory_mode
        assert callable(get_memory_mode)
