from rest_framework import serializers
from .models import Workflow


class WorkflowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workflow
        fields = ['id', 'name', 'description', 'nodes', 'edges', 'api_enabled', 'api_key', 'created_at', 'updated_at']
        read_only_fields = ['id', 'api_key', 'created_at', 'updated_at']
