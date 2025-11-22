from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import viewsets
from datetime import datetime
from .models import Workflow, NodeType
from .serializers import WorkflowSerializer, NodeTypeSerializer


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
