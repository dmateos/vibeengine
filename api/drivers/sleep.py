"""
Sleep driver for pausing workflow execution.
"""

import time
from typing import Dict, Any
from .base import BaseDriver, DriverResponse


class SleepDriver(BaseDriver):
    type = "sleep"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        """Pause execution for specified duration."""
        # Get configuration
        duration = float(node.get("data", {}).get("duration", 1.0))
        unit = node.get("data", {}).get("unit", "seconds")

        # Convert to seconds based on unit
        if unit == "milliseconds":
            sleep_seconds = duration / 1000.0
        elif unit == "seconds":
            sleep_seconds = duration
        elif unit == "minutes":
            sleep_seconds = duration * 60.0
        elif unit == "hours":
            sleep_seconds = duration * 3600.0
        else:
            return DriverResponse({
                "status": "error",
                "error": f"Invalid time unit: {unit}. Use 'milliseconds', 'seconds', 'minutes', or 'hours'."
            })

        # Validate duration
        if sleep_seconds < 0:
            return DriverResponse({
                "status": "error",
                "error": "Duration must be positive"
            })

        if sleep_seconds > 3600:  # Max 1 hour
            return DriverResponse({
                "status": "error",
                "error": "Duration cannot exceed 1 hour (3600 seconds)"
            })

        try:
            # Sleep for the specified duration
            time.sleep(sleep_seconds)

            # Pass through the input as output
            input_data = context.get("input", "")

            return DriverResponse({
                "status": "ok",
                "output": input_data,
                "slept_seconds": sleep_seconds,
                "unit": unit,
                "original_duration": duration,
            })

        except Exception as e:
            return DriverResponse({
                "status": "error",
                "error": f"Sleep error: {str(e)}"
            })
