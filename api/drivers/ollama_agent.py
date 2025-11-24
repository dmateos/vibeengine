from typing import Any, Dict, List
import os
import json
from .base import BaseAgentDriver, DriverResponse


class OllamaAgentDriver(BaseAgentDriver):
    type = "ollama_agent"

    def _post_chat(self, base_url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> str:
        """Post a chat request to Ollama and return content.

        API: POST {base_url}/api/chat with body {model, messages, stream:false, options:{temperature}}
        """
        url = base_url.rstrip("/") + "/api/chat"
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
            # Ollama chat returns {message:{role,content}, ...}
            msg = (data.get("message") or {})
            return msg.get("content", "")
        except Exception:
            return ""

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        input_text = context.get("input", "")
        data = (node.get("data") or {})
        label = data.get("label", "Ollama Agent")
        knowledge = context.get("knowledge") or {}

        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = data.get("model") or os.getenv("OLLAMA_MODEL", "llama3.1:8b-instruct")
        temperature_val = self._get_temperature(data)
        system_prompt = self._build_system_prompt(data, knowledge)

        # Ollama does not require API keys by default (local runtime)
        headers = {"Content-Type": "application/json"}

        try:
            body = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": str(input_text)},
                ],
                "stream": False,
                "options": {"temperature": temperature_val},
            }
            content = self._post_chat(base_url, body, headers)
            return DriverResponse({
                "output": content,
                "model": model,
                "status": "ok",
            })
        except Exception as exc:
            # Check if node configured to continue on error
            continue_on_error = data.get('continue_on_error', False)
            error_msg = f"Ollama connection failed: {str(exc)}"

            if continue_on_error:
                # Continue workflow but track the error
                return DriverResponse({
                    "status": "ok",
                    "output": input_text,  # Pass through input
                    "error": error_msg,
                    "error_type": "connection_error",
                    "had_error": True,
                })
            else:
                # Stop workflow on error
                return DriverResponse({
                    "status": "error",
                    "error": error_msg,
                    "output": input_text,
                    "error_type": "connection_error",
                })

