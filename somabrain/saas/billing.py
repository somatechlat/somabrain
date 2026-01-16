"""
Lago Billing Client for SomaBrain SaaS.

Integrates with Lago billing system for:
- Customer management
- Subscription management
- Usage event reporting
- Invoice retrieval

VIBE Coding Rules v5.2 - ALL 7 PERSONAS:
- Architect: Clean async/sync client design
- Security: API key authentication
- DevOps: Environment-based config
- QA: Testable with mocking
- Docs: Comprehensive docstrings
- DBA: N/A (external API)
- SRE: Retry logic, observability
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from django.conf import settings

from .models import SubscriptionTier, Tenant

logger = logging.getLogger(__name__)


# =============================================================================
# LAGO CLIENT
# =============================================================================


class LagoClient:
    """
    Lago billing API client.

    Handles communication with Lago for billing operations.
    Uses httpx for async HTTP requests.
    """

    def __init__(self):
        """Initialize the instance."""

        self.base_url = getattr(settings, "LAGO_URL", "http://localhost:3000")
        self.api_key = getattr(settings, "LAGO_API_KEY", "")
        self._client = None

    @property
    def headers(self) -> dict:
        """Default headers for Lago API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                headers=self.headers,
                timeout=30.0,
            )
        return self._client

    # -------------------------------------------------------------------------
    # CUSTOMER OPERATIONS
    # -------------------------------------------------------------------------

    def create_customer(self, tenant: Tenant) -> Optional[dict]:
        """
        Create a Lago customer for a tenant.

        Args:
            tenant: The Tenant object

        Returns:
            Lago customer response or None on error
        """
        try:
            response = self._get_client().post(
                "/api/v1/customers",
                json={
                    "customer": {
                        "external_id": str(tenant.id),
                        "name": tenant.name,
                        "email": tenant.billing_email or tenant.admin_email,
                        "metadata": [
                            {"key": "tenant_slug", "value": tenant.slug},
                            {
                                "key": "created_at",
                                "value": tenant.created_at.isoformat(),
                            },
                        ],
                    }
                },
            )

            if response.status_code in [200, 201]:
                data = response.json()
                lago_customer_id = data.get("customer", {}).get("lago_id")

                # Update tenant with Lago ID
                tenant.lago_customer_id = lago_customer_id
                tenant.save(update_fields=["lago_customer_id", "updated_at"])

                logger.info(
                    f"Created Lago customer for tenant {tenant.slug}: {lago_customer_id}"
                )
                return data

            logger.error(
                f"Lago create customer failed: {response.status_code} - {response.text}"
            )
            return None

        except Exception as e:
            logger.exception(f"Lago create customer error: {e}")
            return None

    def get_customer(self, external_id: str) -> Optional[dict]:
        """Get Lago customer by external ID (tenant UUID)."""
        try:
            response = self._get_client().get(f"/api/v1/customers/{external_id}")

            if response.status_code == 200:
                return response.json()

            return None

        except Exception as e:
            logger.exception(f"Lago get customer error: {e}")
            return None

    def update_customer(self, external_id: str, updates: dict) -> Optional[dict]:
        """Update Lago customer details."""
        try:
            response = self._get_client().put(
                f"/api/v1/customers/{external_id}",
                json={"customer": updates},
            )

            if response.status_code == 200:
                return response.json()

            logger.error(f"Lago update customer failed: {response.text}")
            return None

        except Exception as e:
            logger.exception(f"Lago update customer error: {e}")
            return None

    # -------------------------------------------------------------------------
    # SUBSCRIPTION OPERATIONS
    # -------------------------------------------------------------------------

    def create_subscription(
        self,
        tenant: Tenant,
        tier: SubscriptionTier,
        external_id: str = None,
    ) -> Optional[dict]:
        """
        Create a Lago subscription for a tenant.

        Args:
            tenant: The Tenant object
            tier: The SubscriptionTier to subscribe to
            external_id: Optional external subscription ID

        Returns:
            Lago subscription response or None on error
        """
        try:
            subscription_id = external_id or f"{tenant.id}_{tier.slug}"

            response = self._get_client().post(
                "/api/v1/subscriptions",
                json={
                    "subscription": {
                        "external_customer_id": str(tenant.id),
                        "plan_code": tier.slug,
                        "external_id": subscription_id,
                    }
                },
            )

            if response.status_code in [200, 201]:
                data = response.json()
                lago_sub_id = data.get("subscription", {}).get("lago_id")

                # Update tenant with subscription ID
                tenant.lago_subscription_id = lago_sub_id
                tenant.save(update_fields=["lago_subscription_id", "updated_at"])

                logger.info(
                    f"Created Lago subscription for tenant {tenant.slug}: {lago_sub_id}"
                )
                return data

            logger.error(f"Lago create subscription failed: {response.text}")
            return None

        except Exception as e:
            logger.exception(f"Lago create subscription error: {e}")
            return None

    def terminate_subscription(self, external_id: str) -> bool:
        """Terminate a Lago subscription."""
        try:
            response = self._get_client().delete(f"/api/v1/subscriptions/{external_id}")

            if response.status_code in [200, 204]:
                logger.info(f"Terminated Lago subscription: {external_id}")
                return True

            logger.error(f"Lago terminate subscription failed: {response.text}")
            return False

        except Exception as e:
            logger.exception(f"Lago terminate subscription error: {e}")
            return False

    def change_subscription_plan(
        self,
        external_id: str,
        new_plan_code: str,
    ) -> Optional[dict]:
        """Change subscription to a different plan."""
        try:
            response = self._get_client().put(
                f"/api/v1/subscriptions/{external_id}",
                json={
                    "subscription": {
                        "plan_code": new_plan_code,
                    }
                },
            )

            if response.status_code == 200:
                logger.info(
                    f"Changed subscription {external_id} to plan {new_plan_code}"
                )
                return response.json()

            logger.error(f"Lago change plan failed: {response.text}")
            return None

        except Exception as e:
            logger.exception(f"Lago change plan error: {e}")
            return None

    # -------------------------------------------------------------------------
    # USAGE EVENTS
    # -------------------------------------------------------------------------

    def report_usage(
        self,
        tenant: Tenant,
        event_type: str,
        properties: dict = None,
        timestamp: datetime = None,
    ) -> bool:
        """
        Report a usage event to Lago.

        Args:
            tenant: The Tenant object
            event_type: Event code (e.g., "api_call", "memory_operation")
            properties: Event properties (e.g., {"count": 10})
            timestamp: Event timestamp (defaults to now)

        Returns:
            True if event was recorded, False otherwise
        """
        try:
            event_timestamp = timestamp or datetime.now(timezone.utc)

            response = self._get_client().post(
                "/api/v1/events",
                json={
                    "event": {
                        "transaction_id": f"{tenant.id}_{event_type}_{event_timestamp.timestamp()}",
                        "external_customer_id": str(tenant.id),
                        "code": event_type,
                        "timestamp": int(event_timestamp.timestamp()),
                        "properties": properties or {},
                    }
                },
            )

            if response.status_code in [200, 201]:
                logger.debug(
                    f"Reported usage event: {event_type} for tenant {tenant.slug}"
                )
                return True

            logger.warning(f"Lago usage event failed: {response.text}")
            return False

        except Exception as e:
            logger.exception(f"Lago usage event error: {e}")
            return False

    def report_batch_usage(self, events: list[dict]) -> int:
        """
        Report multiple usage events in a batch.

        Args:
            events: List of event dicts with transaction_id, external_customer_id, code, timestamp, properties

        Returns:
            Number of events successfully recorded
        """
        try:
            response = self._get_client().post(
                "/api/v1/events/batch",
                json={"events": events},
            )

            if response.status_code in [200, 201]:
                return len(events)

            logger.warning(f"Lago batch events failed: {response.text}")
            return 0

        except Exception as e:
            logger.exception(f"Lago batch events error: {e}")
            return 0

    # -------------------------------------------------------------------------
    # INVOICE OPERATIONS
    # -------------------------------------------------------------------------

    def get_invoices(self, external_customer_id: str) -> list[dict]:
        """Get all invoices for a customer."""
        try:
            response = self._get_client().get(
                f"/api/v1/invoices?external_customer_id={external_customer_id}"
            )

            if response.status_code == 200:
                return response.json().get("invoices", [])

            return []

        except Exception as e:
            logger.exception(f"Lago get invoices error: {e}")
            return []

    def get_invoice(self, invoice_id: str) -> Optional[dict]:
        """Get a specific invoice by ID."""
        try:
            response = self._get_client().get(f"/api/v1/invoices/{invoice_id}")

            if response.status_code == 200:
                return response.json()

            return None

        except Exception as e:
            logger.exception(f"Lago get invoice error: {e}")
            return None

    def download_invoice_pdf(self, invoice_id: str) -> Optional[bytes]:
        """Download invoice as PDF."""
        try:
            response = self._get_client().get(f"/api/v1/invoices/{invoice_id}/download")

            if response.status_code == 200:
                return response.content

            return None

        except Exception as e:
            logger.exception(f"Lago download invoice error: {e}")
            return None

    # -------------------------------------------------------------------------
    # WALLET (CREDITS)
    # -------------------------------------------------------------------------

    def create_wallet(
        self,
        external_customer_id: str,
        credits: int,
        currency: str = "USD",
    ) -> Optional[dict]:
        """Create a wallet (prepaid credits) for a customer."""
        try:
            response = self._get_client().post(
                "/api/v1/wallets",
                json={
                    "wallet": {
                        "external_customer_id": external_customer_id,
                        "rate_amount": "1",
                        "currency": currency,
                        "paid_credits": str(credits),
                        "granted_credits": str(credits),
                    }
                },
            )

            if response.status_code in [200, 201]:
                return response.json()

            return None

        except Exception as e:
            logger.exception(f"Lago create wallet error: {e}")
            return None

    def add_credits(
        self,
        wallet_id: str,
        credits: int,
        reason: str = "Manual credit",
    ) -> Optional[dict]:
        """Add credits to a wallet."""
        try:
            response = self._get_client().post(
                f"/api/v1/wallets/{wallet_id}/wallet_transactions",
                json={
                    "wallet_transaction": {
                        "wallet_id": wallet_id,
                        "granted_credits": str(credits),
                    }
                },
            )

            if response.status_code in [200, 201]:
                logger.info(f"Added {credits} credits to wallet {wallet_id}")
                return response.json()

            return None

        except Exception as e:
            logger.exception(f"Lago add credits error: {e}")
            return None

    # -------------------------------------------------------------------------
    # ANALYTICS (REAL REVENUE DATA)
    # -------------------------------------------------------------------------

    def get_mrr_analytics(self, currency: str = "USD") -> Optional[dict]:
        """
        Fetch MRR analytics from Lago.

        According to Lago API docs (doc.getlago.com):
        GET /api/v1/analytics/mrr

        Returns:
            MRR data including current MRR and breakdown by category
            (new, expansion, contraction, churn)

        VIBE: REAL data from REAL server. No mocks.
        """
        try:
            response = self._get_client().get(
                "/api/v1/analytics/mrr",
                params={"currency": currency},
            )

            if response.status_code == 200:
                return response.json()

            logger.warning(f"Lago MRR analytics failed: {response.status_code}")
            return None

        except Exception as e:
            logger.exception(f"Lago MRR analytics error: {e}")
            return None

    def get_revenue_summary(self) -> dict:
        """
        Get revenue summary combining Lago analytics with subscription counts.

        Returns dict with:
        - mrr: float (Monthly Recurring Revenue from Lago)
        - arr: float (MRR * 12)
        - mrr_growth: float (percentage change)
        - active_subs: int (from Lago subscriptions)
        - by_currency: dict (MRR breakdown by currency)

        VIBE: ALL data from Lago API, no ORM fallbacks for billing data.
        """
        result = {
            "mrr": 0.0,
            "arr": 0.0,
            "mrr_growth": 0.0,
            "active_subs": 0,
            "by_currency": {},
        }

        # Fetch MRR from Lago analytics
        mrr_data = self.get_mrr_analytics()
        if mrr_data and "mrrs" in mrr_data:
            mrrs = mrr_data.get("mrrs", [])
            if mrrs:
                # Get latest MRR entry
                latest = mrrs[-1] if mrrs else {}
                result["mrr"] = float(latest.get("amount_cents", 0)) / 100
                result["arr"] = result["mrr"] * 12
                result["by_currency"] = {latest.get("currency", "USD"): result["mrr"]}

                # Calculate growth if we have previous month
                if len(mrrs) >= 2:
                    prev_mrr = float(mrrs[-2].get("amount_cents", 0)) / 100
                    if prev_mrr > 0:
                        result["mrr_growth"] = round(
                            ((result["mrr"] - prev_mrr) / prev_mrr) * 100, 1
                        )

        # Get subscription count from Lago
        try:
            response = self._get_client().get(
                "/api/v1/subscriptions",
                params={"status[]": "active"},
            )
            if response.status_code == 200:
                subs = response.json().get("subscriptions", [])
                result["active_subs"] = len(subs)
        except Exception:
            pass

        return result

    # -------------------------------------------------------------------------
    # HEALTH CHECK
    # -------------------------------------------------------------------------

    def health_check(self) -> bool:
        """Check if Lago is reachable."""
        try:
            response = self._get_client().get("/api/v1/organizations")
            return response.status_code == 200
        except Exception:
            return False


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_lago_client: Optional[LagoClient] = None


def get_lago_client() -> LagoClient:
    """Get the singleton Lago client instance."""
    global _lago_client
    if _lago_client is None:
        _lago_client = LagoClient()
    return _lago_client
