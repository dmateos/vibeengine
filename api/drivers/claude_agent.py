from typing import Any, Dict, List, Tuple
import os
import json
import logging
from .base import BaseAgentDriver, DriverResponse

logger = logging.getLogger(__name__)


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
        except Exception as e:
            # Try to provide more detailed error information
            error_details = self._parse_api_error(e, "Claude")
            raise Exception(error_details) from e

        try:
            # Extract text from content blocks
            content_blocks = data.get("content", [])
            if isinstance(content_blocks, list) and len(content_blocks) > 0:
                return content_blocks[0].get("text", "")
            return ""
        except Exception:
            return ""

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

                    if status_code == 401:
                        return f"{provider} API: Invalid API key (401 Unauthorized). Check your ANTHROPIC_API_KEY environment variable."
                    elif status_code == 429:
                        return f"{provider} API: Rate limit exceeded (429). Please wait and try again later."
                    elif status_code == 400:
                        return f"{provider} API: Bad request (400). {error_msg}"
                    elif status_code == 404:
                        return f"{provider} API: Model not found (404). Check that the model name is correct."
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
            except Exception as e:
                # Try to provide more detailed error information
                error_details = self._parse_api_error(e, "Claude")
                raise Exception(error_details) from e

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

                    if name.startswith("memory_"):
                        memory_nodes = shared_context.get("agent_memory_node_map") or {}
                        mem_id = name.replace("memory_", "", 1)
                        mnode = memory_nodes.get(str(mem_id))
                        if not mnode:
                            res_obj = {"status": "error", "error": f"unknown memory node {name}"}
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
                    else:
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
            # Optional console debug
            if tool_call_log and os.getenv("DEBUG_TOOL_CALLS"):
                try:
                    print("[ClaudeAgentDriver] tool calls:", json.dumps(tool_call_log)[:2000])
                except Exception:
                    pass
            return (final_text, tool_call_log)

        # loop exhausted
        return ("", tool_call_log)

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        input_text = context.get("input", "")
        data = (node.get("data") or {})
        label = data.get("label", "Claude Agent")
        node_id = node.get("id", "unknown")
        knowledge = context.get("knowledge") or {}
        tools = context.get("tools") or []

        logger.info(f"[Claude] Starting execution - Node: {label} ({node_id})")
        logger.debug(f"[Claude] Input: {str(input_text)[:200]}...")

        # API key: check node data first, then fall back to env var
        api_key = data.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
        base_url = data.get("base_url") or os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        # Default to requested Claude Sonnet model if none specified in node data
        model = data.get("model") or "claude-sonnet-4-5-20250929"
        temperature_val = self._get_temperature(data)
        system_prompt = self._build_system_prompt(data, knowledge)

        logger.info(f"[Claude] Using model: {model}, temperature: {temperature_val}, base_url: {base_url}")
        logger.debug(f"[Claude] API key source: {'node config' if data.get('api_key') else 'env var'}")

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

            mem_specs: List[Dict[str, Any]] = context.get("agent_memory_nodes") or []

            if agent_tools or mem_specs:
                tool_defs: List[Dict[str, Any]] = []
                for t in agent_tools:
                    tid = str(t.get("nodeId"))
                    tname = t.get("name") or t.get("label") or f"Tool {tid}"
                    input_schema = {
                        "type": "object",
                        "properties": {
                            "input": {"type": ["string", "null"], "description": "Optional input override"},
                            "params": {"type": "object", "description": "Optional parameters"},
                        },
                    }
                    tool_defs.append({
                        "name": f"tool_{tid}",
                        "description": f"Invoke connected tool '{tname}'",
                        "input_schema": input_schema,
                    })
                # Add memory node functions
                for m in mem_specs:
                    mid = str(m.get("nodeId"))
                    key = m.get("key")
                    namespace = m.get("namespace")
                    tool_defs.append({
                        "name": f"memory_{mid}",
                        "description": f"Persist extracted info to memory key '{key}' in namespace '{namespace}'.",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "value": {"type": ["string","number","boolean","object","array","null"], "description": "Data to store (any JSON)"},
                                "mode": {"type": "string", "enum": ["replace","append","merge"], "description": "Replace, append to list, or merge objects"},
                                "dedupe": {"type": ["boolean","null"], "description": "De-duplicate when appending lists"},
                            },
                            "required": ["value"],
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
            logger.info(f"[Claude] Execution completed - Node: {label} ({node_id})")
            logger.debug(f"[Claude] Output: {str(content)[:200]}...")
            if call_log:
                logger.info(f"[Claude] Tool calls made: {len(call_log)}")
                logger.debug(f"[Claude] Tool call log: {json.dumps(call_log)[:500]}...")

            resp = DriverResponse({
                "output": content,
                "model": model,
                "tool_call_log": call_log,
                "status": "ok",
            })
            return resp
        except Exception as exc:
            # Check if node configured to continue on error
            continue_on_error = data.get('continue_on_error', False)
            error_msg = f"Claude API failed: {str(exc)}"

            logger.error(f"[Claude] Error in node {label} ({node_id}): {error_msg}")

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
