"""
For Each loop driver for iterating over arrays.
"""

import logging
from typing import Dict, Any, List
from .base import BaseDriver, DriverResponse

logger = logging.getLogger(__name__)


class ForEachDriver(BaseDriver):
    type = "for_each"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        """
        Execute a for-each loop over an array.

        Uses dual output handles:
        - 'body' handle: connects to loop body start
        - 'exit' handle: connects to post-loop continuation
        """
        input_data = context.get("input", [])

        # Validate input is iterable
        if not isinstance(input_data, (list, tuple)):
            return DriverResponse({
                "status": "error",
                "error": f"For Each requires an array/list input, got {type(input_data).__name__}"
            })

        # Get configuration
        item_var = node.get("data", {}).get("item_var", "item")
        collect_results = node.get("data", {}).get("collect_results", True)
        max_iterations = int(node.get("data", {}).get("max_iterations", 1000))

        # Get graph structure from context
        edges = context.get("_edges", [])
        nodes = context.get("_nodes", {})

        if not edges or not nodes:
            return DriverResponse({
                "status": "error",
                "error": "For Each requires graph structure (_edges and _nodes in context)"
            })

        # Find body and exit edges
        node_id = str(node.get("id"))
        body_edge = self._find_edge(node_id, "body", edges)
        exit_edge = self._find_edge(node_id, "exit", edges)

        if not body_edge:
            logger.warning(f"For Each node {node_id} has no body edge, passing through")
            return DriverResponse({
                "status": "ok",
                "output": input_data,
                "route": "exit"  # Follow exit edge
            })

        # Execute loop iterations
        results = []
        items_to_process = input_data[:max_iterations]

        logger.info(f"For Each: Processing {len(items_to_process)} items (max: {max_iterations})")

        for i, item in enumerate(items_to_process):
            logger.debug(f"For Each iteration {i}/{len(items_to_process)}: {str(item)[:100]}")

            # Build iteration context
            iter_context = {
                **context,
                "input": item,
                item_var: item,
                "loop_index": i,
                "loop_total": len(items_to_process),
                "is_first": i == 0,
                "is_last": i == len(items_to_process) - 1
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

                if collect_results:
                    results.append(body_output)

            except Exception as e:
                logger.error(f"For Each iteration {i} failed: {str(e)}")
                return DriverResponse({
                    "status": "error",
                    "error": f"Loop iteration {i} failed: {str(e)}",
                    "iteration": i,
                    "partial_results": results
                })

        # Return collected results or original input
        output = results if collect_results else input_data

        logger.info(f"For Each completed: {len(results)} iterations, output length: {len(output) if isinstance(output, list) else 'N/A'}")

        return DriverResponse({
            "status": "ok",
            "output": output,
            "iterations": len(results),
            "route": "exit"  # Signal executor to follow exit edge
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
