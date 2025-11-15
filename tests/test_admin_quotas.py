"""
Tests for quota management admin endpoints.

These tests verify that the admin endpoints for quota management work correctly,
including listing quotas, resetting quotas, and adjusting quota limits.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from datetime import datetime, timezone

from somabrain.schemas import (
    QuotaStatus,
    QuotaListResponse,
    QuotaResetRequest,
    QuotaResetResponse,
    QuotaAdjustRequest,
    QuotaAdjustResponse,
)
from somabrain.quotas import QuotaManager, QuotaConfig, QuotaInfo


class TestQuotaAdminEndpoints:
    """Test suite for quota admin endpoints."""

    @pytest.fixture
    def mock_quota_manager(self):
        """Mock QuotaManager for testing."""
        with patch('somabrain.quotas.QuotaManager') as mock:
            manager = Mock(spec=QuotaManager)
            
            # Mock get_all_quotas method
            quota_info1 = QuotaInfo(
                tenant_id="tenant1",
                daily_limit=10000,
                remaining=5000,
                used_today=5000,
                reset_at=datetime.now(timezone.utc),
                is_exempt=False
            )
            quota_info2 = QuotaInfo(
                tenant_id="AGENT_ZERO",
                daily_limit=10000,
                remaining=float("inf"),
                used_today=0,
                reset_at=datetime.now(timezone.utc),
                is_exempt=True
            )
            manager.get_all_quotas.return_value = [quota_info1, quota_info2]
            
            # Mock tenant_exists method
            manager.tenant_exists.return_value = True
            
            # Mock remaining method
            manager.remaining.return_value = 10000
            
            # Mock reset_quota method
            manager.reset_quota.return_value = True
            
            # Mock get_quota_info method
            manager.get_quota_info.return_value = quota_info1
            
            # Mock adjust_quota_limit method
            manager.adjust_quota_limit.return_value = True
            
            mock.return_value = manager
            yield manager

    @pytest.mark.asyncio
    async def test_admin_list_quotas_success(self, mock_quota_manager):
        """Test successful quota listing."""
        from somabrain.app import admin_list_quotas
        
        # Mock request
        request = Mock()
        
        # Call the endpoint
        response = await admin_list_quotas(request, limit=10, offset=0)
        
        # Verify response structure
        assert isinstance(response, QuotaListResponse)
        assert len(response.quotas) == 2
        assert response.total_tenants == 2
        
        # Verify first quota
        quota1 = response.quotas[0]
        assert quota1.tenant_id == "tenant1"
        assert quota1.daily_limit == 10000
        assert quota1.remaining == 5000
        assert quota1.used_today == 5000
        assert quota1.is_exempt == False
        
        # Verify second quota (exempt tenant)
        quota2 = response.quotas[1]
        assert quota2.tenant_id == "AGENT_ZERO"
        assert quota2.is_exempt == True
        assert quota2.remaining == float("inf")

    @pytest.mark.asyncio
    async def test_admin_list_quotas_with_filter(self, mock_quota_manager):
        """Test quota listing with tenant filter."""
        from somabrain.app import admin_list_quotas
        
        # Mock request
        request = Mock()
        
        # Call the endpoint with filter
        response = await admin_list_quotas(
            request, 
            limit=10, 
            offset=0, 
            tenant_filter="tenant1"
        )
        
        # Verify response
        assert isinstance(response, QuotaListResponse)
        assert len(response.quotas) == 1
        assert response.quotas[0].tenant_id == "tenant1"

    @pytest.mark.asyncio
    async def test_admin_reset_quota_success(self, mock_quota_manager):
        """Test successful quota reset."""
        from somabrain.app import admin_reset_quota
        
        # Mock request
        request = Mock()
        
        # Create reset request
        reset_request = QuotaResetRequest(reason="Test reset")
        
        # Call the endpoint
        response = await admin_reset_quota("tenant1", reset_request)
        
        # Verify response
        assert isinstance(response, QuotaResetResponse)
        assert response.tenant_id == "tenant1"
        assert response.reset == True
        assert response.new_remaining == 10000
        assert "Quota reset for tenant tenant1" in response.message
        
        # Verify quota_manager.reset_quota was called
        mock_quota_manager.reset_quota.assert_called_once_with("tenant1")

    @pytest.mark.asyncio
    async def test_admin_reset_quota_tenant_not_found(self, mock_quota_manager):
        """Test quota reset for non-existent tenant."""
        from somabrain.app import admin_reset_quota
        
        # Mock request
        request = Mock()
        
        # Configure mock to return False for tenant_exists
        mock_quota_manager.tenant_exists.return_value = False
        mock_quota_manager._is_exempt.return_value = False
        
        # Create reset request
        reset_request = QuotaResetRequest(reason="Test reset")
        
        # Call the endpoint and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await admin_reset_quota("nonexistent", reset_request)
        
        assert exc_info.value.status_code == 404
        assert "Tenant nonexistent not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_admin_adjust_quota_success(self, mock_quota_manager):
        """Test successful quota limit adjustment."""
        from somabrain.app import admin_adjust_quota
        
        # Mock request
        request = Mock()
        
        # Create adjust request
        adjust_request = QuotaAdjustRequest(new_limit=20000, reason="Increase limit")
        
        # Call the endpoint
        response = await admin_adjust_quota("tenant1", adjust_request)
        
        # Verify response
        assert isinstance(response, QuotaAdjustResponse)
        assert response.tenant_id == "tenant1"
        assert response.old_limit == 10000
        assert response.new_limit == 20000
        assert response.adjusted == True
        assert "Quota limit adjusted for tenant tenant1" in response.message
        
        # Verify quota_manager.adjust_quota_limit was called
        mock_quota_manager.adjust_quota_limit.assert_called_once_with("tenant1", 20000)

    @pytest.mark.asyncio
    async def test_admin_adjust_quota_tenant_not_found(self, mock_quota_manager):
        """Test quota adjustment for non-existent tenant."""
        from somabrain.app import admin_adjust_quota
        
        # Mock request
        request = Mock()
        
        # Configure mock to return False for tenant_exists
        mock_quota_manager.tenant_exists.return_value = False
        mock_quota_manager._is_exempt.return_value = False
        
        # Create adjust request
        adjust_request = QuotaAdjustRequest(new_limit=20000, reason="Increase limit")
        
        # Call the endpoint and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await admin_adjust_quota("nonexistent", adjust_request)
        
        assert exc_info.value.status_code == 404
        assert "Tenant nonexistent not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_admin_adjust_quota_invalid_limit(self, mock_quota_manager):
        """Test quota adjustment with invalid limit."""
        from somabrain.app import admin_adjust_quota
        
        # Mock request
        request = Mock()
        
        # Configure mock to return False for adjust_quota_limit (invalid limit)
        mock_quota_manager.adjust_quota_limit.return_value = False
        
        # Create adjust request with invalid limit
        adjust_request = QuotaAdjustRequest(new_limit=-1, reason="Invalid limit")
        
        # Call the endpoint and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await admin_adjust_quota("tenant1", adjust_request)
        
        assert exc_info.value.status_code == 500
        assert "Failed to adjust quota" in exc_info.value.detail


class TestQuotaManagerExtensions:
    """Test suite for QuotaManager extension methods."""

    def test_tenant_exists_existing(self):
        """Test tenant_exists for existing tenant."""
        manager = QuotaManager(QuotaConfig())
        
        # Add a quota record
        manager._counts["test_tenant"] = (manager._day_key(), 5)
        
        assert manager.tenant_exists("test_tenant") == True

    def test_tenant_exists_exempt(self):
        """Test tenant_exists for exempt tenant."""
        manager = QuotaManager(QuotaConfig())
        
        # AGENT_ZERO should exist even without records
        assert manager.tenant_exists("AGENT_ZERO") == True

    def test_tenant_exists_nonexistent(self):
        """Test tenant_exists for non-existent tenant."""
        manager = QuotaManager(QuotaConfig())
        
        assert manager.tenant_exists("nonexistent") == False

    def test_get_quota_info(self):
        """Test get_quota_info method."""
        manager = QuotaManager(QuotaConfig(daily_writes=1000))
        
        # Add a quota record
        day = manager._day_key()
        manager._counts["test_tenant"] = (day, 300)
        
        # Get quota info
        info = manager.get_quota_info("test_tenant")
        
        assert info.tenant_id == "test_tenant"
        assert info.daily_limit == 1000
        assert info.remaining == 700
        assert info.used_today == 300
        assert info.is_exempt == False
        assert info.reset_at is not None

    def test_get_quota_info_exempt(self):
        """Test get_quota_info for exempt tenant."""
        manager = QuotaManager(QuotaConfig())
        
        # Get quota info for exempt tenant
        info = manager.get_quota_info("AGENT_ZERO")
        
        assert info.tenant_id == "AGENT_ZERO"
        assert info.is_exempt == True
        assert info.remaining == float("inf")

    def test_get_all_quotas(self):
        """Test get_all_quotas method."""
        manager = QuotaManager(QuotaConfig(daily_writes=1000))
        
        # Add multiple quota records
        day = manager._day_key()
        manager._counts["tenant1"] = (day, 100)
        manager._counts["tenant2"] = (day, 200)
        
        # Get all quotas
        quotas = manager.get_all_quotas()
        
        assert len(quotas) == 2
        tenant_ids = {q.tenant_id for q in quotas}
        assert tenant_ids == {"tenant1", "tenant2"}

    def test_reset_quota(self):
        """Test reset_quota method."""
        manager = QuotaManager(QuotaConfig(daily_writes=1000))
        
        # Add a quota record
        day = manager._day_key()
        manager._counts["test_tenant"] = (day, 500)
        
        # Reset quota
        result = manager.reset_quota("test_tenant")
        
        assert result == True
        assert manager._counts["test_tenant"] == (day, 0)

    def test_reset_quota_nonexistent(self):
        """Test reset_quota for non-existent tenant."""
        manager = QuotaManager(QuotaConfig())
        
        # Reset quota for non-existent tenant
        result = manager.reset_quota("nonexistent")
        
        assert result == False

    def test_adjust_quota_limit(self):
        """Test adjust_quota_limit method."""
        manager = QuotaManager(QuotaConfig(daily_writes=1000))
        
        # Adjust quota limit
        result = manager.adjust_quota_limit("test_tenant", 2000)
        
        assert result == True
        assert manager.cfg.daily_writes == 2000

    def test_adjust_quota_limit_invalid(self):
        """Test adjust_quota_limit with invalid limit."""
        manager = QuotaManager(QuotaConfig())
        
        # Adjust quota limit with invalid value
        result = manager.adjust_quota_limit("test_tenant", -1)
        
        assert result == False
        assert manager.cfg.daily_writes == 10000  # Should remain unchanged