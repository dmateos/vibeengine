from typing import Any, Dict
import logging
from .base import BaseDriver, DriverResponse

logger = logging.getLogger(__name__)


class CronTriggerDriver(BaseDriver):
    """Cron schedule trigger - acts as workflow entry point."""
    type = "cron_trigger"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        node_id = node.get("id", "unknown")
        label = node.get("data", {}).get("label", "Cron Trigger")
        cron_expr = node.get("data", {}).get("cronExpression", "")

        logger.info(f"[CronTrigger] Node: {label} ({node_id})")
        logger.debug(f"[CronTrigger] Cron Expression: {cron_expr}")

        # Validate cron expression
        if not cron_expr:
            return DriverResponse({
                "status": "error",
                "error": "Cron expression is required"
            })

        # Validate syntax using croniter
        try:
            from croniter import croniter
            croniter(cron_expr)
        except Exception as e:
            return DriverResponse({
                "status": "error",
                "error": f"Invalid cron expression: {str(e)}"
            })

        # Return initial input (like input node does)
        # The initial input can be defined in the node data
        initial_input = node.get("data", {}).get("initialInput", {})

        # If no initial input is set, use the context input
        if not initial_input:
            initial_input = context.get("input", {})

        logger.debug(f"[CronTrigger] Initial Input: {str(initial_input)[:200]}...")

        return DriverResponse({
            "status": "ok",
            "output": initial_input
        })
