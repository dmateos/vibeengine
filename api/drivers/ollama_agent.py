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
        except Exception as e:
            # Try to provide more detailed error information
            error_details = self._parse_api_error(e, "Ollama", base_url)
            raise Exception(error_details) from e

        try:
            # Ollama chat returns {message:{role,content}, ...}
            msg = (data.get("message") or {})
            return msg.get("content", "")
        except Exception:
            return ""

    def _parse_api_error(self, exc: Exception, provider: str, base_url: str) -> str:
        """Parse API errors and return a helpful error message."""
        try:
            import requests
            if isinstance(exc, requests.exceptions.HTTPError):
                status_code = exc.response.status_code
                try:
                    error_data = exc.response.json()
                    error_msg = error_data.get("error", str(exc))

                    if status_code == 404:
                        if "model" in error_msg.lower():
                            return f"{provider}: Model not found (404). The model may not be installed. Run 'ollama pull <model-name>' to download it."
                        return f"{provider}: Not found (404). Check that Ollama is running at {base_url}"
                    elif status_code == 400:
                        return f"{provider}: Bad request (400). {error_msg}"
                    elif status_code >= 500:
                        return f"{provider}: Server error ({status_code}). Ollama may be overloaded or crashed."
                    else:
                        return f"{provider} error ({status_code}): {error_msg}"
                except:
                    if status_code == 404:
                        return f"{provider}: Connection failed (404). Make sure Ollama is running at {base_url}"
                    return f"{provider} error ({status_code}): {str(exc)}"
            elif isinstance(exc, requests.exceptions.Timeout):
                return f"{provider}: Request timeout. The model may be too slow or Ollama may be overloaded (>60s)."
            elif isinstance(exc, requests.exceptions.ConnectionError):
                return f"{provider}: Connection refused. Is Ollama running at {base_url}? Start it with 'ollama serve'"
            elif isinstance(exc, requests.exceptions.RequestException):
                return f"{provider}: Request failed - {str(exc)}"
        except:
            pass

        # Handle urllib errors
        try:
            import urllib.error
            if isinstance(exc, urllib.error.HTTPError):
                status_code = exc.code
                if status_code == 404:
                    return f"{provider}: Connection failed (404). Make sure Ollama is running at {base_url}"
                try:
                    error_data = json.loads(exc.read().decode('utf-8'))
                    error_msg = error_data.get("error", str(exc))
                    return f"{provider} error ({status_code}): {error_msg}"
                except:
                    return f"{provider} error ({status_code}): {str(exc)}"
            elif isinstance(exc, urllib.error.URLError):
                return f"{provider}: Connection failed - {str(exc.reason)}. Is Ollama running at {base_url}?"
        except:
            pass

        # Fallback to generic error
        return f"{provider} connection failed: {str(exc)}. Check that Ollama is running at {base_url}"

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

