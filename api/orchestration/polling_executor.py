"""
Workflow executor with polling support.

Executes workflows in background thread and updates cache with progress.
"""
from typing import Any, Dict, List, Optional
from django.core.cache import cache
from .workflow_executor import WorkflowExecutor
import time


class PollingExecutor(WorkflowExecutor):
    """
    Workflow executor that updates execution state in cache for polling.

    During execution, updates cache with:
    - Current running node
    - Completed nodes
    - Error nodes
    - Trace entries
    - Final result
    """

    def __init__(self, execution_id: str, max_steps: Optional[int] = None):
        """
        Initialize polling executor.

        Args:
            execution_id: Unique ID for this execution (used as cache key)
            max_steps: Maximum steps to execute
        """
        super().__init__(max_steps)
        self.execution_id = execution_id
        self.cache_timeout = 300  # 5 minutes

    def _update_cache(self, **kwargs):
        """Update execution state in cache."""
        cache_key = f'execution_{self.execution_id}'

        # Get current state or initialize
        state = cache.get(cache_key, {
            'status': 'running',
            'currentNodeId': None,
            'completedNodes': [],
            'errorNodes': [],
            'trace': [],
            'steps': 0,
            'final': None,
            'error': None,
            'timestamp': time.time()
        })

        # Update with new values
        state.update(kwargs)
        state['timestamp'] = time.time()

        # Save to cache
        cache.set(cache_key, state, timeout=self.cache_timeout)

    # Override hook methods to add cache updates
    def _on_execution_start(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]],
                           start_node_id: Optional[str]) -> None:
        """Update cache when execution starts."""
        self._update_cache(
            status='running',
            totalNodes=len(nodes),
            currentNodeId=None,
            completedNodes=[],
            errorNodes=[],
            trace=[],
            startNodeId=start_node_id
        )

    def _on_node_start(self, node: Dict[str, Any], steps: int) -> None:
        """Update cache when a node starts."""
        self._update_cache(
            currentNodeId=str(node.get('id')),
            steps=steps
        )

    def _on_node_complete(self, node: Dict[str, Any], result: Dict[str, Any],
                         completed_nodes: List[str], trace: List[Dict[str, Any]], steps: int) -> None:
        """Update cache when a node completes."""
        # Track nodes that encountered errors (but continued execution)
        cache_key = f'execution_{self.execution_id}'
        state = cache.get(cache_key, {})
        error_nodes = state.get('errorNodes', [])

        # If node has had_error flag, track it
        if result.get('had_error'):
            node_id = str(node.get('id'))
            if node_id not in error_nodes:
                error_nodes.append(node_id)

        self._update_cache(
            currentNodeId=None,
            completedNodes=completed_nodes,
            errorNodes=error_nodes,
            trace=trace,
            steps=steps
        )

    def _on_execution_complete(self, final_value: Any, trace: List[Dict[str, Any]],
                              completed_nodes: List[str], steps: int) -> None:
        """Update cache when execution completes."""
        self._update_cache(
            status='completed',
            final=final_value,
            completedNodes=completed_nodes,
            trace=trace,
            steps=steps,
            currentNodeId=None
        )

    def _on_execution_error(self, error: str, trace: List[Dict[str, Any]],
                           completed_nodes: List[str]) -> None:
        """Update cache when execution fails."""
        self._update_cache(
            status='error',
            error=error,
            currentNodeId=None,
            errorNodes=completed_nodes,
            trace=trace
        )
