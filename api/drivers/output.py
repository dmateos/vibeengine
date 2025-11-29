from typing import Any, Dict
import logging
from .base import BaseDriver, DriverResponse

logger = logging.getLogger(__name__)


class OutputDriver(BaseDriver):
    type = "output"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        node_id = node.get("id", "unknown")
        label = node.get("data", {}).get("label", "Output")
        final_val = context.get("input")

        logger.info(f"[Output] Node: {label} ({node_id})")
        logger.info(f"[Output] Final value: {str(final_val)[:200]}...")

        # Treat provided input as final output for display/persistence
        return DriverResponse({
            "final": final_val,
            "status": "ok",
        })
