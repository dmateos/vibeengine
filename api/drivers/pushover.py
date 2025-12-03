from typing import Any, Dict
import logging
import requests

from .base import BaseDriver, DriverResponse

logger = logging.getLogger(__name__)


class PushoverDriver(BaseDriver):
    type = "pushover"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        node_id = node.get("id", "unknown")
        data = node.get("data") or {}
        label = data.get("label", "Pushover")

        logger.info(f"[Pushover] Node: {label} ({node_id})")

        # Get configuration
        user_key = data.get("user_key", "").strip()
        api_token = data.get("api_token", "").strip()
        title = data.get("title", "").strip()
        priority = data.get("priority", 0)
        sound = data.get("sound", "").strip()
        device = data.get("device", "").strip()
        url = data.get("url", "").strip()
        url_title = data.get("url_title", "").strip()

        # Get message from input or configured message
        message_template = data.get("message", "").strip()
        input_val = context.get("input", "")

        # If message template is empty, use input as message
        if not message_template:
            message = str(input_val)
        else:
            # Allow {input} placeholder in message template
            message = message_template.replace("{input}", str(input_val))

        # Validate required fields
        if not user_key:
            return DriverResponse({
                "status": "error",
                "error": "Pushover user key is required",
            })

        if not api_token:
            return DriverResponse({
                "status": "error",
                "error": "Pushover API token is required",
            })

        if not message:
            return DriverResponse({
                "status": "error",
                "error": "Message is required (from input or message field)",
            })

        # Validate priority
        try:
            priority = int(priority)
            if priority not in [-2, -1, 0, 1, 2]:
                priority = 0
        except (ValueError, TypeError):
            priority = 0

        # Build request payload
        payload = {
            "token": api_token,
            "user": user_key,
            "message": message,
        }

        # Add optional fields
        if title:
            payload["title"] = title
        if priority != 0:
            payload["priority"] = priority
        if sound:
            payload["sound"] = sound
        if device:
            payload["device"] = device
        if url:
            payload["url"] = url
            if url_title:
                payload["url_title"] = url_title

        # Send notification
        try:
            logger.debug(f"[Pushover] Sending notification to user {user_key[:8]}...")

            response = requests.post(
                "https://api.pushover.net/1/messages.json",
                data=payload,
                timeout=10
            )

            response_data = response.json()

            if response.status_code == 200 and response_data.get("status") == 1:
                logger.info(f"[Pushover] Notification sent successfully")
                return DriverResponse({
                    "status": "ok",
                    "output": {
                        "sent": True,
                        "message": message,
                        "title": title or None,
                        "request_id": response_data.get("request"),
                    }
                })
            else:
                errors = response_data.get("errors", ["Unknown error"])
                error_message = ", ".join(errors)
                logger.error(f"[Pushover] API error: {error_message}")
                return DriverResponse({
                    "status": "error",
                    "error": f"Pushover API error: {error_message}",
                })

        except requests.exceptions.Timeout:
            logger.error(f"[Pushover] Request timed out")
            return DriverResponse({
                "status": "error",
                "error": "Pushover API request timed out",
            })
        except requests.exceptions.RequestException as e:
            logger.error(f"[Pushover] Request failed: {str(e)}")
            return DriverResponse({
                "status": "error",
                "error": f"Pushover request failed: {str(e)}",
            })
        except Exception as e:
            logger.error(f"[Pushover] Unexpected error: {str(e)}")
            return DriverResponse({
                "status": "error",
                "error": f"Pushover error: {str(e)}",
            })
