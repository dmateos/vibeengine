"""
Celery tasks for VibeEngine workflow execution.
"""
import time
import logging
from typing import Dict, Any, List, Optional
from celery import shared_task
from django.core.cache import cache
from .orchestration.polling_executor import PollingExecutor
from .models import WorkflowExecution, WorkflowSchedule

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='api.execute_workflow')
def execute_workflow_task(
    self,
    execution_id: str,
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    context: Dict[str, Any],
    start_node_id: Optional[str] = None,
    workflow_execution_id: Optional[int] = None
):
    """
    Execute a workflow in the background using Celery.

    Args:
        execution_id: Unique execution identifier
        nodes: Workflow nodes
        edges: Workflow edges
        context: Execution context including input and state
        start_node_id: Optional starting node ID
        workflow_execution_id: Optional WorkflowExecution database record ID

    Returns:
        Dict with execution status and results
    """
    start_time = time.time()

    logger.info(f"[Celery Task] Starting workflow execution - ID: {execution_id}")
    logger.info(f"[Celery Task] Nodes: {len(nodes)}, Edges: {len(edges)}")
    logger.debug(f"[Celery Task] Context: {str(context)[:200]}...")

    try:
        # Execute the workflow
        logger.info(f"[Celery Task] Creating PollingExecutor for {execution_id}")
        executor = PollingExecutor(execution_id=execution_id)
        executor.execute(nodes, edges, context, start_node_id)
        logger.info(f"[Celery Task] PollingExecutor completed for {execution_id}")

        # Wait for executor to finish and update cache
        time.sleep(0.5)

        # Get final result from cache
        execution_state = cache.get(f'execution_{execution_id}')
        logger.info(f"[Celery Task] Retrieved execution state from cache for {execution_id}")
        logger.debug(f"[Celery Task] State status: {execution_state.get('status') if execution_state else 'None'}")

        # Update execution record if provided
        if workflow_execution_id:
            try:
                execution_record = WorkflowExecution.objects.get(id=workflow_execution_id)
                if execution_state:
                    execution_time = time.time() - start_time
                    execution_record.status = execution_state.get('status', 'completed')
                    execution_record.final_output = str(execution_state.get('final', ''))
                    execution_record.trace = execution_state.get('trace', [])
                    error_msg = execution_state.get('error')
                    execution_record.error_message = error_msg if error_msg else ''
                    execution_record.execution_time = execution_time
                    execution_record.save()
            except WorkflowExecution.DoesNotExist:
                pass  # Record was deleted, ignore

        execution_time = time.time() - start_time
        final_status = execution_state.get('status', 'completed') if execution_state else 'unknown'
        logger.info(f"[Celery Task] Workflow completed - ID: {execution_id}, Status: {final_status}, Time: {execution_time:.2f}s")

        return {
            'execution_id': execution_id,
            'status': final_status,
            'execution_time': execution_time
        }

    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = str(e)

        logger.error(f"[Celery Task] Workflow failed - ID: {execution_id}, Error: {error_msg}, Time: {execution_time:.2f}s")

        # Update cache with error
        cache.set(f'execution_{execution_id}', {
            'status': 'error',
            'error': error_msg,
            'currentNodeId': None,
            'completedNodes': [],
            'errorNodes': [],
            'trace': []
        }, timeout=300)

        # Update execution record if provided
        if workflow_execution_id:
            try:
                execution_record = WorkflowExecution.objects.get(id=workflow_execution_id)
                execution_record.status = 'error'
                execution_record.error_message = error_msg
                execution_record.execution_time = execution_time
                execution_record.save()
            except WorkflowExecution.DoesNotExist:
                pass  # Record was deleted, ignore

        # Re-raise the exception so Celery marks the task as failed
        raise


@shared_task(bind=True, name='api.execute_branch')
def execute_branch_task(
    self,
    branch_id: str,
    start_node: Dict[str, Any],
    context: Dict[str, Any],
    outgoing: Dict[str, List[Dict[str, Any]]],
    node_by_id: Dict[str, Dict[str, Any]],
    edges: List[Dict[str, Any]],
    max_steps: int = 100,
    execution_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a single branch in parallel execution.

    Args:
        branch_id: Unique identifier for this branch
        start_node: Starting node for this branch
        context: Execution context for this branch
        outgoing: Outgoing edges map
        node_by_id: Node lookup map
        edges: All workflow edges
        max_steps: Maximum steps to execute

    Returns:
        Dict with final_output and trace
    """
    from .orchestration.workflow_executor import WorkflowExecutor

    logger.info(f"[Branch Task] Starting branch execution - ID: {branch_id}, Node: {start_node.get('id')}")

    def _update_parallel_status(status: str, error: Optional[str] = None):
        """Push branch status into execution cache if execution_id is provided."""
        if not execution_id:
            return
        cache_key = f'execution_{execution_id}'
        state = cache.get(cache_key, {})
        parallel_status = state.get('parallelStatus', {}) or {}
        parallel_status[branch_id] = status
        if error:
            state['error'] = error
        state['parallelStatus'] = parallel_status
        cache.set(cache_key, state, timeout=300)

    _update_parallel_status('running')

    try:
        executor = WorkflowExecutor()

        # Execute the branch
        final_output, trace = executor._execute_branch(
            start_node, context, outgoing, node_by_id, edges, max_steps
        )

        logger.info(f"[Branch Task] Branch {branch_id} completed successfully")
        logger.debug(f"[Branch Task] Branch {branch_id} output: {str(final_output)[:100]}...")
        _update_parallel_status('ok')

        return {
            'branch_id': branch_id,
            'final_output': final_output,
            'trace': trace,
            'status': 'ok'
        }

    except Exception as e:
        logger.error(f"[Branch Task] Branch {branch_id} failed: {str(e)}")
        _update_parallel_status('error', str(e))
        return {
            'branch_id': branch_id,
            'final_output': None,
            'trace': [],
            'status': 'error',
            'error': str(e)
        }


@shared_task(name='api.check_scheduled_workflows')
def check_and_execute_scheduled_workflows():
    """
    Check for workflows due to run and execute them.
    This task runs every minute via Celery Beat.
    """
    from croniter import croniter
    from datetime import datetime, timezone as tz
    import pytz
    import uuid

    logger.info("[Scheduler] Checking for scheduled workflows...")

    now = datetime.now(tz.utc)

    # Find all active schedules that are due
    schedules = WorkflowSchedule.objects.filter(
        is_active=True,
        next_run__lte=now
    ).select_related('workflow')

    logger.info(f"[Scheduler] Found {schedules.count()} schedules due to run")

    for schedule in schedules:
        try:
            workflow = schedule.workflow
            logger.info(f"[Scheduler] Executing workflow '{workflow.name}' (ID: {workflow.id}) - Schedule: {schedule.cron_expression}")

            # Create execution record
            execution_id = str(uuid.uuid4())
            execution_record = WorkflowExecution.objects.create(
                workflow=workflow,
                execution_id=execution_id,
                input_data='{}',
                status='running',
                triggered_by='scheduled'
            )

            # Execute workflow asynchronously
            execute_workflow_task.delay(
                execution_id=execution_id,
                nodes=workflow.nodes,
                edges=workflow.edges,
                context={'input': {}, 'state': {}, 'params': {}},
                start_node_id=schedule.cron_node_id,
                workflow_execution_id=execution_record.id
            )

            # Update schedule
            schedule.last_run = now

            # Calculate next run using user's timezone
            user_tz = pytz.timezone(schedule.timezone)
            now_in_tz = now.astimezone(user_tz)
            cron = croniter(schedule.cron_expression, now_in_tz)
            next_run_in_tz = cron.get_next(datetime)
            schedule.next_run = next_run_in_tz.astimezone(tz.utc)
            schedule.save()

            logger.info(f"[Scheduler] Workflow '{workflow.name}' scheduled - Execution ID: {execution_id}, Next run: {schedule.next_run}")

        except Exception as e:
            logger.error(f"[Scheduler] Error executing scheduled workflow {schedule.id}: {str(e)}")
            # Continue with other schedules even if one fails
            continue

    logger.info("[Scheduler] Finished checking scheduled workflows")
