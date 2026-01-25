"""
AAAS Models - Audit Logging.

Immutable audit trail for all admin actions.
"""

from uuid import uuid4

from django.db import models

from .enums import ActorType


class AuditLog(models.Model):
    """Audit trail for all admin actions."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    tenant = models.ForeignKey(
        "Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    actor_id = models.CharField(max_length=255)
    actor_type = models.CharField(
        max_length=20, choices=ActorType.choices, default=ActorType.USER
    )
    actor_email = models.EmailField(null=True, blank=True)

    action = models.CharField(max_length=100, db_index=True)
    resource_type = models.CharField(max_length=100)
    resource_id = models.CharField(max_length=255)

    details = models.JSONField(default=dict, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    request_id = models.CharField(max_length=255, null=True, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        """Meta configuration."""

        db_table = "aaas_audit_log"
        ordering = ["-timestamp"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        indexes = [
            models.Index(fields=["tenant", "timestamp"]),
            models.Index(fields=["action", "timestamp"]),
            models.Index(fields=["actor_id", "timestamp"]),
            models.Index(fields=["resource_type", "resource_id"]),
        ]

    def __str__(self):
        """Return string representation."""
        return f"{self.action} by {self.actor_id} at {self.timestamp}"

    @classmethod
    def log(
        cls,
        action: str,
        resource_type: str,
        resource_id: str,
        actor_id: str,
        actor_type: str = ActorType.USER,
        tenant: "Tenant" = None,
        details: dict = None,
        ip_address: str = None,
        user_agent: str = None,
        request_id: str = None,
        actor_email: str = None,
    ) -> "AuditLog":
        """Create an audit log entry and publish to Kafka."""
        entry = cls.objects.create(
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            actor_id=str(actor_id),
            actor_type=actor_type,
            tenant=tenant,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            actor_email=actor_email,
        )

        try:
            from somabrain.audit import publish_event

            publish_event(
                {
                    "type": "aaas.audit",
                    "action": action,
                    "resource_type": resource_type,
                    "resource_id": str(resource_id),
                    "actor_id": str(actor_id),
                    "actor_type": actor_type,
                    "tenant_id": str(tenant.id) if tenant else None,
                    "details": details or {},
                    "timestamp": entry.timestamp.isoformat(),
                },
                topic="soma.aaas.audit",
            )
        except Exception:
            import logging

            logging.getLogger("somabrain.aaas.models").debug(
                "Kafka audit publish failed (ORM entry persisted)", exc_info=True
            )

        return entry
