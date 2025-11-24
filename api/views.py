from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import viewsets
from .models import Workflow
from .serializers import WorkflowSerializer
from rest_framework import status
from .drivers import execute_node_by_type
from .orchestration import WorkflowExecutor, PollingExecutor
from .node_types import get_all_node_types
from typing import Any, Dict, List, Optional
from django.core.cache import cache
import threading
import uuid


@api_view(['GET'])
def node_types_list(request):
    """
    API endpoint for retrieving node types.
    Returns node type definitions from node_types.py.
    """
    node_types = get_all_node_types()

    # Convert to list format expected by frontend (with id field for compatibility)
    result = []
    for idx, (name, definition) in enumerate(node_types.items(), start=1):
        result.append({
            'id': idx,
            'name': name,
            **definition
        })

    return Response(result)


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
      "context": { "input": "...", "params": {...}, "condition": bool, "state": {...} },
      "startNodeId": "optional-node-id"
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

    # Execute workflow using the orchestration layer
    executor = WorkflowExecutor()
    result = executor.execute(nodes, edges, context, start_node_id)

    # Convert result to HTTP response
    http_status = status.HTTP_200_OK if result.status == 'ok' else status.HTTP_400_BAD_REQUEST
    return Response(result.to_dict(), status=http_status)


@api_view(['POST'])
def execute_workflow_async(request):
    """
    Execute a workflow asynchronously in a background thread.

    Returns immediately with an execution ID that can be used to poll for status.

    Expected payload:
    {
      "nodes": [ ... reactflow nodes ... ],
      "edges": [ ... reactflow edges ... ],
      "context": { "input": "...", "params": {...}, "condition": bool, "state": {...} },
      "startNodeId": "optional-node-id"
    }

    Returns:
    {
      "executionId": "uuid-string",
      "status": "started"
    }
    """
    payload = request.data or {}
    nodes: List[Dict[str, Any]] = payload.get('nodes') or []
    edges: List[Dict[str, Any]] = payload.get('edges') or []
    context: Dict[str, Any] = payload.get('context') or {}
    start_node_id = payload.get('startNodeId')

    if not nodes:
        return Response(
            {"status": "error", "error": "nodes are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Generate unique execution ID
    execution_id = str(uuid.uuid4())

    # Define background execution function
    def execute_in_background():
        try:
            executor = PollingExecutor(execution_id=execution_id)
            executor.execute(nodes, edges, context, start_node_id)
        except Exception as e:
            # Update cache with error
            cache.set(f'execution_{execution_id}', {
                'status': 'error',
                'error': str(e),
                'currentNodeId': None,
                'completedNodes': [],
                'errorNodes': [],
                'trace': []
            }, timeout=300)

    # Start background thread
    thread = threading.Thread(target=execute_in_background, daemon=True)
    thread.start()

    return Response({
        'executionId': execution_id,
        'status': 'started'
    }, status=status.HTTP_202_ACCEPTED)


@api_view(['GET'])
def execution_status(request, execution_id):
    """
    Get the current status of a workflow execution.

    Returns:
    {
      "status": "running" | "completed" | "error" | "not_found",
      "currentNodeId": "node-id" | null,
      "completedNodes": ["node-id-1", "node-id-2", ...],
      "errorNodes": ["node-id", ...],
      "trace": [...],
      "steps": 5,
      "final": "result value" | null,
      "error": "error message" | null,
      "timestamp": 1234567890.123
    }
    """
    cache_key = f'execution_{execution_id}'
    execution_state = cache.get(cache_key)

    if execution_state is None:
        return Response({
            'status': 'not_found',
            'error': 'Execution not found or expired'
        }, status=status.HTTP_404_NOT_FOUND)

    return Response(execution_state, status=status.HTTP_200_OK)
