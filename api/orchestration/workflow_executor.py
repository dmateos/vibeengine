from typing import Any, Dict, List, Optional
from ..drivers import execute_node_by_type
from ..memory_store import store


class ExecutionResult:
    """Result of workflow execution."""

    def __init__(self, status: str, final: Any = None, trace: List[Dict[str, Any]] = None,
                 steps: int = 0, start_node_id: Optional[str] = None, error: Optional[str] = None):
        self.status = status
        self.final = final
        self.trace = trace or []
        self.steps = steps
        self.start_node_id = start_node_id
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        result = {
            'status': self.status,
            'final': self.final,
            'trace': self.trace,
            'steps': self.steps,
            'startNodeId': self.start_node_id,
        }
        if self.error:
            result['error'] = self.error
        return result


class WorkflowExecutor:
    """
    Executes workflows by traversing nodes and edges.

    Routing rules:
    - Starts at first node of type 'input' or a node with no incoming edges.
    - For 'router' nodes, selects the outgoing edge whose sourceHandle matches result.route ('yes'|'no'),
      otherwise falls back to the first outgoing edge.
    - For other nodes, follows the first outgoing edge.
    - Propagates context: if a node returns 'output', it becomes next 'input'; returns 'state' merge into context.state.
    - Stops when an 'output' node is reached or there are no further edges.
    """

    def __init__(self, max_steps: Optional[int] = None):
        """
        Initialize the workflow executor.

        Args:
            max_steps: Maximum number of steps to execute before stopping (default: len(nodes) + len(edges) + 10)
        """
        self.max_steps = max_steps

    # Hook methods that can be overridden by subclasses
    def _on_execution_start(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]],
                           start_node_id: Optional[str]) -> None:
        """Called when execution starts. Override for custom behavior."""
        pass

    def _on_node_start(self, node: Dict[str, Any], steps: int) -> None:
        """Called before a node executes. Override for custom behavior."""
        pass

    def _on_node_complete(self, node: Dict[str, Any], result: Dict[str, Any],
                         completed_nodes: List[str], trace: List[Dict[str, Any]], steps: int) -> None:
        """Called after a node completes successfully. Override for custom behavior."""
        pass

    def _on_execution_complete(self, final_value: Any, trace: List[Dict[str, Any]],
                              completed_nodes: List[str], steps: int) -> None:
        """Called when execution completes. Override for custom behavior."""
        pass

    def _on_execution_error(self, error: str, trace: List[Dict[str, Any]],
                           completed_nodes: List[str]) -> None:
        """Called when execution fails. Override for custom behavior."""
        pass

    def execute(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]],
                context: Optional[Dict[str, Any]] = None,
                start_node_id: Optional[str] = None) -> ExecutionResult:
        """
        Execute a workflow.

        Args:
            nodes: List of reactflow nodes
            edges: List of reactflow edges
            context: Execution context with 'input', 'params', 'condition', 'state'
            start_node_id: Optional specific node to start from

        Returns:
            ExecutionResult with status, final value, trace, and steps
        """
        if not nodes:
            return ExecutionResult(status='error', error='nodes are required')

        context = context or {}
        context.setdefault('state', {})

        # Build node and edge maps
        node_by_id, outgoing, incoming_count = self._build_node_maps(nodes, edges)

        # Select start node
        start = self._select_start_node(nodes, node_by_id, incoming_count, start_node_id)

        # Initialize context with input node defaults if needed
        if start:
            self._initialize_context_from_input_node(start, context)

        # Notify execution start
        self._on_execution_start(nodes, edges, start_node_id)

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

            # Notify node start
            self._on_node_start(current, steps)

            # Build agent-specific context (memory/tools)
            exec_context, used_memory, used_tools = self._build_agent_context(
                current, ntype, context, edges, node_by_id
            )

            # Execute node
            res = execute_node_by_type(ntype, current, exec_context)

            if res.get('status') != 'ok':
                error_msg = res.get('error', 'node execution failed')
                self._on_execution_error(error_msg, trace, completed_nodes)
                return ExecutionResult(
                    status='error',
                    error=error_msg,
                    trace=trace
                )

            # Check for parallel execution
            if res.get('parallel'):
                # Execute all parallel branches
                parallel_results, parallel_trace = self._execute_parallel_branches(
                    current, res, context, outgoing, node_by_id, edges, max_steps - steps
                )

                # Add parallel execution to trace
                trace.extend(parallel_trace)
                steps += len(parallel_trace)

                # Store results for join node
                context['parallel_results'] = parallel_results

                # Find join node (first common target of all branches)
                nxt, used_edge = self._find_join_node(current, outgoing, node_by_id)

                # Add trace for parallel node itself
                trace.append(self._build_trace_entry(
                    current, ntype, res, None, nxt, used_memory, used_tools, exec_context
                ))
            else:
                # Normal execution path
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
                trace.append(self._build_trace_entry(
                    current, ntype, res, used_edge, nxt, used_memory, used_tools, exec_context
                ))

            # Mark node as completed
            completed_nodes.append(node_id)

            # Notify node completion
            self._on_node_complete(current, res, completed_nodes, trace, steps)

            # Stop at output node
            if ntype == 'output':
                break

            current = nxt

        # Notify execution completion
        self._on_execution_complete(final_value, trace, completed_nodes, steps)

        return ExecutionResult(
            status='ok',
            final=final_value,
            trace=trace,
            steps=steps,
            start_node_id=start.get('id') if start else None
        )

    def _build_node_maps(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> tuple:
        """Build lookup maps for nodes and edges."""
        node_by_id: Dict[str, Dict[str, Any]] = {str(n.get('id')): n for n in nodes}
        outgoing: Dict[str, List[Dict[str, Any]]] = {}
        incoming_count: Dict[str, int] = {str(n.get('id')): 0 for n in nodes}

        for e in edges:
            s = str(e.get('source'))
            t = str(e.get('target'))
            outgoing.setdefault(s, []).append(e)
            if t in incoming_count:
                incoming_count[t] += 1

        return node_by_id, outgoing, incoming_count

    def _select_start_node(self, nodes: List[Dict[str, Any]],
                          node_by_id: Dict[str, Dict[str, Any]],
                          incoming_count: Dict[str, int],
                          start_node_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Select the starting node for workflow execution.

        Priority:
        1. Explicitly provided start_node_id
        2. First 'input' type node
        3. First node with no incoming edges
        4. First node in the list
        """
        start = None

        if start_node_id is not None:
            start = node_by_id.get(str(start_node_id))

        if not start:
            start = next((n for n in nodes if n.get('type') == 'input'), None)

        if not start:
            start = next((n for n in nodes if incoming_count.get(str(n.get('id')), 0) == 0), None)

        if not start and nodes:
            start = nodes[0]

        return start

    def _initialize_context_from_input_node(self, start: Dict[str, Any],
                                           context: Dict[str, Any]) -> None:
        """Initialize context with input node's configured value if no explicit input provided."""
        if start.get('type') == 'input':
            try:
                node_val = (start.get('data') or {}).get('value')
                if (context.get('input') is None) or (isinstance(context.get('input'), str) and context.get('input') == ''):
                    if node_val is not None:
                        context['input'] = node_val
            except Exception:
                pass

    def _build_agent_context(self, current: Dict[str, Any], ntype: str,
                           context: Dict[str, Any], edges: List[Dict[str, Any]],
                           node_by_id: Dict[str, Dict[str, Any]]) -> tuple:
        """
        Build execution context with supplemental knowledge and tools for agent nodes.

        Returns:
            Tuple of (exec_context, used_memory, used_tools)
        """
        exec_context = dict(context)
        used_memory: List[str] = []
        used_tools: List[str] = []

        if ntype not in ('openai_agent', 'claude_agent', 'ollama_agent'):
            return exec_context, used_memory, used_tools

        current_id = str(current.get('id'))
        tool_specs: List[Dict[str, Any]] = []
        tool_nodes_map: Dict[str, Any] = {}
        memory_nodes_map: Dict[str, Any] = {}
        mem_knowledge: Dict[str, Any] = {}
        mem_specs: List[Dict[str, Any]] = []

        # Scan all edges connected to this agent
        for e in edges:
            src = str(e.get('source'))
            tgt = str(e.get('target'))
            other_id = None

            if src == current_id:
                other_id = tgt
            elif tgt == current_id:
                other_id = src

            if not other_id:
                continue

            other = node_by_id.get(str(other_id))
            if not other:
                continue

            otype = other.get('type')

            if otype == 'memory':
                data = (other.get('data') or {})
                key = data.get('key', 'memory')
                namespace = data.get('namespace') or 'default'
                store_key = f"{namespace}:{key}"
                val = store.get(store_key)
                mem_knowledge[key] = val
                used_memory.append(str(other.get('id')))
                mem_specs.append({
                    'nodeId': str(other.get('id')),
                    'key': key,
                    'namespace': namespace,
                })
                memory_nodes_map[str(other.get('id'))] = other

            elif otype == 'tool':
                tid = str(other.get('id'))
                odata = other.get('data') or {}
                tool_specs.append({
                    'nodeId': tid,
                    'name': odata.get('label') or f'Tool {tid}',
                    'operation': odata.get('operation'),
                    'arg': odata.get('arg'),
                })
                tool_nodes_map[tid] = other
                used_tools.append(tid)

        if mem_knowledge:
            exec_context['knowledge'] = mem_knowledge
        if tool_specs:
            exec_context['agent_tools'] = tool_specs
            exec_context['agent_tool_nodes'] = tool_nodes_map
        if mem_specs:
            exec_context['agent_memory_nodes'] = mem_specs
            exec_context['agent_memory_node_map'] = memory_nodes_map

        return exec_context, used_memory, used_tools

    def _select_next_node(self, current: Dict[str, Any], ntype: str,
                         res: Dict[str, Any], outgoing: Dict[str, List[Dict[str, Any]]],
                         node_by_id: Dict[str, Dict[str, Any]]) -> tuple:
        """
        Select the next node to execute based on routing rules.

        Returns:
            Tuple of (next_node, used_edge)
        """
        cid = str(current.get('id'))

        # Filter out edges to memory/tool nodes (they don't participate in control flow)
        outs = []
        for e in (outgoing.get(cid, []) or []):
            tgt = str(e.get('target'))
            tnode = node_by_id.get(tgt)
            if not tnode:
                continue
            ttype = (tnode or {}).get('type')
            if ttype in ('memory', 'tool'):
                continue
            outs.append(e)

        if not outs:
            return None, None

        # Router node: follow sourceHandle matching route
        if ntype == 'router':
            return self._select_router_edge(res, outs, node_by_id)

        # Other nodes: use preference-based selection
        return self._select_preferred_edge(outs, node_by_id)

    def _select_router_edge(self, res: Dict[str, Any],
                           outs: List[Dict[str, Any]],
                           node_by_id: Dict[str, Dict[str, Any]]) -> tuple:
        """Select edge for router nodes based on route result."""
        route = res.get('route')
        nxt = None
        used_edge = None

        if route is not None:
            for e in outs:
                if str(e.get('sourceHandle')) == str(route):
                    nxt = node_by_id.get(str(e.get('target')))
                    used_edge = e
                    if nxt:
                        break

        # Fallback to first edge
        if not nxt and outs:
            used_edge = outs[0]
            nxt = node_by_id.get(str(outs[0].get('target')))

        return nxt, used_edge

    def _select_preferred_edge(self, outs: List[Dict[str, Any]],
                              node_by_id: Dict[str, Dict[str, Any]]) -> tuple:
        """Select edge based on handle preferences and target type priorities."""
        # Prefer explicit data-flow handle ids
        preferred = {'s', 'out', 'write', 'default'}
        chosen = None

        for e in outs:
            sh = str(e.get('sourceHandle')) if e.get('sourceHandle') is not None else ''
            if sh in preferred:
                chosen = e
                break

        # If still not chosen and multiple outs, prefer certain target types
        if not chosen and len(outs) > 1:
            priority = {
                'openai_agent': 9,
                'claude_agent': 9,
                'ollama_agent': 9,
                'router': 8,
                'memory': 7,
                'output': 1,
            }

            def score(edge):
                tnode = node_by_id.get(str(edge.get('target')))
                ttype = (tnode or {}).get('type')
                return priority.get(ttype, 5)

            outs_sorted = sorted(outs, key=lambda e: score(e), reverse=True)
            chosen = outs_sorted[0]

        if not chosen:
            chosen = outs[0]

        nxt = node_by_id.get(str(chosen.get('target')))
        return nxt, chosen

    def _build_trace_entry(self, current: Dict[str, Any], ntype: str,
                          res: Dict[str, Any], used_edge: Optional[Dict[str, Any]],
                          nxt: Optional[Dict[str, Any]],
                          used_memory: List[str], used_tools: List[str],
                          exec_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build a trace entry for the current execution step."""
        return {
            'nodeId': current.get('id'),
            'type': ntype,
            'result': res,
            'context': {'input': exec_context.get('input')} if exec_context else None,
            'edgeId': used_edge.get('id') if isinstance(used_edge, dict) else None,
            'nextNodeId': nxt.get('id') if isinstance(nxt, dict) else None,
            'usedMemory': used_memory if ntype in ('openai_agent', 'claude_agent', 'ollama_agent') else None,
            'usedTools': used_tools if ntype in ('openai_agent', 'claude_agent', 'ollama_agent') else None,
        }

    def _execute_parallel_branches(self, parallel_node: Dict[str, Any],
                                   res: Dict[str, Any], context: Dict[str, Any],
                                   outgoing: Dict[str, List[Dict[str, Any]]],
                                   node_by_id: Dict[str, Dict[str, Any]],
                                   edges: List[Dict[str, Any]],
                                   remaining_steps: int) -> tuple:
        """
        Execute all parallel branches from a parallel node.

        Returns:
            Tuple of (results_list, trace_list)
        """
        parallel_id = str(parallel_node.get('id'))
        branch_edges = outgoing.get(parallel_id, [])

        # Filter out non-control-flow edges (memory/tool nodes)
        branch_edges = [
            e for e in branch_edges
            if node_by_id.get(str(e.get('target')), {}).get('type') not in ('memory', 'tool')
        ]

        results = []
        trace = []

        # Execute each branch independently
        for edge in branch_edges:
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

            # Execute branch until we hit the join node or end
            branch_result, branch_trace_entries = self._execute_branch(
                branch_node, branch_context, outgoing, node_by_id, edges, remaining_steps
            )

            results.append(branch_result)
            trace.extend(branch_trace_entries)

        return results, trace

    def _execute_branch(self, start_node: Dict[str, Any], context: Dict[str, Any],
                       outgoing: Dict[str, List[Dict[str, Any]]],
                       node_by_id: Dict[str, Dict[str, Any]],
                       edges: List[Dict[str, Any]],
                       max_steps: int) -> tuple:
        """
        Execute a single branch from parallel execution.

        Returns:
            Tuple of (final_output, trace_entries)
        """
        current = start_node
        steps = 0
        trace = []
        final_output = None

        while current and steps < max_steps:
            steps += 1
            ntype = current.get('type')

            # Stop at join node - it will be executed after all branches complete
            if ntype == 'join':
                break

            # Build context for this node
            exec_context, used_memory, used_tools = self._build_agent_context(
                current, ntype, context, edges, node_by_id
            )

            # Execute node
            res = execute_node_by_type(ntype, current, exec_context)

            if res.get('status') != 'ok':
                # On error, store error as output and stop branch
                final_output = {'error': res.get('error', 'node execution failed')}
                trace.append(self._build_trace_entry(
                    current, ntype, res, None, None, used_memory, used_tools, exec_context
                ))
                break

            # Propagate outputs within branch context
            if 'state' in res:
                context['state'] = res['state']
            if 'output' in res:
                context['input'] = res['output']
                final_output = res['output']
            if 'final' in res:
                final_output = res['final']

            # Select next node in branch
            nxt, used_edge = self._select_next_node(
                current, ntype, res, outgoing, node_by_id
            )

            # Add trace entry
            trace.append(self._build_trace_entry(
                current, ntype, res, used_edge, nxt, used_memory, used_tools, exec_context
            ))

            # Stop if no next node or hit output node
            if not nxt or ntype == 'output':
                break

            current = nxt

        return final_output, trace

    def _find_join_node(self, parallel_node: Dict[str, Any],
                       outgoing: Dict[str, List[Dict[str, Any]]],
                       node_by_id: Dict[str, Dict[str, Any]]) -> tuple:
        """
        Find the join node that all parallel branches converge to.

        For simplicity, we look for the first node of type 'join' that any branch leads to.

        Returns:
            Tuple of (join_node, edge) or (None, None) if not found
        """
        parallel_id = str(parallel_node.get('id'))
        branch_edges = outgoing.get(parallel_id, [])

        # Get all branch targets
        for edge in branch_edges:
            target_id = str(edge.get('target'))
            target = node_by_id.get(target_id)

            if not target:
                continue

            # Check if target is a join node
            if target.get('type') == 'join':
                return target, edge

            # Look one level deeper - check target's outgoing edges
            target_edges = outgoing.get(target_id, [])
            for next_edge in target_edges:
                next_target_id = str(next_edge.get('target'))
                next_target = node_by_id.get(next_target_id)

                if next_target and next_target.get('type') == 'join':
                    return next_target, None

        # No join node found - execution will end after parallel branches
        return None, None
