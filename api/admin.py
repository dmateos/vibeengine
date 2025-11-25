from django.contrib import admin
from .models import Workflow, MemoryEntry, WorkflowExecution


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('name', 'node_count', 'edge_count', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-updated_at',)

    def node_count(self, obj):
        return len(obj.nodes) if obj.nodes else 0
    node_count.short_description = 'Nodes'

    def edge_count(self, obj):
        return len(obj.edges) if obj.edges else 0
    edge_count.short_description = 'Edges'


@admin.register(MemoryEntry)
class MemoryEntryAdmin(admin.ModelAdmin):
    list_display = ('namespace', 'key', 'short_value', 'updated_at')
    list_filter = ('namespace', 'updated_at')
    search_fields = ('namespace', 'key')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('namespace', 'key')

    def short_value(self, obj):
        import json
        try:
            s = json.dumps(obj.value, ensure_ascii=False)
        except Exception:
            s = str(obj.value)
        return (s[:80] + '…') if s and len(s) > 80 else s
    short_value.short_description = 'Value'


@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    list_display = ('short_execution_id', 'workflow', 'status', 'short_input', 'short_output', 'execution_time', 'triggered_by', 'created_at')
    list_filter = ('status', 'triggered_by', 'workflow', 'created_at')
    search_fields = ('execution_id', 'input_data', 'final_output', 'error_message')
    readonly_fields = ('workflow', 'execution_id', 'input_data', 'final_output', 'status', 'trace', 'error_message', 'execution_time', 'triggered_by', 'created_at')
    ordering = ('-created_at',)

    def short_execution_id(self, obj):
        return obj.execution_id[:8] + '...'
    short_execution_id.short_description = 'Execution ID'

    def short_input(self, obj):
        return (obj.input_data[:50] + '…') if obj.input_data and len(obj.input_data) > 50 else obj.input_data
    short_input.short_description = 'Input'

    def short_output(self, obj):
        return (obj.final_output[:50] + '…') if obj.final_output and len(obj.final_output) > 50 else obj.final_output
    short_output.short_description = 'Output'
