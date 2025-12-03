from typing import Any, Dict
from .base import BaseDriver, BaseAgentDriver, DriverResponse
from .openai_agent import OpenAIAgentDriver
from .claude_agent import ClaudeAgentDriver
from .ollama_agent import OllamaAgentDriver
from .tool import ToolDriver
from .mcp_tool import MCPToolDriver
from .router import RouterDriver
from .condition import ConditionDriver
from .input import InputDriver
from .output import OutputDriver
from .cron_trigger import CronTriggerDriver
from .memory import MemoryDriver
from .parallel import ParallelDriver
from .join import JoinDriver
from .json_validator import JSONValidatorDriver
from .huggingface import HuggingFaceDriver
from .text_transform import TextTransformDriver
from .consensus import ConsensusDriver
from .conversation import ConversationDriver
from .tcp_output import TCPOutputDriver
from .python_code import PythonCodeDriver
from .ssh_command import SSHCommandDriver
from .html_output import HTMLOutputDriver
from .pushover import PushoverDriver


# Registry of all available drivers
DRIVERS: Dict[str, BaseDriver] = {
    OpenAIAgentDriver.type: OpenAIAgentDriver(),
    ClaudeAgentDriver.type: ClaudeAgentDriver(),
    OllamaAgentDriver.type: OllamaAgentDriver(),
    HuggingFaceDriver.type: HuggingFaceDriver(),
    ToolDriver.type: ToolDriver(),
    MCPToolDriver.type: MCPToolDriver(),
    RouterDriver.type: RouterDriver(),
    ConditionDriver.type: ConditionDriver(),
    InputDriver.type: InputDriver(),
    OutputDriver.type: OutputDriver(),
    CronTriggerDriver.type: CronTriggerDriver(),
    MemoryDriver.type: MemoryDriver(),
    ParallelDriver.type: ParallelDriver(),
    JoinDriver.type: JoinDriver(),
    JSONValidatorDriver.type: JSONValidatorDriver(),
    TextTransformDriver.type: TextTransformDriver(),
    ConsensusDriver.type: ConsensusDriver(),
    ConversationDriver.type: ConversationDriver(),
    TCPOutputDriver.type: TCPOutputDriver(),
    PythonCodeDriver.type: PythonCodeDriver(),
    SSHCommandDriver.type: SSHCommandDriver(),
    HTMLOutputDriver.type: HTMLOutputDriver(),
    PushoverDriver.type: PushoverDriver(),
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
    "HuggingFaceDriver",
    "ToolDriver",
    "MCPToolDriver",
    "RouterDriver",
    "ConditionDriver",
    "InputDriver",
    "OutputDriver",
    "CronTriggerDriver",
    "MemoryDriver",
    "ParallelDriver",
    "JoinDriver",
    "JSONValidatorDriver",
    "TextTransformDriver",
    "ConsensusDriver",
    "ConversationDriver",
    "TCPOutputDriver",
    "PythonCodeDriver",
    "SSHCommandDriver",
    "HTMLOutputDriver",
    "PushoverDriver",
    "DRIVERS",
    "execute_node_by_type",
]
