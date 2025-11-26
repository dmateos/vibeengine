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
        except Exception as e:
            # Try to provide more detailed error information
            error_details = self._parse_api_error(e, "OpenAI")
            raise Exception(error_details) from e

        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            # try the legacy completion shape
            return data.get("choices", [{}])[0].get("text", "")

    def _parse_api_error(self, exc: Exception, provider: str) -> str:
        """Parse API errors and return a helpful error message."""
        try:
            import requests
            if isinstance(exc, requests.exceptions.HTTPError):
                status_code = exc.response.status_code
                try:
                    error_data = exc.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(exc))
                    error_type = error_data.get("error", {}).get("type", "")
                    error_code = error_data.get("error", {}).get("code", "")

                    if status_code == 401:
                        return f"{provider} API: Invalid API key (401 Unauthorized). Check your OPENAI_API_KEY environment variable."
                    elif status_code == 429:
                        return f"{provider} API: Rate limit exceeded (429). Please wait and try again later."
                    elif status_code == 400:
                        return f"{provider} API: Bad request (400). {error_msg}"
                    elif status_code == 404:
                        if "model" in error_msg.lower():
                            return f"{provider} API: Model not found (404). Check that the model name is correct."
                        return f"{provider} API: Not found (404). {error_msg}"
                    elif status_code >= 500:
                        return f"{provider} API: Server error ({status_code}). The API service may be temporarily unavailable."
                    else:
                        return f"{provider} API error ({status_code}): {error_msg}"
                except:
                    return f"{provider} API error ({status_code}): {str(exc)}"
            elif isinstance(exc, requests.exceptions.Timeout):
                return f"{provider} API: Request timeout. The API took too long to respond (>60s)."
            elif isinstance(exc, requests.exceptions.ConnectionError):
                return f"{provider} API: Connection failed. Check your network connection and the API base URL."
            elif isinstance(exc, requests.exceptions.RequestException):
                return f"{provider} API: Request failed - {str(exc)}"
        except:
            pass

        # Handle urllib errors
        try:
            import urllib.error
            if isinstance(exc, urllib.error.HTTPError):
                status_code = exc.code
                try:
                    error_data = json.loads(exc.read().decode('utf-8'))
                    error_msg = error_data.get("error", {}).get("message", str(exc))

                    if status_code == 401:
                        return f"{provider} API: Invalid API key (401 Unauthorized)."
                    elif status_code == 429:
                        return f"{provider} API: Rate limit exceeded (429)."
                    elif status_code >= 500:
                        return f"{provider} API: Server error ({status_code})."
                    else:
                        return f"{provider} API error ({status_code}): {error_msg}"
                except:
                    return f"{provider} API error ({status_code}): {str(exc)}"
            elif isinstance(exc, urllib.error.URLError):
                return f"{provider} API: Connection failed - {str(exc.reason)}"
        except:
            pass

        # Fallback to generic error
        return f"{provider} API failed: {str(exc)}"

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
            except Exception as e:
                # Try to provide more detailed error information
                error_details = self._parse_api_error(e, "OpenAI")
                raise Exception(error_details) from e

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
                    if name.startswith("memory_"):
                        # Handle memory writes using connected memory node config
                        memory_nodes = shared_context.get("agent_memory_node_map") or {}
                        mem_id = name.replace("memory_", "", 1)
                        mnode = memory_nodes.get(str(mem_id))
                        if not mnode:
                            res_obj = {"status": "error", "error": f"unknown memory node {name}"}
                            content = json.dumps(res_obj)
                        else:
                            mdata = mnode.get("data") or {}
                            key = mdata.get("key", "memory")
                            namespace = mdata.get("namespace") or "default"
                            mode = (args.get("mode") or "replace").lower()
                            dedupe = bool(args.get("dedupe", True))
                            value = args.get("value")
                            from ..memory_store import store as _store
                            store_key = f"{namespace}:{key}"
                            previous = _store.get(store_key)
                            try:
                                if mode == "append":
                                    base = previous if isinstance(previous, list) else ([] if previous is None else [previous])
                                    merged = list(base)
                                    vals = value if isinstance(value, list) else [value]
                                    if dedupe:
                                        for v in vals:
                                            if v not in merged:
                                                merged.append(v)
                                    else:
                                        merged.extend(vals)
                                    _store.set(store_key, merged)
                                    stored = merged
                                elif mode == "merge" and isinstance(value, dict):
                                    base = previous if isinstance(previous, dict) else {}
                                    base.update(value)
                                    _store.set(store_key, base)
                                    stored = base
                                else:
                                    _store.set(store_key, value)
                                    stored = value
                                res_obj = {"status": "ok", "operation": "memory_write", "key": key, "namespace": namespace, "previous": previous, "stored": stored}
                            except Exception as exc:
                                res_obj = {"status": "error", "error": str(exc)}
                            content = json.dumps(res_obj)
                    else:
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

            mem_specs: List[Dict[str, Any]] = context.get("agent_memory_nodes") or []

            if agent_tools or mem_specs:
                tool_defs: List[Dict[str, Any]] = []
                for t in agent_tools:
                    tid = str(t.get("nodeId"))
                    tname = t.get("name") or t.get("label") or f"Tool {tid}"
                    params_schema: Dict[str, Any] = {
                        "type": "object",
                        "properties": {
                            "input": {"type": ["string", "null"], "description": "Optional input override"},
                            "params": {"type": "object", "description": "Optional parameters"},
                        },
                    }
                    tool_defs.append({
                        "type": "function",
                        "function": {
                            "name": f"tool_{tid}",
                            "description": f"Invoke connected tool '{tname}'",
                            "parameters": params_schema,
                        },
                    })
                # Add memory node functions
                for m in mem_specs:
                    mid = str(m.get("nodeId"))
                    key = m.get("key")
                    namespace = m.get("namespace")
                    tool_defs.append({
                        "type": "function",
                        "function": {
                            "name": f"memory_{mid}",
                            "description": f"Persist extracted info to memory key '{key}' in namespace '{namespace}'.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": ["string","number","boolean","object","array","null"], "description": "Data to store (any JSON)"},
                                    "mode": {"type": "string", "enum": ["replace","append","merge"], "description": "Replace, append to list, or merge objects"},
                                    "dedupe": {"type": ["boolean","null"], "description": "De-duplicate when appending lists"},
                                },
                                "required": ["value"],
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
            resp = DriverResponse({
                "output": content,
                "model": model,
                "tool_call_log": call_log,
                "status": "ok",
            })
            # Note: no passive memory writes; LLM decides via memory_* function calls
            # Optional console debug of tool calls
            if call_log and os.getenv("DEBUG_TOOL_CALLS"):
                try:
                    print("[OpenAIAgentDriver] tool calls:", json.dumps(call_log)[:2000])
                except Exception:
                    pass
            return resp
        except Exception as exc:
            # Check if node configured to continue on error
            continue_on_error = data.get('continue_on_error', False)
            error_msg = f"OpenAI API failed: {str(exc)}"

            if continue_on_error:
                # Continue workflow but track the error
                return DriverResponse({
                    "status": "ok",
                    "output": input_text,
                    "error": error_msg,
                    "error_type": "api_error",
                    "had_error": True,
                })
            else:
                # Stop workflow on error
                return DriverResponse({
                    "status": "error",
                    "error": error_msg,
                    "output": input_text,
                    "error_type": "api_error",
                })
