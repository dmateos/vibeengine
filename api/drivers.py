from typing import Any, Dict, Tuple
from .memory_store import store


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
        # Agent uses supplemental memory (knowledge) and tools if provided
        input_text = context.get("input", "")
        label = (node.get("data") or {}).get("label", "Agent")
        knowledge = context.get("knowledge") or {}
        tools = context.get("tools") or []

        # If tools are provided as executed results, cascade string outputs
        current = input_text
        used_tool_names = []
        for t in tools:
            t_out = (t or {}).get("output")
            t_name = (t or {}).get("tool") or (t or {}).get("name")
            if isinstance(t_out, str):
                current = t_out
            used_tool_names.append(t_name)

        # Compose a human-readable output
        base = f"{label} processed: {current}"
        if knowledge:
            base += f" | ctx: {knowledge}"
        if used_tool_names:
            base += f" | tools: {used_tool_names}"

        return DriverResponse({
            "output": base,
            "knowledge": knowledge,
            "tools": tools,
            "status": "ok",
        })


class ToolDriver(BaseDriver):
    type = "tool"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        data = (node.get("data") or {})
        operation = data.get("operation") or "echo"
        arg = data.get("arg") or ""
        input_val = context.get("input")
        tool_name = data.get("label", "Tool")

        try:
            if operation == "uppercase" and isinstance(input_val, str):
                out = input_val.upper()
            elif operation == "lowercase" and isinstance(input_val, str):
                out = input_val.lower()
            elif operation == "append" and isinstance(input_val, str):
                out = f"{input_val}{arg}"
            else:
                # Default: echo provided params
                out = {"echo": context.get("params", {})}

            return DriverResponse({
                "output": out,
                "tool": tool_name,
                "status": "ok",
            })
        except Exception as exc:
            return DriverResponse({"status": "error", "error": str(exc)})


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
        # Save to store and to transient context state
        state = context.get("state", {})
        data = (node.get("data") or {})
        key = data.get("key", "memory")
        namespace = data.get("namespace") or "default"
        store_key = f"{namespace}:{key}"
        # Default to using current input when explicit value is not provided
        value = context.get("value", context.get("input"))
        previous = store.get(store_key)
        store.set(store_key, value)
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
