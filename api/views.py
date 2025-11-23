from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import viewsets
from .models import Workflow, NodeType
from .serializers import WorkflowSerializer, NodeTypeSerializer
from rest_framework import status
from .drivers import execute_node_by_type
from .orchestration import WorkflowExecutor
from typing import Any, Dict, List, Optional


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
