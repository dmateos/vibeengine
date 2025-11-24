from typing import Any, Dict
from .base import BaseDriver, DriverResponse


class ParallelDriver(BaseDriver):
    """
    Parallel node driver that forks execution into multiple branches.

    All branches receive the same input and execute concurrently.
    Use a JoinDriver to collect and merge results from parallel branches.

    Configuration:
        No specific configuration needed. The node's outgoing edges define the branches.

    Returns:
        DriverResponse with:
            - parallel: True (marker for executor to handle parallel execution)
            - output: Input passed through to all branches
            - status: 'ok'
    """
    type = "parallel"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        """
        Execute the parallel node by marking that parallel execution is needed.

        The executor will handle the actual parallel execution by:
        1. Finding all outgoing edges (branches)
        2. Cloning the current context for each branch
        3. Executing each branch independently
        4. Collecting results for the join node
        """
        return DriverResponse({
            "status": "ok",
            "parallel": True,
            "output": context.get("input"),  # Pass input through to all branches
        })
