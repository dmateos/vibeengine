"""
Workflow executor with polling support.

Executes workflows in background thread and updates cache with progress.
"""
from typing import Any, Dict, List, Optional, Callable
from django.core.cache import cache
from .workflow_executor import WorkflowExecutor, ExecutionResult
from ..drivers import execute_node_by_type
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

    def execute(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]],
                context: Optional[Dict[str, Any]] = None,
                start_node_id: Optional[str] = None) -> ExecutionResult:
        """
        Execute workflow with cache updates for polling.

        Updates cache after each node execution with current progress.
        """
        # Initialize execution state
        self._update_cache(
            status='running',
            totalNodes=len(nodes),
            currentNodeId=None,
            completedNodes=[],
            errorNodes=[],
            trace=[],
            startNodeId=start_node_id
        )

        if not nodes:
            result = ExecutionResult(status='error', error='nodes are required')
            self._update_cache(
                status='error',
                error='nodes are required'
            )
            return result

        context = context or {}
        context.setdefault('state', {})

        # Build node and edge maps
        node_by_id, outgoing, incoming_count = self._build_node_maps(nodes, edges)

        # Select start node
        start = self._select_start_node(nodes, node_by_id, incoming_count, start_node_id)

        # Initialize context with input node defaults if needed
        if start:
            self._initialize_context_from_input_node(start, context)

        # Execute workflow
        max_steps = self.max_steps or (len(nodes) + len(edges) + 10)
        current = start
        steps = 0
        trace: List[Dict[str, Any]] = []
        final_value: Any = None
        completed_nodes: List[str] = []

        while current and steps < max_steps:
            steps += 1
            ntype = current.get('type')
            node_id = str(current.get('id'))

            # Update cache: node started
            self._update_cache(
                currentNodeId=node_id,
                steps=steps
            )

            # Build agent-specific context (memory/tools)
            exec_context, used_memory, used_tools = self._build_agent_context(
                current, ntype, context, edges, node_by_id
            )

            # Execute node
            res = execute_node_by_type(ntype, current, exec_context)

            if res.get('status') != 'ok':
                # Update cache: error occurred
                error_msg = res.get('error', 'node execution failed')
                self._update_cache(
                    status='error',
                    error=error_msg,
                    currentNodeId=None,
                    errorNodes=completed_nodes + [node_id],
                    trace=trace
                )

                return ExecutionResult(
                    status='error',
                    error=error_msg,
                    trace=trace
                )

            # Propagate outputs into context
            if 'state' in res:
                context['state'] = res['state']
            if 'output' in res:
                context['input'] = res['output']
                final_value = res['output']
            if 'final' in res:
                final_value = res['final']

            # Select next node
            nxt, used_edge = self._select_next_node(
                current, ntype, res, outgoing, node_by_id
            )

            # Add trace entry
            trace_entry = self._build_trace_entry(
                current, ntype, res, used_edge, nxt, used_memory, used_tools, exec_context
            )
            trace.append(trace_entry)

            # Update completed nodes list
            completed_nodes.append(node_id)

            # Update cache: node completed
            self._update_cache(
                currentNodeId=None,
                completedNodes=completed_nodes,
                trace=trace,
                steps=steps
            )

            # Stop at output node
            if ntype == 'output':
                break

            current = nxt

        # Final cache update: execution completed
        self._update_cache(
            status='completed',
            final=final_value,
            completedNodes=completed_nodes,
            trace=trace,
            steps=steps,
            currentNodeId=None
        )

        return ExecutionResult(
            status='ok',
            final=final_value,
            trace=trace,
            steps=steps,
            start_node_id=start.get('id') if start else None
        )
