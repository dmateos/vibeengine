from django.db import models
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
