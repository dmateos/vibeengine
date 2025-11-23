from typing import Any, Dict
from .base import BaseDriver, DriverResponse


class OutputDriver(BaseDriver):
    type = "output"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        # Treat provided input as final output for display/persistence
        return DriverResponse({
            "final": context.get("input"),
            "status": "ok",
        })
