from rest_framework import serializers
from .models import Workflow, WorkflowSchedule


class WorkflowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workflow
        fields = ['id', 'name', 'description', 'nodes', 'edges', 'api_enabled', 'api_key', 'created_at', 'updated_at']
        read_only_fields = ['id', 'api_key', 'created_at', 'updated_at']


class WorkflowScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowSchedule
        fields = ['id', 'workflow', 'cron_node_id', 'cron_expression', 'timezone', 'is_active', 'last_run', 'next_run', 'created_at', 'updated_at']
        read_only_fields = ['id', 'last_run', 'next_run', 'created_at', 'updated_at']
