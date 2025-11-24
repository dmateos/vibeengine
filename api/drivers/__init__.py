from typing import Any, Dict
from .base import BaseDriver, BaseAgentDriver, DriverResponse
from .openai_agent import OpenAIAgentDriver
from .claude_agent import ClaudeAgentDriver
from .ollama_agent import OllamaAgentDriver
from .tool import ToolDriver
from .router import RouterDriver
from .input import InputDriver
from .output import OutputDriver
from .memory import MemoryDriver
from .parallel import ParallelDriver
from .join import JoinDriver


# Registry of all available drivers
DRIVERS: Dict[str, BaseDriver] = {
    OpenAIAgentDriver.type: OpenAIAgentDriver(),
    ClaudeAgentDriver.type: ClaudeAgentDriver(),
    OllamaAgentDriver.type: OllamaAgentDriver(),
    ToolDriver.type: ToolDriver(),
    RouterDriver.type: RouterDriver(),
    InputDriver.type: InputDriver(),
    OutputDriver.type: OutputDriver(),
    MemoryDriver.type: MemoryDriver(),
    ParallelDriver.type: ParallelDriver(),
    JoinDriver.type: JoinDriver(),
}


def execute_node_by_type(node_type: str, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
    """Execute a node using the appropriate driver based on node type.

    Args:
        node_type: The type of node to execute (e.g., 'openai_agent', 'tool', etc.)
        node: The node data including configuration
        context: The execution context including input and state

    Returns:
        DriverResponse with the execution result
    """
    driver = DRIVERS.get(node_type)
    if not driver:
        return DriverResponse({
            "status": "error",
            "error": f"No driver registered for node type '{node_type}'",
        })
    try:
        return driver.execute(node, context)
    except Exception as exc:
        return DriverResponse({
            "status": "error",
            "error": str(exc),
        })


__all__ = [
    "BaseDriver",
    "BaseAgentDriver",
    "DriverResponse",
    "OpenAIAgentDriver",
    "ClaudeAgentDriver",
    "OllamaAgentDriver",
    "ToolDriver",
    "RouterDriver",
    "InputDriver",
    "OutputDriver",
    "MemoryDriver",
    "ParallelDriver",
    "JoinDriver",
    "DRIVERS",
    "execute_node_by_type",
]
