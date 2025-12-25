"""
Django models for somabrain.

Migrated from SQLAlchemy models - 100% Django ORM.
"""

from django.db import models
from django.utils import timezone


class OutboxEvent(models.Model):
    """
    Transactional outbox pattern for reliable event publishing.
    
    Migrated from: somabrain/db/models/outbox.py (SQLAlchemy)
    """
    
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    topic = models.CharField(max_length=255)
    payload = models.JSONField()
    status = models.CharField(max_length=50, default='pending', db_index=True)  # pending, sent, failed
    retries = models.IntegerField(default=0)
    dedupe_key = models.CharField(max_length=255)
    tenant_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    last_error = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'outbox_events'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant_id', 'dedupe_key'],
                name='uq_outbox_tenant_dedupe'
            )
        ]
        indexes = [
            models.Index(
                fields=['status', 'tenant_id', 'created_at'],
                name='ix_outbox_stt'  # status_tenant_time (shortened for 30 char limit)
            ),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"OutboxEvent(id={self.id}, topic='{self.topic}', status='{self.status}')"
    
    def __repr__(self):
        return self.__str__()


class EpisodicSnapshot(models.Model):
    """
    Episodic memory snapshots for long-term storage.
    
    Migrated from: somabrain/db/models/episodic.py (SQLAlchemy)
    """
    
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    tenant_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    namespace = models.CharField(max_length=255, null=True, blank=True)
    key = models.CharField(max_length=500)
    value = models.JSONField()
    tags = models.JSONField(null=True, blank=True)
    policy_tags = models.JSONField(null=True, blank=True)
    
    class Meta:
        db_table = 'episodic_snapshots'
        indexes = [
            models.Index(fields=['tenant_id', 'namespace', 'key']),
            models.Index(fields=['tenant_id', 'created_at']),
            models.Index(fields=['key']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"EpisodicSnapshot(id={self.id}, tenant_id={self.tenant_id}, key='{self.key}')"
    
    def __repr__(self):
        return self.__str__()


class SleepState(models.Model):
    """
    Sleep/consolidation system state tracking.
    
    Migrated from: somabrain/sleep/models.py (partial SQLAlchemy)
    """
    
    id = models.BigAutoField(primary_key=True)
    tenant_id = models.CharField(max_length=255, db_index=True)
    state = models.CharField(max_length=50)  # awake, nrem, rem, etc.
    timestamp = models.DateTimeField(auto_now=True)
    cycle_number = models.IntegerField(default=0)
    metadata = models.JSONField(null=True, blank=True)
    
    class Meta:
        db_table = 'sleep_states'
        indexes = [
            models.Index(fields=['tenant_id', 'timestamp']),
            models.Index(fields=['state']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"SleepState(tenant={self.tenant_id}, state={self.state})"


class CognitiveThread(models.Model):
    """
    Cognitive thread tracking for multi-threaded processing.
    
    Migrated from: somabrain/cognitive/thread_model.py (SQLAlchemy)
    """
    
    id = models.BigAutoField(primary_key=True)
    thread_id = models.CharField(max_length=255, unique=True, db_index=True)
    tenant_id = models.CharField(max_length=255, db_index=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=50, default='active')
    metadata = models.JSONField(null=True, blank=True)
    
    class Meta:
        db_table = 'cognitive_threads'
        indexes = [
            models.Index(fields=['tenant_id', 'status']),
            models.Index(fields=['thread_id']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"CognitiveThread(id={self.thread_id}, tenant={self.tenant_id})"


class TokenLedger(models.Model):
    """
    Token usage tracking and quotas.
    
    Migrated from: somabrain/storage/token_ledger.py (SQLAlchemy)
    """
    
    id = models.BigAutoField(primary_key=True)
    tenant_id = models.CharField(max_length=255, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    tokens_used = models.IntegerField(default=0)
    endpoint = models.CharField(max_length=255, null=True, blank=True)
    operation = models.CharField(max_length=100, null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    
    class Meta:
        db_table = 'token_ledger'
        indexes = [
            models.Index(fields=['tenant_id', 'timestamp']),
            models.Index(fields=['endpoint']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"TokenLedger(tenant={self.tenant_id}, tokens={self.tokens_used})"


class FeedbackRecord(models.Model):
    """
    User feedback and ratings storage.
    
    Migrated from: somabrain/storage/feedback.py (SQLAlchemy)
    """
    
    id = models.BigAutoField(primary_key=True)
    feedback_id = models.CharField(max_length=255, unique=True, db_index=True)
    tenant_id = models.CharField(max_length=255, db_index=True)
    content = models.TextField()
    rating = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    feedback_type = models.CharField(max_length=100, null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    
    class Meta:
        db_table = 'feedback_records'
        indexes = [
            models.Index(fields=['tenant_id', 'timestamp']),
            models.Index(fields=['feedback_type']),
            models.Index(fields=['rating']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"FeedbackRecord(id={self.feedback_id}, tenant={self.tenant_id}, rating={self.rating})"


class ConstitutionVersion(models.Model):
    """
    Constitution document versions.
    
    Migrated from: somabrain/constitution/storage.py (SQLAlchemy)
    """
    
    checksum = models.CharField(max_length=128, primary_key=True)
    document = models.JSONField()
    metadata = models.JSONField(null=True, blank=True, db_column='metadata')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'constitution_versions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', '-created_at']),
        ]
    
    def __str__(self):
        return f"ConstitutionVersion(checksum={self.checksum[:12]}, active={self.is_active})"


class ConstitutionSignature(models.Model):
    """
    Constitution signature records.
    
    Migrated from: somabrain/constitution/storage.py (SQLAlchemy)
    """
    
    id = models.CharField(max_length=256, primary_key=True)
    checksum = models.CharField(max_length=128, db_index=True)
    signer_id = models.CharField(max_length=128)
    signature = models.CharField(max_length=1024)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'constitution_signatures'
        constraints = [
            models.UniqueConstraint(
                fields=['checksum', 'signer_id'],
                name='uq_constitution_signature'
            )
        ]
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['checksum', 'created_at']),
        ]
    
    def __str__(self):
        return f"ConstitutionSignature(checksum={self.checksum[:12]}, signer={self.signer_id})"
