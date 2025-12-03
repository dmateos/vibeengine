from typing import Any, Dict
import logging
from .base import BaseDriver, DriverResponse

logger = logging.getLogger(__name__)


class HTMLOutputDriver(BaseDriver):
    type = "html_output"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        node_id = node.get("id", "unknown")
        data = node.get("data") or {}
        label = data.get("label", "HTML Output")

        logger.info(f"[HTML Output] Node: {label} ({node_id})")

        # Get input HTML content
        html_content = context.get("input", "")

        # Convert to string if needed
        if not isinstance(html_content, str):
            html_content = str(html_content)

        # Basic validation - check if it looks like HTML
        is_html = "<" in html_content and ">" in html_content

        if not is_html:
            logger.warning(f"[HTML Output] Input doesn't appear to be HTML")

        logger.info(f"[HTML Output] Generated HTML ({len(html_content)} characters)")
        logger.debug(f"[HTML Output] Preview: {html_content[:200]}...")

        return DriverResponse({
            "status": "ok",
            "output": html_content,
            "html": html_content,  # Store HTML for preview
            "metadata": {
                "length": len(html_content),
                "is_html": is_html,
            }
        })
