from typing import Any, Dict
from .base import BaseDriver, DriverResponse


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
