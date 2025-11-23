from typing import Any, Dict, List, Optional
import json


class DriverResponse(Dict[str, Any]):
    """Simple dict subclass for clarity when returning driver data."""


class BaseDriver:
    """Base interface for node drivers."""

    type: str = "base"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        raise NotImplementedError


class BaseAgentDriver(BaseDriver):
    """Base class for agent drivers with common logic."""

    def _build_system_prompt(self, data: Dict[str, Any], knowledge: Dict[str, Any]) -> str:
        """Build system prompt including supplemental knowledge."""
        system_prompt = data.get("system") or "You are a helpful assistant."

        if knowledge:
            try:
                knowledge_json = json.dumps(knowledge)[:4000]
                system_prompt = (
                    f"{system_prompt}\n\nSupplemental knowledge (JSON):\n{knowledge_json}"
                )
            except Exception:
                pass

        return system_prompt

    def _get_temperature(self, data: Dict[str, Any]) -> float:
        """Extract and validate temperature from node data."""
        temperature = data.get("temperature")
        try:
            return float(temperature) if temperature is not None else 0.2
        except Exception:
            return 0.2

    def _fallback_response(self, input_text: str, label: str, knowledge: Dict[str, Any],
                          tools: List[Dict[str, Any]], fallback_note: Optional[str] = None) -> DriverResponse:
        """Generate fallback response when LLM is not available."""
        current = input_text
        used_tool_names = []
        for t in tools:
            t_out = (t or {}).get("output")
            t_name = (t or {}).get("tool") or (t or {}).get("name")
            if isinstance(t_out, str):
                current = t_out
            used_tool_names.append(t_name)

        base = f"{label} processed: {current}"
        if knowledge:
            base += f" | ctx: {knowledge}"
        if used_tool_names:
            base += f" | tools: {used_tool_names}"
        if fallback_note:
            base += f" | note: {fallback_note}"

        return DriverResponse({
            "output": base,
            "knowledge": knowledge,
            "tools": tools,
            "status": "ok",
        })
