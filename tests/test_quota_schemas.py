"""
Tests for quota management schemas.

These tests verify that the new quota schemas work correctly
for serialization and validation.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from somabrain.schemas import (
    QuotaStatus,
    QuotaListResponse,
    QuotaResetRequest,
    QuotaResetResponse,
    QuotaAdjustRequest,
    QuotaAdjustResponse,
)


class TestQuotaSchemas:
    """Test suite for quota schemas."""

    def test_quota_status_schema(self):
        """Test QuotaStatus schema validation and serialization."""
        # Create a valid quota status
        reset_time = datetime.now(timezone.utc)
        quota_status = QuotaStatus(
            tenant_id="test_tenant",
            daily_limit=10000,
            remaining=5000,
            used_today=5000,
            reset_at=reset_time,
            is_exempt=False
        )
        
        # Verify fields
        assert quota_status.tenant_id == "test_tenant"
        assert quota_status.daily_limit == 10000
        assert quota_status.remaining == 5000
        assert quota_status.used_today == 5000
        assert quota_status.reset_at == reset_time
        assert quota_status.is_exempt == False
        
        # Test serialization
        data = quota_status.model_dump()
        assert data["tenant_id"] == "test_tenant"
        assert data["daily_limit"] == 10000
        assert data["remaining"] == 5000
        assert data["used_today"] == 5000
        assert data["is_exempt"] == False

    def test_quota_status_exempt_tenant(self):
        """Test QuotaStatus for exempt tenant with infinite remaining."""
        quota_status = QuotaStatus(
            tenant_id="AGENT_ZERO",
            daily_limit=10000,
            remaining=float("inf"),
            used_today=0,
            is_exempt=True
        )
        
        assert quota_status.tenant_id == "AGENT_ZERO"
        assert quota_status.remaining == float("inf")
        assert quota_status.is_exempt == True
        assert quota_status.used_today == 0

    def test_quota_list_response_schema(self):
        """Test QuotaListResponse schema."""
        # Create quota statuses
        quota1 = QuotaStatus(
            tenant_id="tenant1",
            daily_limit=10000,
            remaining=8000,
            used_today=2000,
            is_exempt=False
        )
        quota2 = QuotaStatus(
            tenant_id="AGENT_ZERO",
            daily_limit=10000,
            remaining=float("inf"),
            used_today=0,
            is_exempt=True
        )
        
        # Create list response
        response = QuotaListResponse(
            quotas=[quota1, quota2],
            total_tenants=2
        )
        
        # Verify fields
        assert len(response.quotas) == 2
        assert response.total_tenants == 2
        assert response.quotas[0].tenant_id == "tenant1"
        assert response.quotas[1].tenant_id == "AGENT_ZERO"
        
        # Test serialization
        data = response.model_dump()
        assert len(data["quotas"]) == 2
        assert data["total_tenants"] == 2

    def test_quota_reset_request_schema(self):
        """Test QuotaResetRequest schema."""
        # Test with reason
        request = QuotaResetRequest(reason="Test quota reset")
        assert request.reason == "Test quota reset"
        
        # Test without reason (optional field)
        request2 = QuotaResetRequest()
        assert request2.reason is None
        
        # Test serialization
        data = request.model_dump()
        assert data["reason"] == "Test quota reset"

    def test_quota_reset_response_schema(self):
        """Test QuotaResetResponse schema."""
        response = QuotaResetResponse(
            tenant_id="test_tenant",
            reset=True,
            new_remaining=10000,
            message="Quota reset successfully"
        )
        
        assert response.tenant_id == "test_tenant"
        assert response.reset == True
        assert response.new_remaining == 10000
        assert response.message == "Quota reset successfully"
        
        # Test serialization
        data = response.model_dump()
        assert data["tenant_id"] == "test_tenant"
        assert data["reset"] == True
        assert data["new_remaining"] == 10000
        assert data["message"] == "Quota reset successfully"

    def test_quota_adjust_request_schema(self):
        """Test QuotaAdjustRequest schema validation."""
        # Valid request
        request = QuotaAdjustRequest(new_limit=20000, reason="Increase quota")
        assert request.new_limit == 20000
        assert request.reason == "Increase quota"
        
        # Valid request without reason
        request2 = QuotaAdjustRequest(new_limit=15000)
        assert request2.new_limit == 15000
        assert request2.reason is None
        
        # Test validation - new_limit must be positive
        with pytest.raises(ValidationError):
            QuotaAdjustRequest(new_limit=0)
        
        with pytest.raises(ValidationError):
            QuotaAdjustRequest(new_limit=-100)

    def test_quota_adjust_response_schema(self):
        """Test QuotaAdjustResponse schema."""
        response = QuotaAdjustResponse(
            tenant_id="test_tenant",
            old_limit=10000,
            new_limit=20000,
            adjusted=True,
            message="Quota limit adjusted from 10000 to 20000"
        )
        
        assert response.tenant_id == "test_tenant"
        assert response.old_limit == 10000
        assert response.new_limit == 20000
        assert response.adjusted == True
        assert response.message == "Quota limit adjusted from 10000 to 20000"
        
        # Test serialization
        data = response.model_dump()
        assert data["tenant_id"] == "test_tenant"
        assert data["old_limit"] == 10000
        assert data["new_limit"] == 20000
        assert data["adjusted"] == True

    def test_quota_status_validation(self):
        """Test QuotaStatus field validation."""
        # Valid minimum data
        quota = QuotaStatus(
            tenant_id="test",
            daily_limit=1000,
            remaining=500,
            used_today=500
        )
        assert quota.tenant_id == "test"
        assert quota.reset_at is None  # Optional field
        assert quota.is_exempt == False  # Default value

    def test_quota_list_response_empty(self):
        """Test QuotaListResponse with empty quotas."""
        response = QuotaListResponse(quotas=[], total_tenants=0)
        assert len(response.quotas) == 0
        assert response.total_tenants == 0

    def test_schema_json_serialization(self):
        """Test JSON serialization of all quota schemas."""
        # QuotaStatus
        quota_status = QuotaStatus(
            tenant_id="test",
            daily_limit=1000,
            remaining=500,
            used_today=500,
            is_exempt=True
        )
        json_str = quota_status.model_dump_json()
        assert "tenant_id" in json_str
        assert "is_exempt" in json_str
        
        # QuotaListResponse
        list_response = QuotaListResponse(quotas=[quota_status], total_tenants=1)
        json_str = list_response.model_dump_json()
        assert "quotas" in json_str
        assert "total_tenants" in json_str
        
        # QuotaAdjustRequest
        adjust_request = QuotaAdjustRequest(new_limit=2000)
        json_str = adjust_request.model_dump_json()
        assert "new_limit" in json_str
        
        # QuotaResetResponse
        reset_response = QuotaResetResponse(
            tenant_id="test",
            reset=True,
            new_remaining=1000,
            message="Reset complete"
        )
        json_str = reset_response.model_dump_json()
        assert "tenant_id" in json_str
        assert "reset" in json_str