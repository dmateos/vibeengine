from typing import Any, Dict, List
from .base import BaseDriver, DriverResponse


class JoinDriver(BaseDriver):
    """
    Join node driver that collects and merges results from parallel branches.

    The join node waits for all parallel branches to complete, then merges
    their outputs according to the configured strategy.

    Configuration (node.data):
        merge_strategy: How to combine parallel results
            - 'list': Collect all outputs as a list (default)
            - 'concat': Concatenate string outputs
            - 'first': Use first branch result
            - 'last': Use last branch result
            - 'merge': Merge dict outputs (shallow merge)

    Returns:
        DriverResponse with:
            - output: Merged result from all parallel branches
            - status: 'ok'
    """
    type = "join"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        """
        Execute the join node by merging parallel branch results.

        The executor populates context['parallel_results'] with a list of outputs
        from all completed parallel branches before calling this method.
        """
        data = node.get('data') or {}
        merge_strategy = data.get('merge_strategy', 'list')
        parallel_results = context.get('parallel_results', [])

        # Merge results according to strategy
        merged_output = self._merge_results(parallel_results, merge_strategy)

        return DriverResponse({
            "status": "ok",
            "output": merged_output,
        })

    def _merge_results(self, results: List[Any], strategy: str) -> Any:
        """Merge parallel results according to the specified strategy."""
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

        if strategy == 'merge':
            # Shallow merge dict results
            merged = {}
            for r in results:
                if isinstance(r, dict):
                    merged.update(r)
            return merged

        # Default: 'list' - return all results as a list
        return results
