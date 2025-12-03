"""
Loop driver for counter-based iteration.
"""

import logging
from typing import Dict, Any, List
from .base import BaseDriver, DriverResponse

logger = logging.getLogger(__name__)


class LoopDriver(BaseDriver):
    type = "loop"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        """
        Execute a counter-based loop (like a for loop).

        Uses dual output handles:
        - 'body' handle: connects to loop body start
        - 'exit' handle: connects to post-loop continuation
        """
        # Get configuration
        iterations = int(node.get("data", {}).get("iterations", 1))
        counter_var = node.get("data", {}).get("counter_var", "i")
        start_from = int(node.get("data", {}).get("start_from", 0))
        pass_through = node.get("data", {}).get("pass_through", True)

        # Validate iterations
        if iterations < 0:
            return DriverResponse({
                "status": "error",
                "error": "Iterations must be non-negative"
            })

        if iterations > 10000:
            return DriverResponse({
                "status": "error",
                "error": "Iterations cannot exceed 10,000"
            })

        # Get graph structure from context
        edges = context.get("_edges", [])
        nodes = context.get("_nodes", {})

        if not edges or not nodes:
            return DriverResponse({
                "status": "error",
                "error": "Loop requires graph structure (_edges and _nodes in context)"
            })

        # Find body and exit edges
        node_id = str(node.get("id"))
        body_edge = self._find_edge(node_id, "body", edges)
        exit_edge = self._find_edge(node_id, "exit", edges)

        if not body_edge:
            logger.warning(f"Loop node {node_id} has no body edge, passing through")
            return DriverResponse({
                "status": "ok",
                "output": context.get("input"),
                "route": "exit"
            })

        # Execute loop iterations
        result = context.get("input")
        results = []

        logger.info(f"Loop: Executing {iterations} iterations starting from {start_from}")

        for i in range(start_from, start_from + iterations):
            logger.debug(f"Loop iteration {i}/{start_from + iterations - 1}")

            # Build iteration context
            iter_context = {
                **context,
                "input": result if pass_through else context.get("input"),
                counter_var: i,
                "loop_index": i - start_from,  # 0-based index
                "loop_counter": i,  # Actual counter value
                "loop_total": iterations,
                "is_first": (i == start_from),
                "is_last": (i == start_from + iterations - 1)
            }

            try:
                # Execute loop body
                body_output = self._execute_body(
                    start_node_id=body_edge["target"],
                    stop_at_node_id=exit_edge["target"] if exit_edge else None,
                    context=iter_context,
                    edges=edges,
                    nodes=nodes
                )

                if pass_through:
                    result = body_output  # Chain output to next iteration
                else:
                    results.append(body_output)

            except Exception as e:
                logger.error(f"Loop iteration {i} failed: {str(e)}")
                return DriverResponse({
                    "status": "error",
                    "error": f"Loop iteration {i} failed: {str(e)}",
                    "iteration": i,
                    "partial_results": results if not pass_through else result
                })

        # Return final result
        if pass_through:
            output = result
        else:
            output = results

        logger.info(f"Loop completed: {iterations} iterations")

        return DriverResponse({
            "status": "ok",
            "output": output,
            "iterations": iterations,
            "route": "exit"
        })

    def _find_edge(self, source_id: str, handle_id: str, edges: List[Dict[str, Any]]) -> Dict[str, Any] | None:
        """Find edge by source node ID and source handle ID."""
        return next(
            (e for e in edges
             if str(e.get("source")) == source_id
             and e.get("sourceHandle") == handle_id),
            None
        )

    def _execute_body(self, start_node_id: str, stop_at_node_id: str | None,
                     context: Dict[str, Any], edges: List[Dict[str, Any]],
                     nodes: Dict[str, Dict[str, Any]]) -> Any:
        """
        Execute loop body from start node until stop node.

        Args:
            start_node_id: ID of first node in loop body
            stop_at_node_id: ID of node where loop body ends (exit point)
            context: Iteration context
            edges: All workflow edges
            nodes: Node lookup map

        Returns:
            Final output from loop body execution
        """
        from ..drivers import execute_node_by_type

        current_id = start_node_id
        max_steps = 100  # Prevent infinite loops within body
        steps = 0

        while current_id and steps < max_steps:
            # Stop if we've reached the exit point
            if stop_at_node_id and current_id == str(stop_at_node_id):
                logger.debug(f"Loop body reached exit node {stop_at_node_id}")
                break

            current_node = nodes.get(current_id)
            if not current_node:
                logger.warning(f"Loop body node {current_id} not found")
                break

            node_type = current_node.get("type")

            # Stop at output nodes
            if node_type == "output":
                break

            # Stop at loop end markers
            if node_type == "loop_end":
                break

            # Execute node
            logger.debug(f"Loop body executing node {current_id} ({node_type})")

            # Add graph structure to context for nodes that need it
            exec_context = {
                **context,
                "_edges": edges,
                "_nodes": nodes
            }

            result = execute_node_by_type(node_type, current_node, exec_context)

            if result.get("status") != "ok":
                error_msg = result.get("error", "node execution failed")
                raise Exception(f"Node {current_id} failed: {error_msg}")

            # Propagate output to next node
            if "output" in result:
                context["input"] = result["output"]

            # Update state if returned
            if "state" in result:
                context["state"] = result["state"]

            # Find next node in body
            next_edge = next(
                (e for e in edges if str(e.get("source")) == current_id),
                None
            )

            if not next_edge:
                logger.debug(f"Loop body ended at node {current_id} (no outgoing edges)")
                break

            current_id = str(next_edge.get("target"))
            steps += 1

        if steps >= max_steps:
            logger.warning(f"Loop body hit max steps ({max_steps})")

        return context.get("input")
