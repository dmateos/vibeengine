"""
Node type definitions.

This module contains the canonical definitions for all node types in the system.
Each node type should have a corresponding driver in api/drivers/.
"""

from typing import Dict, Any, TypedDict, List, NotRequired


class NodeTypeDefinition(TypedDict):
    display_name: str
    icon: str
    color: str
    description: str
    category: str
    models: NotRequired[List[Dict[str, Any]]]
    config: NotRequired[Dict[str, Any]]


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
    'cron_trigger': {
        'display_name': 'Cron Trigger',
        'icon': '⏰',
        'color': '#10b981',
        'description': 'Schedule workflow execution using cron expressions',
        'category': 'Input/Output',
    },

    # Agents
    'openai_agent': {
        'display_name': 'OpenAI Agent',
        'icon': '🔵',
        'color': '#10a37f',
        'description': 'OpenAI-powered agent node (GPT-4, GPT-3.5, etc.)',
        'category': 'Agents',
        'models': [
            {'value': 'gpt-5.1', 'label': 'GPT-5.1'},
            {'value': 'gpt-5-mini', 'label': 'GPT-5 mini'},
            {'value': 'gpt-4.1', 'label': 'GPT-4.1'},
        ]
    },
    'claude_agent': {
        'display_name': 'Claude Agent',
        'icon': '🟠',
        'color': '#d97757',
        'description': 'Anthropic Claude-powered agent node',
        'category': 'Agents',
        'models': [
            {'value': 'claude-sonnet-4-5', 'label': 'Claude 4 Sonnet'},
            {'value': 'claude-haiku-4-5', 'label': 'Claude 4 Haiku'},
            {'value': 'claude-opus-4-5', 'label': 'Claude 4 Opus'},
        ]
    },
    'ollama_agent': {
        'display_name': 'Ollama Agent',
        'icon': '🟢',
        'color': '#06b6d4',
        'description': 'Local Ollama-powered agent node',
        'category': 'Agents',
        'models': [
            {'value': 'llama3.1:latest', 'label': 'Llama 3.1'},
            {'value': 'gpt-oss:20b', 'label': 'GPT Oss 20b'},
            {'value': 'deepseek-r1:8b', 'label': 'Deepseek r1 8b'},
            {'value': 'mistral:latest', 'label': 'Mistral'},
        ]
    },
    'huggingface': {
        'display_name': 'Hugging Face',
        'icon': '🤗',
        'color': '#ff9d00',
        'description': 'Local Hugging Face models for classification, NER, Q&A, embeddings, and more',
        'category': 'Agents',
    },
    'memory': {
        'display_name': 'Memory',
        'icon': '🧠',
        'color': '#ef4444',
        'description': 'Read/write flow state',
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
    'sleep': {
        'display_name': 'Sleep',
        'icon': '💤',
        'color': '#64748b',
        'description': 'Pause workflow execution for a specified duration',
        'category': 'Control Flow',
        'config': {
            'units': [
                {'value': 'milliseconds', 'label': 'Milliseconds'},
                {'value': 'seconds', 'label': 'Seconds'},
                {'value': 'minutes', 'label': 'Minutes'},
                {'value': 'hours', 'label': 'Hours'},
            ]
        }
    },
    'for_each': {
        'display_name': 'For Each',
        'icon': '🔁',
        'color': '#8b5cf6',
        'description': 'Iterate over array items and execute loop body for each',
        'category': 'Control Flow',
        'config': {
            'collect_options': [
                {'value': 'true', 'label': 'Collect Results (Array)'},
                {'value': 'false', 'label': 'Pass Through Original'},
            ]
        }
    },
    'loop': {
        'display_name': 'Loop',
        'icon': '🔄',
        'color': '#7c3aed',
        'description': 'Execute loop body N times with counter (for i in range)',
        'category': 'Control Flow',
        'config': {
            'pass_through_options': [
                {'value': 'true', 'label': 'Chain Output (each iteration feeds next)'},
                {'value': 'false', 'label': 'Collect Results (return array)'},
            ]
        }
    },
    'tool': {
        'display_name': 'Tool',
        'icon': '🛠️',
        'color': '#10b981',
        'description': 'Invokes an external capability/tool',
        'category': 'Agents',
    },
    'mcp_tool': {
        'display_name': 'MCP Tool',
        'icon': '🔌',
        'color': '#6366f1',
        'description': 'Connect to MCP servers and execute their tools',
        'category': 'Agents',
    },

    # Multi-Agent
    'consensus': {
        'display_name': 'Consensus',
        'icon': '🤝',
        'color': '#ec4899',
        'description': 'Analyze agreement among multiple responses',
        'category': 'Agents',
    },
    'conversation': {
        'display_name': 'Conversation',
        'icon': '💬',
        'color': '#f97316',
        'description': 'Multi-turn dialogue between multiple agents',
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
    'text_transform': {
        'display_name': 'Text Transform',
        'icon': '✏️',
        'color': '#6366f1',
        'description': 'Transform text with replace, regex, filter, split, and more',
        'category': 'Data',
    },
    'python_code': {
        'display_name': 'Python Code',
        'icon': '🐍',
        'color': '#0ea5e9',
        'description': 'Run Python code with stdin from the current input',
        'category': 'Data',
    },
    'ssh_command': {
        'display_name': 'SSH Command',
        'icon': '🔐',
        'color': '#059669',
        'description': 'Execute commands on remote servers via SSH',
        'category': 'Data',
    },
    'redis': {
        'display_name': 'Redis',
        'icon': '🔴',
        'color': '#dc2626',
        'description': 'Read/write data to Redis key-value store',
        'category': 'Data',
        'config': {
            'operations': [
                {'value': 'get', 'label': 'GET - Get value'},
                {'value': 'set', 'label': 'SET - Set value'},
                {'value': 'delete', 'label': 'DEL - Delete key'},
                {'value': 'incr', 'label': 'INCR - Increment'},
                {'value': 'decr', 'label': 'DECR - Decrement'},
                {'value': 'lpush', 'label': 'LPUSH - Push to list (left)'},
                {'value': 'rpush', 'label': 'RPUSH - Push to list (right)'},
                {'value': 'lpop', 'label': 'LPOP - Pop from list (left)'},
                {'value': 'rpop', 'label': 'RPOP - Pop from list (right)'},
                {'value': 'lrange', 'label': 'LRANGE - Get list items'},
                {'value': 'hset', 'label': 'HSET - Set hash field'},
                {'value': 'hget', 'label': 'HGET - Get hash field'},
                {'value': 'hgetall', 'label': 'HGETALL - Get all hash fields'},
                {'value': 'keys', 'label': 'KEYS - Get keys by pattern'},
                {'value': 'exists', 'label': 'EXISTS - Check if key exists'},
                {'value': 'ttl', 'label': 'TTL - Get time to live'},
            ]
        }
    },
    'sql': {
        'display_name': 'SQL Database',
        'icon': '🗄️',
        'color': '#0284c7',
        'description': 'Execute SQL queries on MySQL or PostgreSQL',
        'category': 'Data',
        'config': {
            'db_types': [
                {'value': 'postgresql', 'label': 'PostgreSQL'},
                {'value': 'mysql', 'label': 'MySQL'},
            ]
        }
    },

    # Network/Output
    'tcp_output': {
        'display_name': 'TCP Output',
        'icon': '🔌',
        'color': '#0891b2',
        'description': 'Send data to a TCP server/socket',
        'category': 'Data',
    },
    'html_output': {
        'display_name': 'HTML Output',
        'icon': '🌐',
        'color': '#e11d48',
        'description': 'Output HTML content with preview capability',
        'category': 'Input/Output',
    },
    'webhook': {
        'display_name': 'Webhook',
        'icon': '🔗',
        'color': '#0891b2',
        'description': 'Send HTTP requests to external webhooks and APIs',
        'category': 'Integrations',
        'config': {
            'methods': [
                {'value': 'GET', 'label': 'GET'},
                {'value': 'POST', 'label': 'POST'},
                {'value': 'PUT', 'label': 'PUT'},
                {'value': 'PATCH', 'label': 'PATCH'},
                {'value': 'DELETE', 'label': 'DELETE'},
            ],
            'auth_types': [
                {'value': 'none', 'label': 'None'},
                {'value': 'bearer', 'label': 'Bearer Token'},
                {'value': 'token', 'label': 'Token'},
                {'value': 'api_key', 'label': 'API Key (X-API-Key header)'},
            ]
        }
    },
    'email_output': {
        'display_name': 'Email Output',
        'icon': '📧',
        'color': '#ef4444',
        'description': 'Send emails via SMTP',
        'category': 'Integrations',
        'config': {
            'use_tls_options': [
                {'value': 'true', 'label': 'TLS (Port 587)'},
                {'value': 'false', 'label': 'SSL (Port 465)'},
            ],
            'html_options': [
                {'value': 'false', 'label': 'Plain Text'},
                {'value': 'true', 'label': 'HTML'},
            ]
        }
    },
    'web_scraper': {
        'display_name': 'Web Scraper',
        'icon': '🕷️',
        'color': '#8b5cf6',
        'description': 'Extract data from websites using CSS selectors',
        'category': 'Integrations',
        'config': {
            'methods': [
                {'value': 'css', 'label': 'CSS Selector'},
                {'value': 'xpath', 'label': 'XPath (not supported yet)'},
            ],
            'extract_types': [
                {'value': 'text', 'label': 'Text Content'},
                {'value': 'html', 'label': 'HTML'},
                {'value': 'attr', 'label': 'Attribute'},
            ],
            'multiple_options': [
                {'value': 'true', 'label': 'Multiple Results (Array)'},
                {'value': 'false', 'label': 'Single Result'},
            ]
        }
    },
    'pushover': {
        'display_name': 'Pushover',
        'icon': '📱',
        'color': '#249df1',
        'description': 'Send push notifications via Pushover',
        'category': 'Integrations',
        'config': {
            'sounds': [
                {'value': '', 'label': 'Default'},
                {'value': 'pushover', 'label': 'Pushover'},
                {'value': 'bike', 'label': 'Bike'},
                {'value': 'bugle', 'label': 'Bugle'},
                {'value': 'cashregister', 'label': 'Cash Register'},
                {'value': 'classical', 'label': 'Classical'},
                {'value': 'cosmic', 'label': 'Cosmic'},
                {'value': 'falling', 'label': 'Falling'},
                {'value': 'gamelan', 'label': 'Gamelan'},
                {'value': 'incoming', 'label': 'Incoming'},
                {'value': 'intermission', 'label': 'Intermission'},
                {'value': 'magic', 'label': 'Magic'},
                {'value': 'mechanical', 'label': 'Mechanical'},
                {'value': 'pianobar', 'label': 'Piano Bar'},
                {'value': 'siren', 'label': 'Siren'},
                {'value': 'spacealarm', 'label': 'Space Alarm'},
                {'value': 'tugboat', 'label': 'Tug Boat'},
                {'value': 'alien', 'label': 'Alien (long)'},
                {'value': 'climb', 'label': 'Climb (long)'},
                {'value': 'persistent', 'label': 'Persistent (long)'},
                {'value': 'echo', 'label': 'Echo (long)'},
                {'value': 'updown', 'label': 'Up Down (long)'},
                {'value': 'vibrate', 'label': 'Vibrate only'},
                {'value': 'none', 'label': 'Silent'},
            ]
        }
    },
    'embeddings': {
        'display_name': 'Embeddings',
        'icon': '🔢',
        'color': '#8b5cf6',
        'description': 'Generate text embeddings from multiple providers (OpenAI, Cohere, HuggingFace)',
        'category': 'Agents',
        'config': {
            'openai': {
                'models': [
                    {'value': 'text-embedding-3-small', 'label': 'text-embedding-3-small'},
                    {'value': 'text-embedding-3-large', 'label': 'text-embedding-3-large'},
                    {'value': 'text-embedding-ada-002', 'label': 'ada-002 (legacy)'},
                ]
            },
            'cohere': {
                'models': [
                    {'value': 'embed-english-v3.0', 'label': 'English v3.0'},
                    {'value': 'embed-multilingual-v3.0', 'label': 'Multilingual v3.0'},
                ]
            },
            'huggingface': {
                'models': [
                    {'value': 'all-MiniLM-L6-v2', 'label': 'all-MiniLM-L6-v2'},
                    {'value': 'all-mpnet-base-v2', 'label': 'all-mpnet-base-v2'},
                ]
            }
        }
    },
    'image_generation': {
        'display_name': 'Image Generation',
        'icon': '🎨',
        'color': '#f59e0b',
        'description': 'Generate images from text using DALL-E, Stable Diffusion, and more',
        'category': 'Agents',
        'config': {
            'dalle': {
                'models': [
                    {'value': 'dall-e-3', 'label': 'DALL-E 3'},
                    {'value': 'dall-e-2', 'label': 'DALL-E 2'},
                ],
                'sizes': [
                    {'value': '1024x1024', 'label': '1024x1024 (Square)'},
                    {'value': '1792x1024', 'label': '1792x1024 (Landscape)'},
                    {'value': '1024x1792', 'label': '1024x1792 (Portrait)'},
                ],
                'qualities': [
                    {'value': 'standard', 'label': 'Standard'},
                    {'value': 'hd', 'label': 'HD (Higher cost)'},
                ],
                'styles': [
                    {'value': 'vivid', 'label': 'Vivid (Hyper-real)'},
                    {'value': 'natural', 'label': 'Natural'},
                ]
            },
            'stability': {
                'models': [
                    {'value': 'stable-diffusion-xl-1024-v1-0', 'label': 'SD XL 1.0'},
                    {'value': 'stable-diffusion-v1-6', 'label': 'SD v1.6'},
                ]
            }
        }
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
