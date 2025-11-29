from typing import Any, Dict
import logging
from .base import BaseDriver, DriverResponse

logger = logging.getLogger(__name__)


class RouterDriver(BaseDriver):
    type = "router"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        node_id = node.get("id", "unknown")
        label = node.get("data", {}).get("label", "Router")
        condition = context.get("condition", False)

        # Very simple router: choose path based on boolean flag
        route = "yes" if condition else "no"

        logger.info(f"[Router] Node: {label} ({node_id}) - Condition: {condition}, Route: {route}")

        return DriverResponse({
            "route": route,
            "status": "ok",
        })
