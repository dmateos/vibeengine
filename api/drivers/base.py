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

    # --- Memory helpers ---
    def _extract_names(self, text: str) -> list:
        """Naive name extractor: capitalized tokens not at sentence start.

        This is intentionally simple and conservative. It won't catch all names
        but provides a lightweight heuristic without external deps.
        """
        if not isinstance(text, str) or not text:
            return []
        import re
        # Split into sentences and words
        sentences = re.split(r"(?<=[.!?])\s+", text)
        candidates = []
        common = set([
            'I','A','The','And','But','Or','We','You','He','She','It','They','We','Your','My',
            'Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday',
            'January','February','March','April','May','June','July','August','September','October','November','December'
        ])
        for s in sentences:
            words = re.findall(r"[A-Za-z][a-z]+(?:'[A-Za-z]+)?", s)
            # Skip the first word (often sentence start capitalization)
            for w in words[1:]:
                if w[0].isupper() and w not in common and len(w) > 1:
                    candidates.append(w)
        # Dedupe, preserve order
        seen = set()
        result = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                result.append(c)
        return result

    def _save_names_to_memory(self, names: list, mem_specs: list) -> None:
        """Append detected names to all connected memory nodes."""
        if not names or not mem_specs:
            return
        try:
            from ..memory_store import store
            for spec in mem_specs:
                ns = (spec or {}).get('namespace') or 'default'
                key = (spec or {}).get('key') or 'names'
                store_key = f"{ns}:{key}"
                prev = store.get(store_key)
                base = prev if isinstance(prev, list) else ([] if prev is None else [prev])
                merged = list(base)
                for n in names:
                    if n not in merged:
                        merged.append(n)
                store.set(store_key, merged)
        except Exception:
            # Non-fatal
            pass
