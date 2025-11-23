from typing import Any, Dict, List, Tuple
import os
import json
from .base import BaseAgentDriver, DriverResponse


class ClaudeAgentDriver(BaseAgentDriver):
    type = "claude_agent"

    def _post_chat(self, base_url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> str:
        """Post a chat completion request to Claude and return content.

        Uses requests if available, else urllib.
        """
        url = base_url.rstrip("/") + "/v1/messages"
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
            # Extract text from content blocks
            content_blocks = data.get("content", [])
            if isinstance(content_blocks, list) and len(content_blocks) > 0:
                return content_blocks[0].get("text", "")
            return ""
        except Exception:
            return ""

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
        """Run a chat that can call defined tools via Claude tool calling.

        Tool names must be of the form 'tool_<nodeId>'.
        """
        from . import execute_node_by_type  # Avoid circular import

        url = base_url.rstrip("/") + "/v1/messages"
        messages: List[Dict[str, Any]] = [
            {"role": "user", "content": str(user_content)},
        ]

        tool_call_log: List[Dict[str, Any]] = []
        for _ in range(4):  # limit tool-exec loops
            body = {
                "model": model,
                "max_tokens": 4096,
                "temperature": temperature,
                "system": system_prompt,
                "messages": messages,
                "tools": tool_defs,
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

            content_blocks = data.get("content", [])
            stop_reason = data.get("stop_reason")

            # Check for tool use
            tool_uses = [block for block in content_blocks if block.get("type") == "tool_use"]

            if tool_uses and stop_reason == "tool_use":
                # Add assistant message with tool uses
                messages.append({
                    "role": "assistant",
                    "content": content_blocks,
                })

                # Execute tools and collect results
                tool_results = []
                for tool_use in tool_uses:
                    tool_id = tool_use.get("id")
                    name = tool_use.get("name", "")
                    args = tool_use.get("input", {})

                    node_id = name.replace("tool_", "", 1)
                    node = tool_nodes.get(str(node_id))
                    if not node:
                        res_obj = {"status": "error", "error": f"unknown tool {name}"}
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
                        except Exception as exc:
                            res_obj = {"status": "error", "error": str(exc)}

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": json.dumps(res_obj),
                    })
                    tool_call_log.append({
                        "name": name,
                        "args": args,
                        "result": res_obj,
                    })

                # Add tool results as user message
                messages.append({
                    "role": "user",
                    "content": tool_results,
                })
                # continue loop for follow-up
                continue

            # no tool calls -> final content
            text_blocks = [block.get("text", "") for block in content_blocks if block.get("type") == "text"]
            final_text = " ".join(text_blocks)
            return (final_text, tool_call_log)

        # loop exhausted
        return ("", tool_call_log)

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        input_text = context.get("input", "")
        data = (node.get("data") or {})
        label = data.get("label", "Claude Agent")
        knowledge = context.get("knowledge") or {}
        tools = context.get("tools") or []

        api_key = os.getenv("ANTHROPIC_API_KEY")
        base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        # Default to requested Claude Sonnet model if none specified in node data
        model = data.get("model") or "claude-sonnet-4-5-20250929"
        temperature_val = self._get_temperature(data)
        system_prompt = self._build_system_prompt(data, knowledge)

        if not api_key:
            return self._fallback_response(input_text, label, knowledge, tools, "Anthropic API key not configured")

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        try:
            # If agent_tools are provided, enable tool calling
            agent_tools: List[Dict[str, Any]] = context.get("agent_tools") or []
            tool_nodes: Dict[str, Any] = context.get("agent_tool_nodes") or {}
            call_log: List[Dict[str, Any]] = []  # Initialize call_log

            if agent_tools:
                tool_defs: List[Dict[str, Any]] = []
                for t in agent_tools:
                    tid = str(t.get("nodeId"))
                    tname = t.get("name") or t.get("label") or f"Tool {tid}"
                    tool_defs.append({
                        "name": f"tool_{tid}",
                        "description": f"Invoke connected tool '{tname}'",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "input": {"type": ["string", "null"], "description": "Optional input override"},
                                "params": {"type": "object", "description": "Optional parameters"},
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
                    "max_tokens": 4096,
                    "temperature": temperature_val,
                    "system": system_prompt,
                    "messages": [
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
            return self._fallback_response(input_text, label, knowledge, tools, f"Claude error: {exc}")
