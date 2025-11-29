from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)
from .base import BaseDriver, DriverResponse


class JoinDriver(BaseDriver):
    """
    Join node driver that combines multiple values into one output.

    Primary use: Merge results from parallel branches (automatic)
    Also supports: Combining arbitrary values from context

    Configuration (node.data):
        merge_strategy: How to combine values
            - 'list': Collect all outputs as a list (default)
            - 'concat': Concatenate string outputs
            - 'first': Use first value
            - 'last': Use last value
            - 'merge': Merge dict outputs (shallow merge)
            - 'join': Join strings with separator

        separator: String separator for 'join' strategy (default: '')

        sources: List of sources to combine (optional)
            - If not specified, uses parallel_results (default behavior)
            - ['input'] - use current input
            - ['state.varname'] - use context.state['varname']
            - ['parallel_results'] - use parallel results
            - ['params.key'] - use context.params['key']

    Returns:
        DriverResponse with:
            - output: Combined result
            - status: 'ok'
    """
    type = "join"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        """
        Execute the join node by combining configured sources.

        If no sources specified, defaults to parallel_results for backward compatibility.
        """
        node_id = node.get("id", "unknown")
        data = node.get('data') or {}
        label = data.get("label", "Join")
        merge_strategy = data.get('merge_strategy', 'list')
        separator = data.get('separator', '')
        sources = data.get('sources')

        logger.info(f"[Join] Node: {label} ({node_id}) - Strategy: {merge_strategy}")

        # Gather values from configured sources
        if sources:
            # Custom sources specified
            values = []
            for source in sources:
                value = self._get_value_from_source(source, context)
                if value is not None:
                    values.append(value)
            logger.debug(f"[Join] Joining {len(values)} custom sources")
        else:
            # Default: use parallel_results for backward compatibility
            values = context.get('parallel_results', [])
            logger.debug(f"[Join] Joining {len(values)} parallel results")

        # Merge results according to strategy
        merged_output = self._merge_results(values, merge_strategy, separator)

        logger.info(f"[Join] Successfully merged {len(values)} values")
        logger.debug(f"[Join] Output: {str(merged_output)[:100]}...")

        return DriverResponse({
            "status": "ok",
            "output": merged_output,
        })

    def _get_value_from_source(self, source: str, context: Dict[str, Any]) -> Any:
        """Get value from a source specification."""
        if source == 'input':
            return context.get('input')

        if source == 'parallel_results':
            return context.get('parallel_results', [])

        if source.startswith('state.'):
            # Extract from context.state
            key = source[6:]  # Remove 'state.' prefix
            return context.get('state', {}).get(key)

        if source.startswith('params.'):
            # Extract from context.params
            key = source[7:]  # Remove 'params.' prefix
            return context.get('params', {}).get(key)

        return None

    def _merge_results(self, results: List[Any], strategy: str, separator: str = '') -> Any:
        """Merge results according to the specified strategy."""
        if not results:
            return None

        if strategy == 'first':
            return results[0]

        if strategy == 'last':
            return results[-1]

        if strategy == 'concat':
            # Concatenate string results
            str_results = [str(r) if r is not None else '' for r in results]
            return ''.join(str_results)

        if strategy == 'join':
            # Join strings with separator
            str_results = [str(r) if r is not None else '' for r in results]
            return separator.join(str_results)

        if strategy == 'merge':
            # Shallow merge dict results
            merged = {}
            for r in results:
                if isinstance(r, dict):
                    merged.update(r)
            return merged

        # Default: 'list' - return all results as a list
        # Flatten if items are lists
        result = []
        for v in results:
            if isinstance(v, list):
                result.extend(v)
            else:
                result.append(v)
        return result
