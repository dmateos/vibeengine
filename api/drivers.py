from typing import Any, Dict, Tuple
import os
import json
from .memory_store import store


class DriverResponse(Dict[str, Any]):
    """Simple dict subclass for clarity when returning driver data."""


class BaseDriver:
    """Base interface for node drivers."""

    type: str = "base"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        raise NotImplementedError


class AgentDriver(BaseDriver):
    type = "agent"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        # Agent can call OpenAI if configured; otherwise falls back to simple echo using knowledge/tools
        input_text = context.get("input", "")
        data = (node.get("data") or {})
        label = data.get("label", "Agent")
        knowledge = context.get("knowledge") or {}
        tools = context.get("tools") or []

        use_openai = data.get("use_openai") or (data.get("provider") == "openai")
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = data.get("model") or "gpt-4o-mini"
        temperature = data.get("temperature")
        try:
            temperature_val = float(temperature) if temperature is not None else 0.2
        except Exception:
            temperature_val = 0.2
        system_prompt = data.get("system") or "You are a helpful assistant."

        # Build a contextual system message including supplemental knowledge summary
        if knowledge:
            try:
                knowledge_json = json.dumps(knowledge)[:4000]
                system_prompt = (
                    f"{system_prompt}\n\nSupplemental knowledge (JSON):\n{knowledge_json}"
                )
            except Exception:
                pass

        if use_openai and api_key:
            payload = {
                "model": model,
                "temperature": temperature_val,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": str(input_text)},
                ],
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            try:
                content = _post_openai_chat(base_url, payload, headers)
                return DriverResponse({
                    "output": content,
                    "model": model,
                    "status": "ok",
                })
            except Exception as exc:
                # Fall through to local behavior with error note
                fallback_note = f"OpenAI error: {exc}"
        else:
            fallback_note = None if use_openai else "OpenAI not enabled on node"

        # Fallback: cascade tool outputs then compose response including knowledge/tools
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


def _post_openai_chat(base_url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> str:
    """Post a chat completion request to OpenAI (or compatible) and return content.

    Uses requests if available, else urllib.
    """
    url = base_url.rstrip("/") + "/chat/completions"
    try:
        import requests  # type: ignore

        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        # fallback to urllib
        import urllib.request
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=60) as f:  # type: ignore
            data = json.loads(f.read().decode("utf-8"))

    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        # try the legacy completion shape
        return data.get("choices", [{}])[0].get("text", "")


class ToolDriver(BaseDriver):
    type = "tool"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        data = (node.get("data") or {})
        operation = data.get("operation") or "echo"
        arg = data.get("arg") or ""
        input_val = context.get("input")
        tool_name = data.get("label", "Tool")

        try:
            if operation == "uppercase" and isinstance(input_val, str):
                out = input_val.upper()
            elif operation == "lowercase" and isinstance(input_val, str):
                out = input_val.lower()
            elif operation == "append" and isinstance(input_val, str):
                out = f"{input_val}{arg}"
            else:
                # Default: echo provided params
                out = {"echo": context.get("params", {})}

            return DriverResponse({
                "output": out,
                "tool": tool_name,
                "status": "ok",
            })
        except Exception as exc:
            return DriverResponse({"status": "error", "error": str(exc)})


class RouterDriver(BaseDriver):
    type = "router"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        # Very simple router: choose path based on boolean flag
        route = "yes" if context.get("condition", False) else "no"
        return DriverResponse({
            "route": route,
            "status": "ok",
        })


class InputDriver(BaseDriver):
    type = "input"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        # Pass-through input as output
        return DriverResponse({
            "output": context.get("input"),
            "status": "ok",
        })


class OutputDriver(BaseDriver):
    type = "output"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        # Treat provided input as final output for display/persistence
        return DriverResponse({
            "final": context.get("input"),
            "status": "ok",
        })


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


DRIVERS: Dict[str, BaseDriver] = {
    AgentDriver.type: AgentDriver(),
    ToolDriver.type: ToolDriver(),
    RouterDriver.type: RouterDriver(),
    InputDriver.type: InputDriver(),
    OutputDriver.type: OutputDriver(),
    MemoryDriver.type: MemoryDriver(),
}


def execute_node_by_type(node_type: str, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
    driver = DRIVERS.get(node_type)
    if not driver:
        return DriverResponse({
            "status": "error",
            "error": f"No driver registered for node type '{node_type}'",
        })
    try:
        return driver.execute(node, context)
    except Exception as exc:
        return DriverResponse({
            "status": "error",
            "error": str(exc),
        })
