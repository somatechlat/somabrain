"""
Tests for QuotaManager extension methods.

These tests verify that the new QuotaManager methods work correctly
without requiring full app initialization.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from somabrain.quotas import QuotaManager, QuotaConfig, QuotaInfo


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

    def test_tenant_exists_case_insensitive_exempt(self):
        """Test tenant_exists for exempt tenant with different cases."""
        manager = QuotaManager(QuotaConfig())
        
        # Various forms of AGENT_ZERO should all exist
        assert manager.tenant_exists("agent_zero") == True
        assert manager.tenant_exists("Agent_Zero") == True
        assert manager.tenant_exists("AGENT ZERO") == True
        assert manager.tenant_exists("agent zero") == True

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
        assert isinstance(info.reset_at, datetime)

    def test_get_quota_info_exempt(self):
        """Test get_quota_info for exempt tenant."""
        manager = QuotaManager(QuotaConfig())
        
        # Get quota info for exempt tenant
        info = manager.get_quota_info("AGENT_ZERO")
        
        assert info.tenant_id == "AGENT_ZERO"
        assert info.is_exempt == True
        assert info.remaining == float("inf")
        assert info.used_today == 0

    def test_get_quota_info_new_tenant(self):
        """Test get_quota_info for tenant with no existing records."""
        manager = QuotaManager(QuotaConfig(daily_writes=500))
        
        # Get quota info for new tenant
        info = manager.get_quota_info("new_tenant")
        
        assert info.tenant_id == "new_tenant"
        assert info.daily_limit == 500
        assert info.remaining == 500
        assert info.used_today == 0
        assert info.is_exempt == False

    def test_get_all_quotas(self):
        """Test get_all_quotas method."""
        manager = QuotaManager(QuotaConfig(daily_writes=1000))
        
        # Add multiple quota records
        day = manager._day_key()
        manager._counts["tenant1"] = (day, 100)
        manager._counts["tenant2"] = (day, 200)
        manager._counts["tenant3"] = (day, 50)
        
        # Get all quotas
        quotas = manager.get_all_quotas()
        
        assert len(quotas) == 3
        tenant_ids = {q.tenant_id for q in quotas}
        assert tenant_ids == {"tenant1", "tenant2", "tenant3"}
        
        # Verify quota details
        for quota in quotas:
            assert quota.daily_limit == 1000
            assert quota.remaining == 1000 - quota.used_today
            assert quota.reset_at is not None

    def test_get_all_quotas_empty(self):
        """Test get_all_quotas when no tenants exist."""
        manager = QuotaManager(QuotaConfig())
        
        # Get all quotas
        quotas = manager.get_all_quotas()
        
        assert len(quotas) == 0

    def test_reset_quota(self):
        """Test reset_quota method."""
        manager = QuotaManager(QuotaConfig(daily_writes=1000))
        
        # Add a quota record
        day = manager._day_key()
        manager._counts["test_tenant"] = (day, 500)
        
        # Verify initial state
        assert manager.remaining("test_tenant") == 500
        
        # Reset quota
        result = manager.reset_quota("test_tenant")
        
        assert result == True
        assert manager._counts["test_tenant"] == (day, 0)
        assert manager.remaining("test_tenant") == 1000

    def test_reset_quota_exempt(self):
        """Test reset_quota for exempt tenant."""
        manager = QuotaManager(QuotaConfig())
        
        # Reset quota for exempt tenant should work
        result = manager.reset_quota("AGENT_ZERO")
        
        assert result == True
        # Exempt tenants should still have infinite remaining
        assert manager.remaining("AGENT_ZERO") == float("inf")

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
        
        # Verify that existing quotas now use the new limit
        day = manager._day_key()
        manager._counts["test_tenant"] = (day, 500)
        assert manager.remaining("test_tenant") == 1500  # 2000 - 500

    def test_adjust_quota_limit_invalid(self):
        """Test adjust_quota_limit with invalid limit."""
        manager = QuotaManager(QuotaConfig(daily_writes=1000))
        
        # Adjust quota limit with invalid value
        result = manager.adjust_quota_limit("test_tenant", -1)
        
        assert result == False
        assert manager.cfg.daily_writes == 1000  # Should remain unchanged

    def test_adjust_quota_limit_zero(self):
        """Test adjust_quota_limit with zero limit."""
        manager = QuotaManager(QuotaConfig(daily_writes=1000))
        
        # Adjust quota limit to zero (should be invalid)
        result = manager.adjust_quota_limit("test_tenant", 0)
        
        assert result == False
        assert manager.cfg.daily_writes == 1000  # Should remain unchanged

    def test_quota_info_reset_at_future(self):
        """Test that reset_at is always in the future."""
        manager = QuotaManager(QuotaConfig())
        
        info = manager.get_quota_info("test_tenant")
        
        now = datetime.now(timezone.utc)
        assert info.reset_at > now
        
        # Should be approximately midnight tomorrow
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = tomorrow.replace(day=now.day + 1)
        assert abs((info.reset_at - tomorrow).total_seconds()) < 60  # Within 1 minute

    def test_quota_info_used_today_persistence(self):
        """Test that used_today reflects actual usage."""
        manager = QuotaManager(QuotaConfig(daily_writes=1000))
        
        # Simulate some quota usage
        manager.allow_write("test_tenant", 100)
        manager.allow_write("test_tenant", 200)
        
        info = manager.get_quota_info("test_tenant")
        assert info.used_today == 300
        assert info.remaining == 700

    def test_quota_info_day_boundary(self):
        """Test quota info across day boundaries."""
        manager = QuotaManager(QuotaConfig(daily_writes=1000))
        
        # Add usage for today
        day = manager._day_key()
        manager._counts["test_tenant"] = (day, 800)
        
        info = manager.get_quota_info("test_tenant")
        assert info.used_today == 800
        assert info.remaining == 200
        
        # Simulate previous day usage (should be ignored)
        old_day = day - 1
        manager._counts["old_tenant"] = (old_day, 500)
        
        old_info = manager.get_quota_info("old_tenant")
        assert old_info.used_today == 0  # Should reset to 0 for new day
        assert old_info.remaining == 1000