from typing import Any, Dict, List
import os
import json
from .base import BaseDriver, DriverResponse
from ..memory_store import store


class ToolDriver(BaseDriver):
    type = "tool"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        data = (node.get("data") or {})
        operation = data.get("operation") or "echo"
        arg = data.get("arg") or ""
        input_val = context.get("input")
        tool_name = data.get("label", "Tool")

        try:
            if operation in ("save_memory", "set_memory", "append_memory"):
                # Persist value into the MemoryStore.
                # Accept overrides via context.params or node.data defaults.
                params = context.get("params") or {}
                key = params.get("key") or data.get("key") or "memory"
                namespace = params.get("namespace") or data.get("namespace") or "default"
                # Value precedence: explicit params.value > context.input
                value = params.get("value", input_val)
                append = bool(params.get("append") or (operation == "append_memory"))

                store_key = f"{namespace}:{key}"
                previous = store.get(store_key)

                if append:
                    # Append to a list, creating if needed, and de-duplicate while preserving order
                    base = previous if isinstance(previous, list) else []
                    # Normalize to list when value is scalar
                    values = value if isinstance(value, list) else [value]
                    merged = list(base)
                    for v in values:
                        if v not in merged:
                            merged.append(v)
                    store.set(store_key, merged)
                    stored = merged
                else:
                    store.set(store_key, value)
                    stored = value

                return DriverResponse({
                    "status": "ok",
                    "tool": tool_name,
                    "operation": operation,
                    "key": key,
                    "namespace": namespace,
                    "previous": previous,
                    "stored": stored,
                    # Pass-through original input
                    "output": input_val,
                })

            if operation == "google_search":
                # Google Programmable Search (CSE) API
                api_key = os.getenv("GOOGLE_API_KEY")
                cse_id = os.getenv("GOOGLE_CSE_ID")

                if not api_key or not cse_id:
                    return DriverResponse({
                        "status": "error",
                        "error": "Google search not configured: set GOOGLE_API_KEY and GOOGLE_CSE_ID",
                    })

                q_base = input_val if isinstance(input_val, str) else ""
                # Optional extra query or site: filter from node arg
                if isinstance(arg, str) and arg:
                    q_base = (q_base + " " + arg).strip()
                # Allow overriding via params
                params = context.get("params") or {}
                q = params.get("query") or params.get("q") or q_base
                num = int(params.get("num", 5))
                num = max(1, min(10, num))

                try:
                    import requests  # type: ignore

                    resp = requests.get(
                        "https://www.googleapis.com/customsearch/v1",
                        params={"q": q, "key": api_key, "cx": cse_id, "num": num},
                        timeout=15,
                    )
                    resp.raise_for_status()
                    data_payload = resp.json()
                except Exception:
                    # Fallback to urllib
                    import urllib.parse
                    import urllib.request

                    qs = urllib.parse.urlencode({
                        "q": q,
                        "key": api_key,
                        "cx": cse_id,
                        "num": num,
                    })
                    req = urllib.request.Request(
                        f"https://www.googleapis.com/customsearch/v1?{qs}"
                    )
                    with urllib.request.urlopen(req, timeout=15) as f:  # type: ignore
                        data_payload = json.loads(f.read().decode("utf-8"))

                items: List[Dict[str, Any]] = []
                for it in (data_payload.get("items") or [])[:num]:
                    items.append({
                        "title": it.get("title"),
                        "link": it.get("link"),
                        "snippet": it.get("snippet"),
                        "displayLink": it.get("displayLink"),
                    })

                return DriverResponse({
                    "status": "ok",
                    "output": {"results": items, "query": q, "count": len(items)},
                    "tool": tool_name,
                })

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
