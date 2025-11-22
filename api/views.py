from rest_framework.decorators import api_view
from rest_framework.response import Response
from datetime import datetime


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
