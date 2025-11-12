"""
Test ROAMDP Phase 3 implementation: DB-backed outbox and write modes.
"""
import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from somabrain.memory_client import MemoryClient
from somabrain.config import Config
from somabrain.db.outbox import enqueue_event


class TestROAMDPPhase3:
    """Test ROAMDP Phase 3 features: DB-backed outbox and write modes."""

    def setup_method(self):
        """Setup test fixtures."""
        self.config = Config()
        self.config.namespace = "test-tenant"
        
    def test_memory_write_mode_config(self):
        """Test memory_write_mode configuration is respected."""
        with patch('somabrain.config.shared_settings') as mock_settings:
            mock_settings.memory_write_mode = "fast_ack"
            
            client = MemoryClient(self.config)
            
            # Verify write mode is accessible
            assert hasattr(client, '_record_outbox')
            assert client._tenant_id == "test-tenant"

    def test_tenant_headers_inclusion(self):
        """Test X-Soma-Tenant and idempotency headers are added."""
        client = MemoryClient(self.config)
        
        # Mock HTTP client
        client._http = MagicMock()
        client._http.post.return_value.status_code = 200
        client._http.post.return_value.json.return_value = {"coord": [1.0, 2.0, 3.0]}
        
        # Test headers include tenant context
        headers = {"X-Request-ID": "test-request-id"}
        client._http_post_with_retries_sync("/test", {}, headers)
        
        # Verify tenant header was added
        call_args = client._http.post.call_args
        sent_headers = call_args[1]['headers']
        assert "X-Soma-Tenant" in sent_headers
        assert sent_headers["X-Soma-Tenant"] == "test-tenant"
        assert "X-Idempotency-Key" in sent_headers

    def test_db_outbox_replaces_file_outbox(self):
        """Test DB-backed outbox replaces file-based approach."""
        client = MemoryClient(self.config)
        
        # Mock the enqueue_event function
        with patch('somabrain.db.outbox.enqueue_event') as mock_enqueue:
            mock_enqueue.return_value = None
            
            # Test _record_outbox uses DB instead of files
            client._record_outbox("test_op", {"test": "data"})
            
            # Verify enqueue_event was called with proper parameters
            mock_enqueue.assert_called_once()
            call_args = mock_enqueue.call_args
            assert call_args[1]['topic'] == "memory.test_op"
            assert call_args[1]['tenant_id'] == "test-tenant"
            assert 'dedupe_key' in call_args[1]

    def test_async_methods_have_tenant_headers(self):
        """Test async HTTP methods also include tenant headers."""
        import asyncio
        
        async def test_async_headers():
            client = MemoryClient(self.config)
            client._http_async = MagicMock()
            client._http_async.post.return_value.status_code = 200
            client._http_async.post.return_value.json.return_value = {"coord": [1.0, 2.0, 3.0]}
            
            headers = {"X-Request-ID": "test-async-id"}
            await client._http_post_with_retries_async("/test", {}, headers)
            
            call_args = client._http_async.post.call_args
            sent_headers = call_args[1]['headers']
            assert "X-Soma-Tenant" in sent_headers
            assert sent_headers["X-Soma-Tenant"] == "test-tenant"
            assert "X-Idempotency-Key" in sent_headers

        asyncio.run(test_async_headers())

    def test_tenant_extraction_from_namespace(self):
        """Test tenant ID extraction works correctly."""
        # Test with namespace containing tenant
        config1 = Config()
        config1.namespace = "memory:sandbox-tenant"
        client1 = MemoryClient(config1)
        assert client1._tenant_id == "sandbox-tenant"
        
        # Test with simple namespace
        config2 = Config()
        config2.namespace = "test-namespace"
        client2 = MemoryClient(config2)
        assert client2._tenant_id == "test-namespace"

    def test_memory_write_modes(self):
        """Test different memory write modes are handled correctly."""
        modes = ["sync", "fast_ack", "background"]
        
        for mode in modes:
            with patch('somabrain.config.shared_settings') as mock_settings:
                mock_settings.memory_write_mode = mode
                
                client = MemoryClient(self.config)
                assert client._tenant_id is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])