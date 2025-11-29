from typing import Any, Dict
import logging
from .base import BaseDriver, DriverResponse

logger = logging.getLogger(__name__)


class InputDriver(BaseDriver):
    type = "input"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        node_id = node.get("id", "unknown")
        label = node.get("data", {}).get("label", "Input")
        input_val = context.get("input")

        logger.info(f"[Input] Node: {label} ({node_id})")
        logger.debug(f"[Input] Value: {str(input_val)[:200]}...")

        # Pass-through input as output
        return DriverResponse({
            "output": input_val,
            "status": "ok",
        })
