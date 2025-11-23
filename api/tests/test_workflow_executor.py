from django.test import TestCase
from unittest.mock import patch, MagicMock
from api.orchestration import WorkflowExecutor
from api.drivers import DriverResponse


class WorkflowExecutorTestCase(TestCase):
    """Test suite for WorkflowExecutor class."""

    def setUp(self):
        self.executor = WorkflowExecutor()

    def test_empty_nodes_returns_error(self):
        """Test that empty nodes list returns error."""
        result = self.executor.execute(nodes=[], edges=[])
        self.assertEqual(result.status, 'error')
        self.assertEqual(result.error, 'nodes are required')

    def test_simple_input_output_workflow(self):
        """Test basic workflow: input -> output."""
        nodes = [
            {'id': '1', 'type': 'input', 'data': {'value': 'test input'}},
            {'id': '2', 'type': 'output', 'data': {}}
        ]
        edges = [
            {'source': '1', 'target': '2', 'id': 'e1'}
        ]
        result = self.executor.execute(nodes=nodes, edges=edges)

        self.assertEqual(result.status, 'ok')
        self.assertEqual(result.steps, 2)
        self.assertEqual(result.final, 'test input')
        self.assertEqual(len(result.trace), 2)
        self.assertEqual(result.start_node_id, '1')

    def test_workflow_with_explicit_start_node(self):
        """Test workflow with explicitly specified start node."""
        nodes = [
            {'id': '1', 'type': 'input', 'data': {'value': 'first'}},
            {'id': '2', 'type': 'input', 'data': {'value': 'second'}},
            {'id': '3', 'type': 'output', 'data': {}}
        ]
        edges = [
            {'source': '1', 'target': '3', 'id': 'e1'},
            {'source': '2', 'target': '3', 'id': 'e2'}
        ]
        result = self.executor.execute(nodes=nodes, edges=edges, start_node_id='2')

        self.assertEqual(result.status, 'ok')
        self.assertEqual(result.start_node_id, '2')
        self.assertEqual(result.final, 'second')

    def test_context_input_override(self):
        """Test that explicit context input overrides node default value."""
        nodes = [
            {'id': '1', 'type': 'input', 'data': {'value': 'default'}},
            {'id': '2', 'type': 'output', 'data': {}}
        ]
        edges = [{'source': '1', 'target': '2', 'id': 'e1'}]
        context = {'input': 'override value'}

        result = self.executor.execute(nodes=nodes, edges=edges, context=context)
        self.assertEqual(result.final, 'override value')

    def test_router_node_yes_path(self):
        """Test router node taking 'yes' path when condition is True."""
        nodes = [
            {'id': '1', 'type': 'input', 'data': {'value': 'start'}},
            {'id': '2', 'type': 'router', 'data': {}},
            {'id': '3', 'type': 'output', 'data': {}},  # yes path
            {'id': '4', 'type': 'output', 'data': {}}   # no path
        ]
        edges = [
            {'source': '1', 'target': '2', 'id': 'e1'},
            {'source': '2', 'target': '3', 'id': 'e2', 'sourceHandle': 'yes'},
            {'source': '2', 'target': '4', 'id': 'e3', 'sourceHandle': 'no'}
        ]
        context = {'condition': True}

        result = self.executor.execute(nodes=nodes, edges=edges, context=context)
        self.assertEqual(result.status, 'ok')
        # Should follow yes path to node 3
        self.assertEqual(result.trace[2]['nodeId'], '3')

    def test_router_node_no_path(self):
        """Test router node taking 'no' path when condition is False."""
        nodes = [
            {'id': '1', 'type': 'input', 'data': {'value': 'start'}},
            {'id': '2', 'type': 'router', 'data': {}},
            {'id': '3', 'type': 'output', 'data': {}},  # yes path
            {'id': '4', 'type': 'output', 'data': {}}   # no path
        ]
        edges = [
            {'source': '1', 'target': '2', 'id': 'e1'},
            {'source': '2', 'target': '3', 'id': 'e2', 'sourceHandle': 'yes'},
            {'source': '2', 'target': '4', 'id': 'e3', 'sourceHandle': 'no'}
        ]
        context = {'condition': False}

        result = self.executor.execute(nodes=nodes, edges=edges, context=context)
        self.assertEqual(result.status, 'ok')
        # Should follow no path to node 4
        self.assertEqual(result.trace[2]['nodeId'], '4')

    def test_memory_and_tool_edges_excluded_from_control_flow(self):
        """Test that edges to memory/tool nodes are excluded from control flow."""
        nodes = [
            {'id': '1', 'type': 'input', 'data': {'value': 'test'}},
            {'id': '2', 'type': 'memory', 'data': {'key': 'test_key'}},
            {'id': '3', 'type': 'tool', 'data': {'operation': 'echo'}},
            {'id': '4', 'type': 'output', 'data': {}}
        ]
        edges = [
            {'source': '1', 'target': '2', 'id': 'e1'},  # to memory
            {'source': '1', 'target': '3', 'id': 'e2'},  # to tool
            {'source': '1', 'target': '4', 'id': 'e3'}   # to output
        ]

        result = self.executor.execute(nodes=nodes, edges=edges)
        self.assertEqual(result.status, 'ok')
        # Should skip memory/tool and go directly to output
        self.assertEqual(result.trace[0]['nextNodeId'], '4')

    def test_preferred_edge_selection(self):
        """Test edge selection with preferred handles."""
        nodes = [
            {'id': '1', 'type': 'input', 'data': {'value': 'test'}},
            {'id': '2', 'type': 'output', 'data': {}},
            {'id': '3', 'type': 'output', 'data': {}}
        ]
        edges = [
            {'source': '1', 'target': '2', 'id': 'e1', 'sourceHandle': 'other'},
            {'source': '1', 'target': '3', 'id': 'e2', 'sourceHandle': 'out'}  # preferred
        ]

        result = self.executor.execute(nodes=nodes, edges=edges)
        # Should prefer 'out' handle
        self.assertEqual(result.trace[0]['nextNodeId'], '3')

    def test_priority_based_edge_selection(self):
        """Test edge selection based on target node type priority."""
        nodes = [
            {'id': '1', 'type': 'input', 'data': {'value': 'test'}},
            {'id': '2', 'type': 'output', 'data': {}},      # priority: 1
            {'id': '3', 'type': 'claude_agent', 'data': {}} # priority: 9
        ]
        edges = [
            {'source': '1', 'target': '2', 'id': 'e1'},
            {'source': '1', 'target': '3', 'id': 'e2'}
        ]

        result = self.executor.execute(nodes=nodes, edges=edges)
        # Should prefer agent over output
        self.assertEqual(result.trace[0]['nextNodeId'], '3')

    def test_max_steps_limit(self):
        """Test that executor respects max steps limit."""
        # Create a circular workflow
        nodes = [
            {'id': '1', 'type': 'input', 'data': {'value': 'test'}},
            {'id': '2', 'type': 'input', 'data': {'value': 'loop'}}
        ]
        edges = [
            {'source': '1', 'target': '2', 'id': 'e1'},
            {'source': '2', 'target': '1', 'id': 'e2'}
        ]

        executor = WorkflowExecutor(max_steps=5)
        result = executor.execute(nodes=nodes, edges=edges)

        self.assertEqual(result.status, 'ok')
        self.assertEqual(result.steps, 5)

    def test_state_propagation(self):
        """Test that state is propagated through context."""
        # Note: Memory/tool nodes are not part of control flow when they're targets
        # They're only used as context by agent nodes
        # So we test state propagation through multiple non-memory nodes
        nodes = [
            {'id': '1', 'type': 'input', 'data': {'value': 'test'}},
            {'id': '2', 'type': 'router', 'data': {}},
            {'id': '3', 'type': 'output', 'data': {}}
        ]
        edges = [
            {'source': '1', 'target': '2', 'id': 'e1'},
            {'source': '2', 'target': '3', 'id': 'e2', 'sourceHandle': 'no'}
        ]

        result = self.executor.execute(nodes=nodes, edges=edges, context={'state': {'initial': 'value'}})
        self.assertEqual(result.status, 'ok')
        # State should be maintained through execution
        self.assertEqual(len(result.trace), 3)

    def test_node_execution_error_handling(self):
        """Test that executor handles node execution errors."""
        nodes = [
            {'id': '1', 'type': 'invalid_type', 'data': {}},
            {'id': '2', 'type': 'output', 'data': {}}
        ]
        edges = [{'source': '1', 'target': '2', 'id': 'e1'}]

        result = self.executor.execute(nodes=nodes, edges=edges)
        self.assertEqual(result.status, 'error')
        self.assertIsNotNone(result.error)

    def test_no_outgoing_edges_stops_execution(self):
        """Test that execution stops when node has no outgoing edges."""
        nodes = [
            {'id': '1', 'type': 'input', 'data': {'value': 'test'}},
            {'id': '2', 'type': 'input', 'data': {'value': 'no edges'}}
        ]
        edges = [{'source': '1', 'target': '2', 'id': 'e1'}]

        result = self.executor.execute(nodes=nodes, edges=edges)
        self.assertEqual(result.status, 'ok')
        self.assertEqual(result.steps, 2)

    def test_trace_includes_all_execution_details(self):
        """Test that trace includes all relevant execution information."""
        nodes = [
            {'id': '1', 'type': 'input', 'data': {'value': 'test'}},
            {'id': '2', 'type': 'output', 'data': {}}
        ]
        edges = [{'source': '1', 'target': '2', 'id': 'e1'}]

        result = self.executor.execute(nodes=nodes, edges=edges)

        # Check first trace entry
        trace_entry = result.trace[0]
        self.assertEqual(trace_entry['nodeId'], '1')
        self.assertEqual(trace_entry['type'], 'input')
        self.assertIn('result', trace_entry)
        self.assertEqual(trace_entry['edgeId'], 'e1')
        self.assertEqual(trace_entry['nextNodeId'], '2')

    @patch('api.orchestration.workflow_executor.execute_node_by_type')
    def test_agent_context_building_with_memory(self, mock_execute):
        """Test that agent nodes receive memory knowledge in context."""
        # Return different responses for agent vs output node
        def side_effect(node_type, node, context):
            if node_type in ('claude_agent', 'openai_agent'):
                return DriverResponse({'status': 'ok', 'output': 'agent result'})
            elif node_type == 'output':
                return DriverResponse({'status': 'ok', 'final': context.get('input')})
            return DriverResponse({'status': 'ok'})

        mock_execute.side_effect = side_effect

        nodes = [
            {'id': '1', 'type': 'claude_agent', 'data': {'system': 'test'}},
            {'id': '2', 'type': 'memory', 'data': {'key': 'test_mem', 'namespace': 'default'}},
            {'id': '3', 'type': 'output', 'data': {}}
        ]
        edges = [
            {'source': '1', 'target': '2', 'id': 'e1'},  # agent connected to memory
            {'source': '1', 'target': '3', 'id': 'e2'}
        ]

        result = self.executor.execute(nodes=nodes, edges=edges, context={'input': 'test'})

        # Check that agent was called with knowledge context
        agent_call = mock_execute.call_args_list[0]
        exec_context = agent_call[0][2]
        self.assertIn('knowledge', exec_context)

    @patch('api.orchestration.workflow_executor.execute_node_by_type')
    def test_agent_context_building_with_tools(self, mock_execute):
        """Test that agent nodes receive tool specs in context."""
        def side_effect(node_type, node, context):
            if node_type in ('claude_agent', 'openai_agent'):
                return DriverResponse({'status': 'ok', 'output': 'agent result'})
            elif node_type == 'output':
                return DriverResponse({'status': 'ok', 'final': context.get('input')})
            return DriverResponse({'status': 'ok'})

        mock_execute.side_effect = side_effect

        nodes = [
            {'id': '1', 'type': 'openai_agent', 'data': {'system': 'test'}},
            {'id': '2', 'type': 'tool', 'data': {'label': 'TestTool', 'operation': 'echo'}},
            {'id': '3', 'type': 'output', 'data': {}}
        ]
        edges = [
            {'source': '1', 'target': '2', 'id': 'e1'},
            {'source': '1', 'target': '3', 'id': 'e2'}
        ]

        result = self.executor.execute(nodes=nodes, edges=edges, context={'input': 'test'})

        # Check that agent was called with tool specs
        agent_call = mock_execute.call_args_list[0]
        exec_context = agent_call[0][2]
        self.assertIn('agent_tools', exec_context)
        self.assertEqual(len(exec_context['agent_tools']), 1)
        self.assertEqual(exec_context['agent_tools'][0]['name'], 'TestTool')

    def test_trace_records_used_memory_and_tools(self):
        """Test that trace records which memory/tools were used by agents."""
        nodes = [
            {'id': '1', 'type': 'claude_agent', 'data': {}},
            {'id': '2', 'type': 'memory', 'data': {'key': 'mem1'}},
            {'id': '3', 'type': 'tool', 'data': {'label': 'tool1'}},
            {'id': '4', 'type': 'output', 'data': {}}
        ]
        edges = [
            {'source': '1', 'target': '2', 'id': 'e1'},
            {'source': '1', 'target': '3', 'id': 'e2'},
            {'source': '1', 'target': '4', 'id': 'e3'}
        ]

        result = self.executor.execute(nodes=nodes, edges=edges, context={'input': 'test'})

        # Check trace for agent node
        agent_trace = result.trace[0]
        self.assertIn('2', agent_trace['usedMemory'])
        self.assertIn('3', agent_trace['usedTools'])

    def test_output_propagation_chain(self):
        """Test that output from one node becomes input for next node."""
        # Note: tool/memory nodes are excluded from control flow, so we use input nodes for chaining
        nodes = [
            {'id': '1', 'type': 'input', 'data': {'value': 'initial'}},
            {'id': '2', 'type': 'input', 'data': {'value': 'ignored'}},  # Will use context input instead
            {'id': '3', 'type': 'output', 'data': {}}
        ]
        edges = [
            {'source': '1', 'target': '2', 'id': 'e1'},
            {'source': '2', 'target': '3', 'id': 'e2'}
        ]

        result = self.executor.execute(nodes=nodes, edges=edges)
        self.assertEqual(result.status, 'ok')
        # Input from node 1 should propagate through to output
        self.assertEqual(result.final, 'initial')

    def test_start_node_selection_priority(self):
        """Test start node selection priority: explicit > input type > no incoming > first."""
        # Test: no incoming edges when no input type exists
        nodes = [
            {'id': '1', 'type': 'tool', 'data': {}},
            {'id': '2', 'type': 'output', 'data': {}}
        ]
        edges = [{'source': '1', 'target': '2', 'id': 'e1'}]

        result = self.executor.execute(nodes=nodes, edges=edges, context={'input': 'test'})
        self.assertEqual(result.start_node_id, '1')
