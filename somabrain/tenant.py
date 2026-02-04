"""
Tenant resolution facade.

This module re-exports functionality from somabrain.aaas.logic.tenant to maintain
compatibility with imports expecting `somabrain.tenant`.
"""

from somabrain.aaas.logic.tenant import TenantContext, get_tenant

__all__ = ["TenantContext", "get_tenant"]
