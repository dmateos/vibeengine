from typing import Any, Dict
from .base import BaseDriver, DriverResponse


class InputDriver(BaseDriver):
    type = "input"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        # Pass-through input as output
        return DriverResponse({
            "output": context.get("input"),
            "status": "ok",
        })
