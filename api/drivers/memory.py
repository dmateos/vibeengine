from typing import Any, Dict
from ..memory_store import store
from .base import BaseDriver, DriverResponse


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
