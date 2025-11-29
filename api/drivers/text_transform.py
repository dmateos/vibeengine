from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)
import re
from .base import BaseDriver, DriverResponse


class TextTransformDriver(BaseDriver):
    type = "text_transform"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        node_id = node.get("id", "unknown")
        input_text = context.get("input", "")
        data = node.get("data") or {}
        label = data.get("label", "Text Transform")

        operation = data.get("operation", "upper")

        logger.info(f"[Text Transform] Node: {label} ({node_id}) - Operation: {operation}")
        logger.debug(f"[Text Transform] Input: {str(input_text)[:100]}...")

        try:
            # String replacement
            if operation == "replace":
                find = data.get("find", "")
                replace_with = data.get("replace_with", "")

                if not find:
                    return DriverResponse({
                        "status": "error",
                        "error": "Replace operation requires 'find' parameter",
                        "output": input_text,
                    })

                output = str(input_text).replace(find, replace_with)

                return DriverResponse({
                    "status": "ok",
                    "output": output,
                    "operation": operation,
                })

            # Regex replace
            elif operation == "regex_replace":
                pattern = data.get("pattern", "")
                replace_with = data.get("replace_with", "")

                if not pattern:
                    return DriverResponse({
                        "status": "error",
                        "error": "Regex replace requires 'pattern' parameter",
                        "output": input_text,
                    })

                output = re.sub(pattern, replace_with, str(input_text))

                return DriverResponse({
                    "status": "ok",
                    "output": output,
                    "operation": operation,
                })

            # Regex extract
            elif operation == "regex_extract":
                pattern = data.get("pattern", "")

                if not pattern:
                    return DriverResponse({
                        "status": "error",
                        "error": "Regex extract requires 'pattern' parameter",
                        "output": input_text,
                    })

                matches = re.findall(pattern, str(input_text))
                output = "\n".join(matches) if matches else ""

                return DriverResponse({
                    "status": "ok",
                    "output": output,
                    "matches": matches,
                    "count": len(matches),
                    "operation": operation,
                })

            # Filter lines
            elif operation == "filter_lines":
                pattern = data.get("pattern", "")

                if not pattern:
                    return DriverResponse({
                        "status": "error",
                        "error": "Filter lines requires 'pattern' parameter",
                        "output": input_text,
                    })

                lines = str(input_text).split("\n")
                filtered = [line for line in lines if re.search(pattern, line)]
                output = "\n".join(filtered)

                return DriverResponse({
                    "status": "ok",
                    "output": output,
                    "matched_lines": len(filtered),
                    "total_lines": len(lines),
                    "operation": operation,
                })

            # Uppercase
            elif operation == "upper":
                output = str(input_text).upper()

                return DriverResponse({
                    "status": "ok",
                    "output": output,
                    "operation": operation,
                })

            # Lowercase
            elif operation == "lower":
                output = str(input_text).lower()

                return DriverResponse({
                    "status": "ok",
                    "output": output,
                    "operation": operation,
                })

            # Trim whitespace
            elif operation == "trim":
                output = str(input_text).strip()

                return DriverResponse({
                    "status": "ok",
                    "output": output,
                    "operation": operation,
                })

            # Split by delimiter
            elif operation == "split":
                delimiter = data.get("delimiter", ",")
                parts = str(input_text).split(delimiter)
                output = "\n".join(parts)

                return DriverResponse({
                    "status": "ok",
                    "output": output,
                    "parts": parts,
                    "count": len(parts),
                    "operation": operation,
                })

            # Substring
            elif operation == "substring":
                start = data.get("start", 0)
                end = data.get("end", None)

                try:
                    start = int(start)
                    end = int(end) if end is not None and end != "" else None
                except (ValueError, TypeError):
                    return DriverResponse({
                        "status": "error",
                        "error": "Start and end must be integers",
                        "output": input_text,
                    })

                if end is not None:
                    output = str(input_text)[start:end]
                else:
                    output = str(input_text)[start:]

                return DriverResponse({
                    "status": "ok",
                    "output": output,
                    "operation": operation,
                })

            # Length
            elif operation == "length":
                length = len(str(input_text))
                output = str(length)

                return DriverResponse({
                    "status": "ok",
                    "output": output,
                    "length": length,
                    "operation": operation,
                })

            # Join lines
            elif operation == "join":
                delimiter = data.get("delimiter", " ")
                lines = str(input_text).split("\n")
                output = delimiter.join(lines)

                return DriverResponse({
                    "status": "ok",
                    "output": output,
                    "operation": operation,
                })

            else:
                logger.error(f"[Text Transform] Unknown operation: {operation}")
                return DriverResponse({
                    "status": "error",
                    "error": f"Unknown operation: {operation}",
                    "output": input_text,
                })

        except re.error as exc:
            logger.error(f"[Text Transform] Invalid regex: {str(exc)}")
            return DriverResponse({
                "status": "error",
                "error": f"Invalid regex pattern: {str(exc)}",
                "output": input_text,
            })
        except Exception as exc:
            logger.error(f"[Text Transform] Error: {str(exc)}")
            return DriverResponse({
                "status": "error",
                "error": f"Text transform error: {str(exc)}",
                "output": input_text,
            })
