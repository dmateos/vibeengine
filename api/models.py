from django.db import models
from django.contrib.auth.models import User
import secrets


class MemoryEntry(models.Model):
    """Key-value memory persisted in the Django database.

    Keys are stored as (namespace, key) to avoid collisions. Value is JSON.
    """
    namespace = models.CharField(max_length=128, default='default')
    key = models.CharField(max_length=256)
    value = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["namespace", "key"], name="uniq_memory_namespace_key"),
        ]
        indexes = [
            models.Index(fields=["namespace", "key"], name="idx_memory_ns_key"),
        ]

    def __str__(self) -> str:
        return f"{self.namespace}:{self.key}"


class Workflow(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workflows')
    nodes = models.JSONField(default=list)
    edges = models.JSONField(default=list)
    api_enabled = models.BooleanField(default=False)
    api_key = models.CharField(max_length=64, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name

    def generate_api_key(self):
        """Generate a new API key for this workflow."""
        self.api_key = f"wf_{secrets.token_urlsafe(32)}"
        return self.api_key


class WorkflowExecution(models.Model):
    """Record of a workflow execution."""
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='executions')
    execution_id = models.CharField(max_length=64, unique=True, db_index=True)
    input_data = models.TextField()
    final_output = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, default='running')  # running/completed/error
    trace = models.JSONField(default=list)
    error_message = models.TextField(blank=True, default='')
    execution_time = models.FloatField(null=True, blank=True)  # seconds
    triggered_by = models.CharField(max_length=20, default='manual')  # manual/api/scheduled
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workflow', '-created_at']),
            models.Index(fields=['execution_id']),
        ]

    def __str__(self):
        return f"{self.workflow.name} - {self.execution_id[:8]} - {self.status}"
