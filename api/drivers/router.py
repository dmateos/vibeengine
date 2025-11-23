from typing import Any, Dict
from .base import BaseDriver, DriverResponse


class RouterDriver(BaseDriver):
    type = "router"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        # Very simple router: choose path based on boolean flag
        route = "yes" if context.get("condition", False) else "no"
        return DriverResponse({
            "route": route,
            "status": "ok",
        })
