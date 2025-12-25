"""
Django admin configuration for somabrain models.
"""

from django.contrib import admin
from .models import (
    OutboxEvent,
    EpisodicSnapshot,
    SleepState,
    CognitiveThread,
    TokenLedger,
    FeedbackRecord,
)


@admin.register(OutboxEvent)
class OutboxEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'topic', 'status', 'tenant_id', 'created_at', 'retries')
    list_filter = ('status', 'topic', 'created_at')
    search_fields = ('topic', 'tenant_id', 'dedupe_key')
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'created_at'
    
    actions = ['mark_as_sent', 'mark_as_failed', 'retry_failed']
    
    def mark_as_sent(self, request, queryset):
        queryset.update(status='sent')
    mark_as_sent.short_description = "Mark selected as sent"
    
    def mark_as_failed(self, request, queryset):
        queryset.update(status='failed')
    mark_as_failed.short_description = "Mark selected as failed"
    
    def retry_failed(self, request, queryset):
        queryset.filter(status='failed').update(status='pending', retries=0)
    retry_failed.short_description = "Retry failed events"


@admin.register(EpisodicSnapshot)
class EpisodicSnapshotAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant_id', 'namespace', 'key', 'created_at')
    list_filter = ('namespace', 'created_at', 'tenant_id')
    search_fields = ('key', 'tenant_id', 'namespace')
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'created_at'


@admin.register(SleepState)
class SleepStateAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant_id', 'state', 'cycle_number', 'timestamp')
    list_filter = ('state', 'timestamp', 'tenant_id')
    search_fields = ('tenant_id',)
    readonly_fields = ('id', 'timestamp')
    date_hierarchy = 'timestamp'


@admin.register(CognitiveThread)
class CognitiveThreadAdmin(admin.ModelAdmin):
    list_display = ('thread_id', 'tenant_id', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at', 'tenant_id')
    search_fields = ('thread_id', 'tenant_id')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(TokenLedger)
class TokenLedgerAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant_id', 'tokens_used', 'endpoint', 'operation', 'timestamp')
    list_filter = ('endpoint', 'operation', 'timestamp', 'tenant_id')
    search_fields = ('tenant_id', 'endpoint')
    readonly_fields = ('id', 'timestamp')
    date_hierarchy = 'timestamp'


@admin.register(FeedbackRecord)
class FeedbackRecordAdmin(admin.ModelAdmin):
    list_display = ('feedback_id', 'tenant_id', 'feedback_type', 'rating', 'timestamp')
    list_filter = ('feedback_type', 'rating', 'timestamp', 'tenant_id')
    search_fields = ('feedback_id', 'tenant_id', 'content')
    readonly_fields = ('id', 'timestamp')
    date_hierarchy = 'timestamp'
