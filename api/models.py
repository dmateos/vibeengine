from django.db import models


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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name
