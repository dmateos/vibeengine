from typing import Any, Dict, List, Tuple
import os
import json
from .base import BaseAgentDriver, DriverResponse


class OpenAIAgentDriver(BaseAgentDriver):
    type = "openai_agent"

    def _post_chat(self, base_url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> str:
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
        self,
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
        from . import execute_node_by_type  # Avoid circular import

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

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        input_text = context.get("input", "")
        data = (node.get("data") or {})
        label = data.get("label", "OpenAI Agent")
        knowledge = context.get("knowledge") or {}
        tools = context.get("tools") or []

        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = data.get("model") or "gpt-4o-mini"
        temperature_val = self._get_temperature(data)
        system_prompt = self._build_system_prompt(data, knowledge)

        if not api_key:
            return self._fallback_response(input_text, label, knowledge, tools, "OpenAI API key not configured")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            # If agent_tools are provided, enable function calling
            agent_tools: List[Dict[str, Any]] = context.get("agent_tools") or []
            tool_nodes: Dict[str, Any] = context.get("agent_tool_nodes") or {}
            call_log: List[Dict[str, Any]] = []  # Initialize call_log

            if agent_tools:
                tool_defs: List[Dict[str, Any]] = []
                for t in agent_tools:
                    tid = str(t.get("nodeId"))
                    tname = t.get("name") or t.get("label") or f"Tool {tid}"
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
                content, call_log = self._chat_with_tools(
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
                content = self._post_chat(base_url, payload, headers)

            # The 'content' already contains the LLM's final response after seeing tool results
            # (if tools were called, the LLM has already incorporated their results)
            return DriverResponse({
                "output": content,
                "model": model,
                "tool_call_log": call_log,
                "status": "ok",
            })
        except Exception as exc:
            return self._fallback_response(input_text, label, knowledge, tools, f"OpenAI error: {exc}")
