from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .models import Workflow, WorkflowExecution, WorkflowSchedule
from .serializers import WorkflowSerializer, WorkflowScheduleSerializer
from rest_framework import status
from .drivers import execute_node_by_type
from .orchestration import WorkflowExecutor, PollingExecutor
from .node_types import get_all_node_types
from typing import Any, Dict, List, Optional
from django.core.cache import cache
import uuid
import time
import logging
from backend.celery import app as celery_app
from .tasks import execute_workflow_task


logger = logging.getLogger(__name__)


# Authentication endpoints
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """Register a new user and return authentication token."""
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if User.objects.filter(username=username).exists():
        return Response(
            {'error': 'Username already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            }
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    """Authenticate user and return token."""
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(username=username, password=password)

    if user is None:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    token, _ = Token.objects.get_or_create(user=user)

    return Response({
        'token': token.key,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """Logout user by deleting their token."""
    try:
        request.user.auth_token.delete()
        return Response({'message': 'Successfully logged out'})
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """Get current authenticated user information."""
    return Response({
        'user': {
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
        }
    })


def _celery_workers_available(timeout: float = 1.0) -> bool:
    """Quickly check if any Celery workers are responding."""
    try:
        replies = celery_app.control.ping(timeout=timeout)
        return bool(replies)
    except Exception as exc:
        logger.warning("Celery worker availability check failed: %s", exc)
        return False


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
    Requires authentication.
    """
    queryset = Workflow.objects.all()
    serializer_class = WorkflowSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return workflows owned by the current user."""
        return Workflow.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        """Set owner to current authenticated user."""
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        """Generate API key if api_enabled is set to True and no key exists."""
        instance = serializer.save()
        if instance.api_enabled and not instance.api_key:
            instance.generate_api_key()
            instance.save()


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
      "startNodeId": "optional-node-id",
      "workflowId": 123  // optional, for saving execution history
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
    workflow_id = payload.get('workflowId')

    if not nodes:
        return Response(
            {"status": "error", "error": "nodes are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Ensure a worker is available before enqueuing
    if not _celery_workers_available():
        return Response(
            {'status': 'error', 'error': 'Task workers are unavailable. Please start a Celery worker and retry.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    # Generate unique execution ID
    execution_id = str(uuid.uuid4())

    # Create execution record if workflow_id is provided
    execution_record = None
    if workflow_id:
        try:
            workflow = Workflow.objects.get(id=workflow_id)
            input_data = context.get('input', '')
            execution_record = WorkflowExecution.objects.create(
                workflow=workflow,
                execution_id=execution_id,
                input_data=str(input_data),
                status='running',
                triggered_by='manual'
            )
        except Workflow.DoesNotExist:
            pass  # Continue without saving history if workflow not found

    # Execute workflow in background using Celery
    try:
        execute_workflow_task.delay(
            execution_id=execution_id,
            nodes=nodes,
            edges=edges,
            context=context,
            start_node_id=start_node_id,
            workflow_execution_id=execution_record.id if execution_record else None
        )
    except Exception as exc:
        logger.exception("Failed to enqueue workflow %s", execution_id)
        cache.set(
            f'execution_{execution_id}',
            {
                'status': 'error',
                'error': 'Task queue is unavailable',
                'currentNodeId': None,
                'completedNodes': [],
                'errorNodes': [],
                'trace': [],
                'steps': 0,
                'final': None,
                'timestamp': time.time(),
            },
            timeout=300
        )
        if execution_record:
            execution_record.status = 'error'
            execution_record.error_message = 'Task queue is unavailable'
            execution_record.save(update_fields=['status', 'error_message'])
        return Response(
            {'status': 'error', 'error': 'Task queue is unavailable. Please retry later.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

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


@api_view(['POST'])
def trigger_workflow(request, workflow_id):
    """
    Trigger a workflow execution via external API call.

    Requires X-API-Key header with the workflow's API key.

    Expected payload:
    {
      "input": "text input for the workflow"
    }

    Returns:
    {
      "executionId": "uuid-string",
      "status": "started"
    }
    """
    # Get API key from header
    api_key = request.headers.get('X-API-Key')

    if not api_key:
        return Response(
            {"status": "error", "error": "X-API-Key header is required"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Get workflow
    try:
        workflow = Workflow.objects.get(id=workflow_id)
    except Workflow.DoesNotExist:
        return Response(
            {"status": "error", "error": "Workflow not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # Check if API access is enabled
    if not workflow.api_enabled:
        return Response(
            {"status": "error", "error": "API access is not enabled for this workflow"},
            status=status.HTTP_403_FORBIDDEN
        )

    # Verify API key
    if workflow.api_key != api_key:
        return Response(
            {"status": "error", "error": "Invalid API key"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Get input from request
    input_data = request.data.get('input', '')

    # Prepare execution context
    nodes = workflow.nodes
    edges = workflow.edges
    context = {"input": input_data}

    if not nodes:
        return Response(
            {"status": "error", "error": "Workflow has no nodes"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Ensure a worker is available before enqueuing
    if not _celery_workers_available():
        return Response(
            {"status": "error", "error": "Task workers are unavailable. Please start a Celery worker and retry."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    # Generate unique execution ID
    execution_id = str(uuid.uuid4())

    # Create execution record
    execution_record = WorkflowExecution.objects.create(
        workflow=workflow,
        execution_id=execution_id,
        input_data=str(input_data),
        status='running',
        triggered_by='api'
    )

    # Execute workflow in background using Celery
    try:
        execute_workflow_task.delay(
            execution_id=execution_id,
            nodes=nodes,
            edges=edges,
            context=context,
            start_node_id=None,
            workflow_execution_id=execution_record.id
        )
    except Exception as exc:
        logger.exception("Failed to enqueue workflow %s", execution_id)
        cache.set(
            f'execution_{execution_id}',
            {
                'status': 'error',
                'error': 'Task queue is unavailable',
                'currentNodeId': None,
                'completedNodes': [],
                'errorNodes': [],
                'trace': [],
                'steps': 0,
                'final': None,
                'timestamp': time.time(),
            },
            timeout=300
        )
        execution_record.status = 'error'
        execution_record.error_message = 'Task queue is unavailable'
        execution_record.save(update_fields=['status', 'error_message'])
        return Response(
            {"status": "error", "error": "Task queue is unavailable. Please retry later."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    return Response({
        "executionId": execution_id,
        "status": "started"
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
def regenerate_api_key(request, workflow_id):
    """
    Regenerate the API key for a workflow.

    Returns:
    {
      "api_key": "new-api-key"
    }
    """
    try:
        workflow = Workflow.objects.get(id=workflow_id)
    except Workflow.DoesNotExist:
        return Response(
            {"status": "error", "error": "Workflow not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # Generate new API key
    workflow.generate_api_key()
    workflow.save()

    return Response({
        "api_key": workflow.api_key
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def workflow_executions(request, workflow_id):
    """
    Get execution history for a workflow.

    Query parameters:
    - limit: Number of executions to return (default: 50, max: 100)
    - offset: Offset for pagination (default: 0)

    Returns:
    {
      "count": 123,
      "results": [
        {
          "id": 1,
          "execution_id": "uuid",
          "input_data": "...",
          "final_output": "...",
          "status": "completed",
          "error_message": "",
          "execution_time": 1.23,
          "triggered_by": "api",
          "created_at": "2025-11-25T21:00:00Z"
        },
        ...
      ]
    }
    """
    try:
        workflow = Workflow.objects.get(id=workflow_id)
    except Workflow.DoesNotExist:
        return Response(
            {"status": "error", "error": "Workflow not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # Get pagination parameters
    limit = int(request.GET.get('limit', 50))
    offset = int(request.GET.get('offset', 0))
    limit = min(limit, 100)  # Cap at 100

    # Get executions
    executions = workflow.executions.all()[offset:offset + limit]
    total_count = workflow.executions.count()

    results = []
    for execution in executions:
        results.append({
            'id': execution.id,
            'execution_id': execution.execution_id,
            'input_data': execution.input_data,
            'final_output': execution.final_output,
            'status': execution.status,
            'error_message': execution.error_message,
            'execution_time': execution.execution_time,
            'triggered_by': execution.triggered_by,
            'created_at': execution.created_at.isoformat(),
            'trace': execution.trace  # Include trace for detailed view
        })

    return Response({
        'count': total_count,
        'results': results
    }, status=status.HTTP_200_OK)


# Workflow Schedule endpoints
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def workflow_schedules(request, workflow_id):
    """Get all schedules or create a new schedule for a workflow."""
    from croniter import croniter
    from datetime import datetime
    import pytz
    from django.shortcuts import get_object_or_404

    workflow = get_object_or_404(Workflow, id=workflow_id, owner=request.user)

    if request.method == 'GET':
        schedules = workflow.schedules.all()
        serializer = WorkflowScheduleSerializer(schedules, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        cron_node_id = request.data.get('cron_node_id')
        cron_expression = request.data.get('cron_expression')
        timezone_str = request.data.get('timezone', 'UTC')

        if not cron_node_id or not cron_expression:
            return Response({
                'error': 'cron_node_id and cron_expression are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate cron expression
        try:
            croniter(cron_expression)
        except Exception as e:
            return Response({
                'error': f'Invalid cron expression: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate timezone
        try:
            user_tz = pytz.timezone(timezone_str)
        except Exception:
            return Response({
                'error': f'Invalid timezone: {timezone_str}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Calculate next run
        now = datetime.now(user_tz)
        cron = croniter(cron_expression, now)
        next_run = cron.get_next(datetime).astimezone(pytz.utc)

        # Create or update schedule
        schedule, created = WorkflowSchedule.objects.update_or_create(
            workflow=workflow,
            cron_node_id=cron_node_id,
            defaults={
                'cron_expression': cron_expression,
                'timezone': timezone_str,
                'next_run': next_run,
                'is_active': True
            }
        )

        serializer = WorkflowScheduleSerializer(schedule)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def workflow_schedule_detail(request, workflow_id, schedule_id):
    """Get or delete a specific schedule."""
    from django.shortcuts import get_object_or_404

    workflow = get_object_or_404(Workflow, id=workflow_id, owner=request.user)
    schedule = get_object_or_404(WorkflowSchedule, id=schedule_id, workflow=workflow)

    if request.method == 'GET':
        serializer = WorkflowScheduleSerializer(schedule)
        return Response(serializer.data)

    elif request.method == 'DELETE':
        schedule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def toggle_workflow_schedule(request, workflow_id, schedule_id):
    """Enable/disable a schedule without deleting it."""
    from django.shortcuts import get_object_or_404

    workflow = get_object_or_404(Workflow, id=workflow_id, owner=request.user)
    schedule = get_object_or_404(WorkflowSchedule, id=schedule_id, workflow=workflow)

    is_active = request.data.get('is_active')
    if is_active is None:
        return Response({
            'error': 'is_active field is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    schedule.is_active = is_active
    schedule.save()

    serializer = WorkflowScheduleSerializer(schedule)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_workflow_schedules(request, workflow_id):
    """
    Auto-sync schedules based on cron_trigger nodes in the workflow.
    Creates/updates schedules for all cron_trigger nodes (inactive by default).
    Deactivates schedules for deleted nodes.
    """
    from django.shortcuts import get_object_or_404
    from croniter import croniter
    from datetime import datetime
    import pytz

    workflow = get_object_or_404(Workflow, id=workflow_id, owner=request.user)

    # Find all cron_trigger nodes in the workflow
    cron_nodes = [node for node in workflow.nodes if node.get('type') == 'cron_trigger']
    cron_node_ids = {node['id'] for node in cron_nodes}

    created_count = 0
    updated_count = 0
    deactivated_count = 0

    # Create/update schedules for each cron_trigger node
    for node in cron_nodes:
        node_id = node['id']
        node_data = node.get('data', {})
        cron_expression = node_data.get('cronExpression', '')
        timezone_str = node_data.get('timezone', 'UTC')

        # Skip if no cron expression is set
        if not cron_expression:
            continue

        # Validate cron expression
        try:
            croniter(cron_expression)
        except Exception:
            continue  # Skip invalid cron expressions

        # Validate timezone
        try:
            user_tz = pytz.timezone(timezone_str)
        except Exception:
            timezone_str = 'UTC'
            user_tz = pytz.utc

        # Calculate next run
        now = datetime.now(user_tz)
        cron = croniter(cron_expression, now)
        next_run = cron.get_next(datetime).astimezone(pytz.utc)

        # Check if schedule already exists to preserve is_active status
        try:
            existing_schedule = WorkflowSchedule.objects.get(
                workflow=workflow,
                cron_node_id=node_id
            )
            existing_is_active = existing_schedule.is_active
        except WorkflowSchedule.DoesNotExist:
            existing_is_active = False  # New schedules are inactive by default

        # Create or update schedule
        schedule, created = WorkflowSchedule.objects.update_or_create(
            workflow=workflow,
            cron_node_id=node_id,
            defaults={
                'cron_expression': cron_expression,
                'timezone': timezone_str,
                'next_run': next_run,
                'is_active': existing_is_active
            }
        )

        if created:
            created_count += 1
        else:
            updated_count += 1

    # Deactivate schedules for nodes that no longer exist
    orphaned_schedules = WorkflowSchedule.objects.filter(
        workflow=workflow,
        is_active=True
    ).exclude(cron_node_id__in=cron_node_ids)

    deactivated_count = orphaned_schedules.count()
    orphaned_schedules.update(is_active=False)

    return Response({
        'status': 'success',
        'created': created_count,
        'updated': updated_count,
        'deactivated': deactivated_count,
        'total_schedules': WorkflowSchedule.objects.filter(workflow=workflow).count()
    })

# Health check endpoint for Docker
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Simple health check endpoint for Docker healthcheck."""
    return Response({'status': 'healthy', 'service': 'vibeengine-api'}, status=status.HTTP_200_OK)

