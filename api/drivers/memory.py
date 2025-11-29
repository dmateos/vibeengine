from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)
from ..memory_store import store
from .base import BaseDriver, DriverResponse


class MemoryDriver(BaseDriver):
    type = "memory"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        node_id = node.get("id", "unknown")
        # Save to store and to transient context state
        state = context.get("state", {})
        data = (node.get("data") or {})
        label = data.get("label", "Memory")
        key = data.get("key", "memory")
        namespace = data.get("namespace") or "default"
        store_key = f"{namespace}:{key}"
        # Default to using current input when explicit value is not provided
        value = context.get("value", context.get("input"))
        previous = store.get(store_key)

        logger.info(f"[Memory] Node: {label} ({node_id}) - Storing to {store_key}")
        logger.debug(f"[Memory] Value: {str(value)[:100]}...")

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
