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
        """Generate minimal, non-conversational fallback output.

        To respect prompts like "only transform the input; don't be conversational",
        we avoid appending any context, notes, or labels. We simply pass through
        the input (or the last tool-produced string if available), so downstream
        nodes receive a clean value.
        """
        # Prefer last tool string output if present; else use input_text as-is
        current = input_text
        for t in tools or []:
            t_out = (t or {}).get("output")
            if isinstance(t_out, str) and t_out:
                current = t_out

        return DriverResponse({
            "output": current,
            "status": "ok",
        })

    # No passive memory heuristics; LLM decides via memory_* functions
