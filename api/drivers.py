from typing import Any, Dict, Tuple


class DriverResponse(Dict[str, Any]):
    """Simple dict subclass for clarity when returning driver data."""


class BaseDriver:
    """Base interface for node drivers."""

    type: str = "base"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        raise NotImplementedError


class AgentDriver(BaseDriver):
    type = "agent"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        # Stubbed agent behavior: echo input with agent label
        input_text = context.get("input", "")
        label = (node.get("data") or {}).get("label", "Agent")
        return DriverResponse({
            "output": f"{label} processed: {input_text}",
            "status": "ok",
        })


class ToolDriver(BaseDriver):
    type = "tool"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        # Simulate a tool invocation by returning a transformed payload
        params = context.get("params", {})
        tool_name = (node.get("data") or {}).get("label", "Tool")
        return DriverResponse({
            "output": {"tool": tool_name, "result": {"echo": params}},
            "status": "ok",
        })


class RouterDriver(BaseDriver):
    type = "router"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        # Very simple router: choose path based on boolean flag
        route = "yes" if context.get("condition", False) else "no"
        return DriverResponse({
            "route": route,
            "status": "ok",
        })


class InputDriver(BaseDriver):
    type = "input"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        # Pass-through input as output
        return DriverResponse({
            "output": context.get("input"),
            "status": "ok",
        })


class OutputDriver(BaseDriver):
    type = "output"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        # Treat provided input as final output for display/persistence
        return DriverResponse({
            "final": context.get("input"),
            "status": "ok",
        })


class MemoryDriver(BaseDriver):
    type = "memory"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        # Simulate saving to memory and returning prior+current
        state = context.get("state", {})
        key = (node.get("data") or {}).get("key", "memory")
        # Default to using current input when explicit value is not provided
        value = context.get("value", context.get("input"))
        previous = state.get(key)
        state[key] = value
        return DriverResponse({
            "previous": previous,
            "stored": value,
            "state": state,
            # pass-through so the next node receives the same value
            "output": value,
            "status": "ok",
        })


DRIVERS: Dict[str, BaseDriver] = {
    AgentDriver.type: AgentDriver(),
    ToolDriver.type: ToolDriver(),
    RouterDriver.type: RouterDriver(),
    InputDriver.type: InputDriver(),
    OutputDriver.type: OutputDriver(),
    MemoryDriver.type: MemoryDriver(),
}


def execute_node_by_type(node_type: str, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
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
