"""
Webhook driver for sending HTTP requests to external services.
"""

import os
import json
import requests
from typing import Dict, Any
from .base import BaseDriver, DriverResponse


class WebhookDriver(BaseDriver):
    type = "webhook"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        """Send HTTP request to configured webhook URL."""
        # Get configuration
        url = node.get("data", {}).get("url", "")
        method = node.get("data", {}).get("method", "POST").upper()
        headers_str = node.get("data", {}).get("headers", "")
        body_template = node.get("data", {}).get("body", "")
        timeout = int(node.get("data", {}).get("timeout", 30))
        auth_type = node.get("data", {}).get("auth_type", "none")
        auth_token = node.get("data", {}).get("auth_token", "")

        # Support {input} placeholder in URL and body
        input_data = context.get("input", "")
        if isinstance(input_data, (dict, list)):
            input_str = json.dumps(input_data)
        else:
            input_str = str(input_data)

        url = url.replace("{input}", input_str) if url else ""
        body_template = body_template.replace("{input}", input_str) if body_template else input_str

        if not url:
            return DriverResponse({
                "status": "error",
                "error": "Webhook URL is required"
            })

        try:
            # Parse headers
            headers = {}
            if headers_str:
                try:
                    # Try JSON format first
                    headers = json.loads(headers_str)
                except json.JSONDecodeError:
                    # Fall back to line-by-line format: "Key: Value"
                    for line in headers_str.strip().split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            headers[key.strip()] = value.strip()

            # Add authentication
            if auth_type == "bearer" and auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            elif auth_type == "token" and auth_token:
                headers["Authorization"] = f"Token {auth_token}"
            elif auth_type == "api_key" and auth_token:
                headers["X-API-Key"] = auth_token

            # Prepare request
            request_args = {
                "url": url,
                "headers": headers,
                "timeout": timeout,
            }

            # Parse body based on method
            if method in ["POST", "PUT", "PATCH"]:
                # Try to parse as JSON first
                try:
                    body_data = json.loads(body_template)
                    request_args["json"] = body_data
                    if "Content-Type" not in headers:
                        headers["Content-Type"] = "application/json"
                except json.JSONDecodeError:
                    # Send as plain text
                    request_args["data"] = body_template
                    if "Content-Type" not in headers:
                        headers["Content-Type"] = "text/plain"

            # Make request
            if method == "GET":
                response = requests.get(**request_args)
            elif method == "POST":
                response = requests.post(**request_args)
            elif method == "PUT":
                response = requests.put(**request_args)
            elif method == "PATCH":
                response = requests.patch(**request_args)
            elif method == "DELETE":
                response = requests.delete(**request_args)
            else:
                return DriverResponse({
                    "status": "error",
                    "error": f"Unsupported HTTP method: {method}"
                })

            # Parse response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = response.text

            return DriverResponse({
                "status": "ok",
                "output": response_data,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "url": url,
                "method": method,
            })

        except requests.exceptions.Timeout:
            return DriverResponse({
                "status": "error",
                "error": f"Request timed out after {timeout} seconds"
            })
        except requests.exceptions.ConnectionError as e:
            return DriverResponse({
                "status": "error",
                "error": f"Connection error: {str(e)}"
            })
        except requests.exceptions.RequestException as e:
            return DriverResponse({
                "status": "error",
                "error": f"Request failed: {str(e)}"
            })
        except Exception as e:
            return DriverResponse({
                "status": "error",
                "error": f"Webhook error: {str(e)}"
            })
