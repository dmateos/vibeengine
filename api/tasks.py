"""
Celery tasks for VibeEngine workflow execution.
"""
import time
import logging
from typing import Dict, Any, List, Optional
from celery import shared_task
from django.core.cache import cache
from .orchestration.polling_executor import PollingExecutor
from .models import WorkflowExecution

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
