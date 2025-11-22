from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import viewsets
from datetime import datetime
from .models import Workflow, NodeType
from .serializers import WorkflowSerializer, NodeTypeSerializer
from rest_framework import status
from .drivers import execute_node_by_type
from typing import Any, Dict, List, Optional
from .memory_store import store


@api_view(['GET'])
def hello_world(request):
    """Simple hello world endpoint"""
    return Response({
        'message': 'Hello from Django!',
        'timestamp': datetime.now().isoformat(),
        'status': 'success'
    })


@api_view(['GET'])
def get_items(request):
    """Sample endpoint that returns a list of items"""
    items = [
        {'id': 1, 'name': 'Item One', 'description': 'First sample item'},
        {'id': 2, 'name': 'Item Two', 'description': 'Second sample item'},
        {'id': 3, 'name': 'Item Three', 'description': 'Third sample item'},
    ]
    return Response({
        'items': items,
        'count': len(items)
    })


class NodeTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for retrieving node types.
    Read-only access to available node types.
    """
    queryset = NodeType.objects.all()
    serializer_class = NodeTypeSerializer


class WorkflowViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing workflows.
    Supports CRUD operations for workflows including nodes and edges.
    """
    queryset = Workflow.objects.all()
    serializer_class = WorkflowSerializer


@api_view(['POST'])
def execute_node(request):
    """
    Execute a single node via the agent driver mechanism.

    Expected payload:
    {
      "node": { ... reactflow node ... },
      "context": { ... arbitrary inputs ... }
    }
    """
    payload = request.data or {}
    node = payload.get('node') or {}
    context = payload.get('context') or {}

    node_type = node.get('type')
    if not node_type:
        return Response({
            'status': 'error',
            'error': 'node.type is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    result = execute_node_by_type(node_type, node, context)
    http_status = status.HTTP_200_OK if result.get('status') == 'ok' else status.HTTP_400_BAD_REQUEST
    return Response(result, status=http_status)


@api_view(['POST'])
def execute_workflow(request):
    """
    Execute a workflow by traversing nodes and edges.

    Expected payload:
    {
      "nodes": [ ... reactflow nodes ... ],
      "edges": [ ... reactflow edges ... ],
      "context": { "input": "...", "params": {...}, "condition": bool, "state": {...} }
    }

    Routing rules:
    - Starts at first node of type 'input' or a node with no incoming edges.
    - For 'router' nodes, selects the outgoing edge whose sourceHandle matches result.route ('yes'|'no'),
      otherwise falls back to the first outgoing edge.
    - For other nodes, follows the first outgoing edge.
    - Propagates context: if a node returns 'output', it becomes next 'input'; returns 'state' merge into context.state.
    - Stops when an 'output' node is reached or there are no further edges.
    """
    payload = request.data or {}
    nodes: List[Dict[str, Any]] = payload.get('nodes') or []
    edges: List[Dict[str, Any]] = payload.get('edges') or []
    context: Dict[str, Any] = payload.get('context') or {}
    start_node_id = payload.get('startNodeId')

    if not nodes:
        return Response({"status": "error", "error": "nodes are required"}, status=status.HTTP_400_BAD_REQUEST)

    node_by_id: Dict[str, Dict[str, Any]] = {str(n.get('id')): n for n in nodes}
    # helper to get type by id
    def node_type_by_id(node_id: Optional[str]) -> Optional[str]:
        if node_id is None:
            return None
        n = node_by_id.get(str(node_id))
        return n.get('type') if n else None
    outgoing: Dict[str, List[Dict[str, Any]]] = {}
    incoming_count: Dict[str, int] = {str(n.get('id')): 0 for n in nodes}

    for e in edges:
        s = str(e.get('source'))
        t = str(e.get('target'))
        outgoing.setdefault(s, []).append(e)
        if t in incoming_count:
            incoming_count[t] += 1

    # pick start node
    start = None
    if start_node_id is not None:
        start = node_by_id.get(str(start_node_id))
    if not start:
        # first input node, else node with no incoming edges, else first
        start = next((n for n in nodes if (n.get('type') == 'input')), None)
    if not start:
        start = next((n for n in nodes if incoming_count.get(str(n.get('id')), 0) == 0), None)
    if not start and nodes:
        start = nodes[0]

    current = start
    steps = 0
    max_steps = len(nodes) + len(edges) + 10
    trace: List[Dict[str, Any]] = []
    final_value: Any = None

    # ensure mutable state in context
    context.setdefault('state', {})

    while current and steps < max_steps:
        steps += 1
        ntype = current.get('type')

        # Build supplemental knowledge/tools for agents only
        exec_context = dict(context)
        used_memory: List[str] = []
        used_tools: List[str] = []
        tool_results: List[Dict[str, Any]] = []
        mem_knowledge: Dict[str, Any] = {}
        if ntype == 'agent':
            current_id = str(current.get('id'))
            # consider all edges connected to this agent
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
                elif otype == 'tool':
                    # Execute the tool with current input context
                    tool_res = execute_node_by_type('tool', other, context)
                    tool_results.append({'nodeId': other.get('id'), **tool_res})
                    used_tools.append(str(other.get('id')))

            if mem_knowledge:
                exec_context['knowledge'] = mem_knowledge
            if tool_results:
                exec_context['tools'] = tool_results

        res = execute_node_by_type(ntype, current, exec_context)

        if res.get('status') != 'ok':
            return Response({
                'status': 'error',
                'error': res.get('error', 'node execution failed'),
                'trace': trace,
            }, status=status.HTTP_400_BAD_REQUEST)

        # propagate outputs into context
        if 'state' in res:
            # overwrite or merge state
            context['state'] = res['state']
        if 'output' in res:
            context['input'] = res['output']
            final_value = res['output']
        if 'final' in res:
            final_value = res['final']

        # choose next node
        cid = str(current.get('id'))
        # exclude edges that point to memory/tool from control flow
        outs = []
        for e in (outgoing.get(cid, []) or []):
            tgt = str(e.get('target'))
            ttype = node_type_by_id(tgt)
            if ttype in ('memory', 'tool'):
                continue
            outs.append(e)
        nxt = None
        used_edge = None
        if not outs:
            nxt = None
        elif ntype == 'router':
            route = res.get('route')
            if route is not None:
                # find edge with matching sourceHandle
                for e in outs:
                    if str(e.get('sourceHandle')) == str(route):
                        nxt = node_by_id.get(str(e.get('target')))
                        used_edge = e
                        if nxt:
                            break
            # fallback to first edge
            if not nxt and outs:
                used_edge = outs[0]
                nxt = node_by_id.get(str(outs[0].get('target')))
        else:
            if outs:
                # prefer explicit data-flow handle ids if present
                preferred = {'s', 'out', 'write', 'default'}
                chosen = None
                for e in outs:
                    sh = str(e.get('sourceHandle')) if e.get('sourceHandle') is not None else ''
                    if sh in preferred:
                        chosen = e
                        break
                # if still not chosen and multiple outs, prefer certain target types
                if not chosen and len(outs) > 1:
                    priority = {
                        'tool': 10,
                        'agent': 9,
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
                used_edge = chosen
                nxt = node_by_id.get(str(chosen.get('target')))

        trace.append({
            'nodeId': current.get('id'),
            'type': ntype,
            'result': res,
            'edgeId': used_edge.get('id') if isinstance(used_edge, dict) else None,
            'nextNodeId': nxt.get('id') if isinstance(nxt, dict) else None,
            'usedMemory': used_memory if ntype == 'agent' else None,
            'usedTools': used_tools if ntype == 'agent' else None,
        })

        if ntype == 'output':
            break

        current = nxt

    return Response({
        'status': 'ok',
        'final': final_value,
        'trace': trace,
        'steps': steps,
        'startNodeId': start.get('id') if start else None,
    })
