from typing import Any, Dict
import json
from .base import BaseDriver, DriverResponse


class JSONValidatorDriver(BaseDriver):
    type = "json_validator"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        input_data = context.get("input", "")
        data = node.get("data") or {}
        schema_str = data.get("schema", "{}")
        route_on_validation = data.get("route_on_validation", False)

        # Try to parse input as JSON
        try:
            if isinstance(input_data, str):
                json_data = json.loads(input_data)
            else:
                json_data = input_data
        except (json.JSONDecodeError, TypeError) as e:
            return DriverResponse({
                "status": "ok",
                "output": input_data,
                "valid": False,
                "errors": [f"Invalid JSON input: {str(e)}"],
                "route": "invalid" if route_on_validation else None
            })

        # Try to parse schema
        try:
            schema = json.loads(schema_str) if isinstance(schema_str, str) else schema_str
        except (json.JSONDecodeError, TypeError) as e:
            return DriverResponse({
                "status": "ok",
                "output": input_data,
                "valid": False,
                "errors": [f"Invalid JSON schema: {str(e)}"],
                "route": "invalid" if route_on_validation else None
            })

        # Validate JSON against schema
        try:
            import jsonschema
            jsonschema.validate(instance=json_data, schema=schema)

            return DriverResponse({
                "status": "ok",
                "output": input_data,
                "valid": True,
                "errors": [],
                "route": "valid" if route_on_validation else None
            })
        except jsonschema.exceptions.ValidationError as e:
            error_path = ".".join(str(p) for p in e.path) if e.path else "root"
            error_msg = f"{error_path}: {e.message}"

            return DriverResponse({
                "status": "ok",
                "output": input_data,
                "valid": False,
                "errors": [error_msg],
                "route": "invalid" if route_on_validation else None
            })
        except Exception as e:
            return DriverResponse({
                "status": "ok",
                "output": input_data,
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "route": "invalid" if route_on_validation else None
            })
