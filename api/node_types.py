"""
Node type definitions.

This module contains the canonical definitions for all node types in the system.
Each node type should have a corresponding driver in api/drivers/.
"""

from typing import Dict, Any, TypedDict


class NodeTypeDefinition(TypedDict):
    display_name: str
    icon: str
    color: str
    description: str
    category: str


NODE_TYPE_DEFINITIONS: Dict[str, NodeTypeDefinition] = {
    # Input/Output
    'input': {
        'display_name': 'Input',
        'icon': '⬇️',
        'color': '#3b82f6',
        'description': 'Flow input node',
        'category': 'Input/Output',
    },
    'output': {
        'display_name': 'Output',
        'icon': '⬆️',
        'color': '#8b5cf6',
        'description': 'Flow output node',
        'category': 'Input/Output',
    },

    # Agents
    'openai_agent': {
        'display_name': 'OpenAI Agent',
        'icon': '🔵',
        'color': '#10a37f',
        'description': 'OpenAI-powered agent node (GPT-4, GPT-3.5, etc.)',
        'category': 'Agents',
    },
    'claude_agent': {
        'display_name': 'Claude Agent',
        'icon': '🟠',
        'color': '#d97757',
        'description': 'Anthropic Claude-powered agent node',
        'category': 'Agents',
    },
    'ollama_agent': {
        'display_name': 'Ollama Agent',
        'icon': '🟢',
        'color': '#06b6d4',
        'description': 'Local Ollama-powered agent node',
        'category': 'Agents',
    },

    # Control Flow
    'condition': {
        'display_name': 'Condition',
        'icon': '❓',
        'color': '#f59e0b',
        'description': 'Evaluate expressions and route based on true/false result',
        'category': 'Control Flow',
    },
    'router': {
        'display_name': 'Router',
        'icon': '🧭',
        'color': '#f59e0b',
        'description': 'Routes flow based on context',
        'category': 'Control Flow',
    },
    'parallel': {
        'display_name': 'Parallel',
        'icon': '⑂',
        'color': '#8b5cf6',
        'description': 'Fork execution into multiple parallel branches',
        'category': 'Control Flow',
    },
    'join': {
        'display_name': 'Join',
        'icon': '⑃',
        'color': '#a855f7',
        'description': 'Merge results from parallel branches',
        'category': 'Control Flow',
    },
    'tool': {
        'display_name': 'Tool',
        'icon': '🛠️',
        'color': '#10b981',
        'description': 'Invokes an external capability/tool',
        'category': 'Agents',
    },
    'memory': {
        'display_name': 'Memory',
        'icon': '🧠',
        'color': '#ef4444',
        'description': 'Read/write flow state',
        'category': 'Agents',
    },

    # Data
    'json_validator': {
        'display_name': 'JSON Validator',
        'icon': '✓',
        'color': '#14b8a6',
        'description': 'Validate JSON data against a schema',
        'category': 'Data',
    },
}


def get_node_type(name: str) -> NodeTypeDefinition | None:
    """Get a node type definition by name."""
    return NODE_TYPE_DEFINITIONS.get(name)


def get_all_node_types() -> Dict[str, NodeTypeDefinition]:
    """Get all node type definitions."""
    return NODE_TYPE_DEFINITIONS.copy()


def get_node_types_by_category() -> Dict[str, list[Dict[str, Any]]]:
    """Get node types grouped by category."""
    categorized: Dict[str, list[Dict[str, Any]]] = {}

    for name, definition in NODE_TYPE_DEFINITIONS.items():
        category = definition['category']
        if category not in categorized:
            categorized[category] = []

        categorized[category].append({
            'name': name,
            **definition
        })

    return categorized
