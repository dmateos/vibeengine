from typing import Any, Dict, Tuple, List, Optional
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
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            try:
                # If agent_tools are provided, enable function calling
                agent_tools: List[Dict[str, Any]] = context.get("agent_tools") or []
                tool_nodes: Dict[str, Any] = context.get("agent_tool_nodes") or {}
                if agent_tools:
                    tool_defs: List[Dict[str, Any]] = []
                    for t in agent_tools:
                        tid = str(t.get("nodeId"))
                        tname = t.get("name") or t.get("label") or f"Tool {tid}"
                        # Allow passing arbitrary params and optional input override
                        tool_defs.append({
                            "type": "function",
                            "function": {
                                "name": f"tool_{tid}",
                                "description": f"Invoke connected tool '{tname}'",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "input": {"type": ["string", "null"], "description": "Optional input override"},
                                        "params": {"type": "object", "description": "Optional parameters"},
                                    },
                                },
                            },
                        })
                    content, call_log = _chat_with_tools(
                        base_url=base_url,
                        headers=headers,
                        model=model,
                        temperature=temperature_val,
                        system_prompt=system_prompt,
                        user_content=str(input_text),
                        tool_defs=tool_defs,
                        tool_nodes=tool_nodes,
                        shared_context=context,
                    )
                else:
                    payload = {
                        "model": model,
                        "temperature": temperature_val,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": str(input_text)},
                        ],
                    }
                    content = _post_openai_chat(base_url, payload, headers)
                return DriverResponse({
                    "output": content,
                    "model": model,
                    "tool_call_log": call_log if agent_tools else [],
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


def _chat_with_tools(
    *,
    base_url: str,
    headers: Dict[str, str],
    model: str,
    temperature: float,
    system_prompt: str,
    user_content: str,
    tool_defs: List[Dict[str, Any]],
    tool_nodes: Dict[str, Dict[str, Any]],
    shared_context: Dict[str, Any],
) -> Tuple[str, List[Dict[str, Any]]]:
    """Run a chat that can call defined tools via OpenAI function calling.

    Tool names must be of the form 'tool_<nodeId>'.
    """
    url = base_url.rstrip("/") + "/chat/completions"
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": str(user_content)},
    ]

    tool_call_log: List[Dict[str, Any]] = []
    for _ in range(4):  # limit tool-exec loops
        body = {
            "model": model,
            "temperature": temperature,
            "messages": messages,
            "tools": tool_defs,
            "tool_choice": "auto",
        }
        try:
            import requests  # type: ignore

            resp = requests.post(url, headers=headers, json=body, timeout=60)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            # fallback to urllib
            import urllib.request
            req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=60) as f:  # type: ignore
                data = json.loads(f.read().decode("utf-8"))

        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        tool_calls = message.get("tool_calls") or []

        if tool_calls:
            # include the assistant message with tool_calls before sending tool outputs
            messages.append({
                "role": "assistant",
                "content": message.get("content"),
                "tool_calls": tool_calls,
            })

            for tc in tool_calls:
                func = (tc.get("function") or {})
                name = func.get("name", "")
                args_str = func.get("arguments") or "{}"
                try:
                    args = json.loads(args_str)
                except Exception:
                    args = {}
                node_id = name.replace("tool_", "", 1)
                node = tool_nodes.get(str(node_id))
                if not node:
                    res_obj = {"status": "error", "error": f"unknown tool {name}"}
                    content = json.dumps(res_obj)
                else:
                    tool_ctx = dict(shared_context)
                    # Allow overriding input/params via arguments
                    if "input" in args:
                        tool_ctx["input"] = args["input"]
                    if "params" in args:
                        tool_ctx["params"] = args["params"]
                    try:
                        res = execute_node_by_type("tool", node, tool_ctx)
                        res_obj = dict(res)
                        content = json.dumps(res_obj)
                    except Exception as exc:
                        res_obj = {"status": "error", "error": str(exc)}
                        content = json.dumps(res_obj)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id"),
                    "content": content,
                })
                tool_call_log.append({
                    "name": name,
                    "args": args,
                    "result": res_obj,
                })
            # continue loop for follow-up
            continue

        # no tool calls -> final content
        return (message.get("content", "") or "", tool_call_log)

    # loop exhausted
    return ("", tool_call_log)


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
