from django.db import migrations


def seed_agent_node_types(apps, schema_editor):
    NodeType = apps.get_model('api', 'NodeType')
    defaults = [
        {
            'name': 'agent',
            'display_name': 'Agent',
            'icon': '🤖',
            'color': '#667eea',
            'description': 'LLM-backed autonomous agent node',
        },
        {
            'name': 'tool',
            'display_name': 'Tool',
            'icon': '🛠️',
            'color': '#10b981',
            'description': 'Invokes an external capability/tool',
        },
        {
            'name': 'router',
            'display_name': 'Router',
            'icon': '🧭',
            'color': '#f59e0b',
            'description': 'Routes flow based on context',
        },
        {
            'name': 'input',
            'display_name': 'Input',
            'icon': '⬇️',
            'color': '#3b82f6',
            'description': 'Flow input node',
        },
        {
            'name': 'output',
            'display_name': 'Output',
            'icon': '⬆️',
            'color': '#8b5cf6',
            'description': 'Flow output node',
        },
        {
            'name': 'memory',
            'display_name': 'Memory',
            'icon': '🧠',
            'color': '#ef4444',
            'description': 'Read/write flow state',
        },
    ]

    for item in defaults:
        NodeType.objects.update_or_create(name=item['name'], defaults=item)


def unseed_agent_node_types(apps, schema_editor):
    NodeType = apps.get_model('api', 'NodeType')
    for name in ['agent', 'tool', 'router', 'input', 'output', 'memory']:
        try:
            NodeType.objects.filter(name=name).delete()
        except Exception:
            pass


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0002_nodetype'),
    ]

    operations = [
        migrations.RunPython(seed_agent_node_types, reverse_code=unseed_agent_node_types),
    ]

