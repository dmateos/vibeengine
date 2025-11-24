from typing import Any, Dict
import re
from .base import BaseDriver, DriverResponse


class ConditionDriver(BaseDriver):
    """
    Condition node driver that evaluates expressions and routes accordingly.

    The condition node evaluates an expression against the current context
    and routes to 'yes' or 'no' based on the result.

    Configuration (node.data):
        expression: String expression to evaluate
            - Simple comparisons: "input.length > 100"
            - Contains check: "input contains 'urgent'"
            - State checks: "state.count >= 3"
            - Param checks: "params.tier == 'premium'"
            - Boolean combinations: "state.active and input.length > 0"

    Supported operators:
        - Comparison: >, <, >=, <=, ==, !=
        - String: contains, startswith, endswith
        - Boolean: and, or, not
        - Membership: in

    Returns:
        DriverResponse with:
            - route: 'yes' or 'no'
            - status: 'ok'
    """
    type = "condition"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        """
        Execute the condition node by evaluating the configured expression.
        """
        data = node.get('data') or {}
        expression = data.get('expression', '')

        if not expression:
            # No expression, default to 'no'
            return DriverResponse({
                "status": "ok",
                "route": "no",
            })

        try:
            result = self._evaluate_expression(expression, context)
            route = "yes" if result else "no"
        except Exception as e:
            # On error, route to 'no' and include error in response
            return DriverResponse({
                "status": "ok",
                "route": "no",
                "error": f"Expression evaluation failed: {str(e)}",
            })

        return DriverResponse({
            "status": "ok",
            "route": route,
        })

    def _evaluate_expression(self, expression: str, context: Dict[str, Any]) -> bool:
        """Safely evaluate an expression against the context."""
        # Get values from context
        input_val = context.get('input', '')
        state = context.get('state', {})
        params = context.get('params', {})

        # Create safe evaluation namespace
        namespace = {
            'input': input_val,
            'state': state,
            'params': params,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'True': True,
            'False': False,
            'None': None,
        }

        # Handle string operations that aren't valid Python
        expression = self._preprocess_expression(expression)

        # Safely evaluate
        try:
            result = eval(expression, {"__builtins__": {}}, namespace)
            return bool(result)
        except Exception as e:
            raise ValueError(f"Invalid expression: {expression}") from e

    def _preprocess_expression(self, expr: str) -> str:
        """Convert user-friendly syntax to Python expressions."""
        # Convert "contains" to "in"
        # "input contains 'text'" -> "'text' in str(input)"
        expr = re.sub(
            r'(\w+(?:\.\w+)*)\s+contains\s+(["\'])(.*?)\2',
            r'"\3" in str(\1)',
            expr
        )

        # Convert "startswith"
        # "input startswith 'text'" -> "str(input).startswith('text')"
        expr = re.sub(
            r'(\w+(?:\.\w+)*)\s+startswith\s+(["\'])(.*?)\2',
            r'str(\1).startswith("\3")',
            expr
        )

        # Convert "endswith"
        # "input endswith 'text'" -> "str(input).endswith('text')"
        expr = re.sub(
            r'(\w+(?:\.\w+)*)\s+endswith\s+(["\'])(.*?)\2',
            r'str(\1).endswith("\3")',
            expr
        )

        # Convert "and"/"or" if they're standalone (Python already supports these)
        # No conversion needed for these

        # Handle attribute access for complex paths
        # state.user.age -> state.get('user', {}).get('age')
        # This is more complex, for now we'll rely on Python's dict access

        return expr
