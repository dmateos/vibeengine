from django.contrib import admin
from .models import NodeType, Workflow


@admin.register(NodeType)
class NodeTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name', 'icon', 'color', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'display_name', 'description')
    readonly_fields = ('created_at',)
    ordering = ('name',)


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
