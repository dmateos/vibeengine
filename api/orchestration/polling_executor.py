"""
Workflow executor with polling support.

Executes workflows in background thread and updates cache with progress.
"""
from typing import Any, Dict, List, Optional
from django.core.cache import cache
from .workflow_executor import WorkflowExecutor
import time
import logging
from celery import group


logger = logging.getLogger(__name__)


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
            'timestamp': time.time(),
            'parallelStatus': {},
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
            startNodeId=start_node_id,
            parallelStatus={},
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

    def _execute_parallel_branches(self, parallel_node: Dict[str, Any],
                                   res: Dict[str, Any], context: Dict[str, Any],
                                   outgoing: Dict[str, List[Dict[str, Any]]],
                                   node_by_id: Dict[str, Dict[str, Any]],
                                   edges: List[Dict[str, Any]],
                                   remaining_steps: int) -> tuple:
        """
        Execute parallel branches while pushing branch status updates into cache.

        Returns:
            Tuple of (results_list, trace_list)
        """
        from ..tasks import execute_branch_task

        parallel_id = str(parallel_node.get('id'))
        branch_edges = outgoing.get(parallel_id, [])

        # Filter out non-control-flow edges (memory/tool nodes)
        branch_edges = [
            e for e in branch_edges
            if node_by_id.get(str(e.get('target')), {}).get('type') not in ('memory', 'tool')
        ]

        logger.info(f"[Parallel Execution] Starting {len(branch_edges)} branches in parallel")

        branch_status: Dict[str, str] = {}

        def push_status():
            try:
                self._update_cache(parallelStatus=branch_status)
            except Exception:
                # Cache update shouldn't break execution
                pass

        # Create tasks for each branch
        branch_tasks = []
        for idx, edge in enumerate(branch_edges):
            branch_target_id = str(edge.get('target'))
            branch_node = node_by_id.get(branch_target_id)

            if not branch_node:
                continue

            # Clone context for this branch (each branch gets independent context)
            branch_context = {
                'input': context.get('input'),
                'params': context.get('params', {}),
                'condition': context.get('condition', False),
                'state': dict(context.get('state', {})),  # Shallow copy of state
            }

            branch_id = f"{parallel_id}_branch_{idx}"
            branch_status[branch_id] = 'queued'

            # Create Celery task signature for this branch
            task_sig = execute_branch_task.s(
                branch_id=branch_id,
                start_node=branch_node,
                context=branch_context,
                outgoing=outgoing,
                node_by_id=node_by_id,
                edges=edges,
                max_steps=remaining_steps,
                execution_id=getattr(self, 'execution_id', None),
            )
            branch_tasks.append(task_sig)

        push_status()

        # Execute all branches in parallel using Celery group
        if branch_tasks:
            logger.info(f"[Parallel Execution] Dispatching {len(branch_tasks)} tasks to Celery")
            job = group(branch_tasks)
            try:
                result = job.apply_async()

                # If at least one worker responds, mark branches as running
                try:
                    inspector = execute_branch_task.app.control.inspect()
                    active = inspector.active() or {}
                    reserved = inspector.reserved() or {}
                    if active or reserved:
                        for bid in branch_status:
                            branch_status[bid] = 'running'
                        push_status()
                except Exception:
                    # If inspect fails, fall back to leaving them queued
                    pass

                # Wait for all branches to complete
                logger.info(f"[Parallel Execution] Waiting for parallel branches to complete...")
                # Explicitly allow synchronous subtask joining inside a Celery task
                branch_results = result.get(timeout=300, disable_sync_subtasks=False)  # 5 minute timeout
                logger.info(f"[Parallel Execution] All {len(branch_results)} branches completed")
            except Exception as exc:
                logger.error(f"[Parallel Execution] Failed to dispatch/collect parallel branches: {exc}")
                for bid in branch_status:
                    branch_status[bid] = 'error'
                push_status()
                return [], [{'status': 'error', 'error': str(exc)}]
        else:
            branch_results = []

        # Collect results and traces
        results = []
        trace = []

        for branch_result in branch_results:
            branch_id = branch_result.get('branch_id')
            branch_status[branch_id] = branch_result.get('status', 'error')

            if branch_result.get('status') == 'ok':
                results.append(branch_result.get('final_output'))
                trace.extend(branch_result.get('trace', []))
            else:
                # Branch failed, add None result
                results.append(None)
                logger.error(f"[Parallel Execution] Branch {branch_id} failed: {branch_result.get('error')}")

        # Any branch that never reported (e.g., task never started) stays queued

        push_status()

        return results, trace
