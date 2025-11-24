from rest_framework import serializers
from .models import Workflow


class WorkflowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workflow
        fields = ['id', 'name', 'description', 'nodes', 'edges', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
