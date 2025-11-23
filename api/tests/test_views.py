from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from api.models import Workflow, NodeType
from api.drivers import DriverResponse
from api.orchestration import ExecutionResult


class ExecuteNodeViewTestCase(TestCase):
    """Test suite for execute_node API endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/execute-node/'

    def test_execute_node_success(self):
        """Test successful node execution."""
        payload = {
            'node': {
                'id': '1',
                'type': 'input',
                'data': {}
            },
            'context': {
                'input': 'test input'
            }
        }
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'ok')
        self.assertEqual(response.data['output'], 'test input')

    def test_execute_node_missing_type(self):
        """Test node execution with missing type returns error."""
        payload = {
            'node': {
                'id': '1',
                'data': {}
            },
            'context': {}
        }
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['status'], 'error')
        self.assertIn('required', response.data['error'])

    def test_execute_node_invalid_type(self):
        """Test node execution with invalid type."""
        payload = {
            'node': {
                'id': '1',
                'type': 'invalid_type',
                'data': {}
            },
            'context': {}
        }
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['status'], 'error')

    def test_execute_node_with_different_node_types(self):
        """Test execution of different node types."""
        test_cases = [
            ('input', {'input': 'test'}, 'output'),
            ('output', {'input': 'final'}, 'final'),
            ('router', {'condition': True}, 'route'),
        ]

        for node_type, context, expected_key in test_cases:
            payload = {
                'node': {'id': '1', 'type': node_type, 'data': {}},
                'context': context
            }
            response = self.client.post(self.url, payload, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn(expected_key, response.data)

    def test_execute_node_with_empty_payload(self):
        """Test node execution with empty payload uses defaults."""
        response = self.client.post(self.url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['status'], 'error')

    def test_execute_node_tool_uppercase(self):
        """Test tool node execution with uppercase operation."""
        payload = {
            'node': {
                'id': '1',
                'type': 'tool',
                'data': {'operation': 'uppercase'}
            },
            'context': {
                'input': 'hello world'
            }
        }
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['output'], 'HELLO WORLD')

    def test_execute_node_memory_storage(self):
        """Test memory node execution stores value."""
        payload = {
            'node': {
                'id': '1',
                'type': 'memory',
                'data': {'key': 'test_key', 'namespace': 'test_ns'}
            },
            'context': {
                'input': 'stored value'
            }
        }
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['stored'], 'stored value')
        self.assertIn('state', response.data)


class ExecuteWorkflowViewTestCase(TestCase):
    """Test suite for execute_workflow API endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/execute-workflow/'

    def test_execute_workflow_empty_nodes(self):
        """Test workflow execution with empty nodes returns error."""
        payload = {
            'nodes': [],
            'edges': [],
            'context': {}
        }
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['status'], 'error')
        self.assertEqual(response.data['error'], 'nodes are required')

    def test_execute_workflow_simple_input_output(self):
        """Test simple workflow: input -> output."""
        payload = {
            'nodes': [
                {'id': '1', 'type': 'input', 'data': {'value': 'test'}},
                {'id': '2', 'type': 'output', 'data': {}}
            ],
            'edges': [
                {'source': '1', 'target': '2', 'id': 'e1'}
            ],
            'context': {}
        }
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'ok')
        self.assertEqual(response.data['final'], 'test')
        self.assertEqual(response.data['steps'], 2)
        self.assertEqual(len(response.data['trace']), 2)

    def test_execute_workflow_with_context_input(self):
        """Test workflow with explicit context input."""
        payload = {
            'nodes': [
                {'id': '1', 'type': 'input', 'data': {'value': 'default'}},
                {'id': '2', 'type': 'output', 'data': {}}
            ],
            'edges': [
                {'source': '1', 'target': '2', 'id': 'e1'}
            ],
            'context': {
                'input': 'override'
            }
        }
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['final'], 'override')

    def test_execute_workflow_with_start_node_id(self):
        """Test workflow with explicitly specified start node."""
        payload = {
            'nodes': [
                {'id': '1', 'type': 'input', 'data': {'value': 'first'}},
                {'id': '2', 'type': 'input', 'data': {'value': 'second'}},
                {'id': '3', 'type': 'output', 'data': {}}
            ],
            'edges': [
                {'source': '1', 'target': '3', 'id': 'e1'},
                {'source': '2', 'target': '3', 'id': 'e2'}
            ],
            'context': {},
            'startNodeId': '2'
        }
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['startNodeId'], '2')
        self.assertEqual(response.data['final'], 'second')

    def test_execute_workflow_with_router(self):
        """Test workflow with router node."""
        payload = {
            'nodes': [
                {'id': '1', 'type': 'input', 'data': {'value': 'start'}},
                {'id': '2', 'type': 'router', 'data': {}},
                {'id': '3', 'type': 'output', 'data': {}},
                {'id': '4', 'type': 'output', 'data': {}}
            ],
            'edges': [
                {'source': '1', 'target': '2', 'id': 'e1'},
                {'source': '2', 'target': '3', 'id': 'e2', 'sourceHandle': 'yes'},
                {'source': '2', 'target': '4', 'id': 'e3', 'sourceHandle': 'no'}
            ],
            'context': {
                'condition': True
            }
        }
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should follow yes path to node 3
        self.assertEqual(response.data['trace'][2]['nodeId'], '3')

    def test_execute_workflow_with_router_chain(self):
        """Test workflow with chained router operations."""
        # Note: tool/memory nodes are excluded from control flow
        # Input nodes pass through context.input, they don't replace it
        payload = {
            'nodes': [
                {'id': '1', 'type': 'input', 'data': {'value': 'hello'}},
                {'id': '2', 'type': 'router', 'data': {}},
                {'id': '3', 'type': 'output', 'data': {}},
                {'id': '4', 'type': 'output', 'data': {}}
            ],
            'edges': [
                {'source': '1', 'target': '2', 'id': 'e1'},
                {'source': '2', 'target': '3', 'id': 'e2', 'sourceHandle': 'yes'},
                {'source': '2', 'target': '4', 'id': 'e3', 'sourceHandle': 'no'}
            ],
            'context': {'condition': True}
        }
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should take yes path to node 3
        self.assertEqual(response.data['trace'][2]['nodeId'], '3')
        self.assertEqual(response.data['final'], 'hello')

    def test_execute_workflow_with_agent_using_memory(self):
        """Test workflow where agent uses memory node."""
        # Memory nodes are excluded from control flow but accessible by agents
        payload = {
            'nodes': [
                {'id': '1', 'type': 'input', 'data': {'value': 'test input'}},
                {'id': '2', 'type': 'claude_agent', 'data': {'system': 'You are helpful'}},
                {'id': '3', 'type': 'memory', 'data': {'key': 'my_memory', 'namespace': 'default'}},
                {'id': '4', 'type': 'output', 'data': {}}
            ],
            'edges': [
                {'source': '1', 'target': '2', 'id': 'e1'},
                {'source': '2', 'target': '3', 'id': 'e2'},  # memory connected to agent
                {'source': '2', 'target': '4', 'id': 'e3'}
            ],
            'context': {}
        }
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check that agent execution was traced
        self.assertGreater(len(response.data['trace']), 0)
        # Agent trace should show memory was used
        agent_trace = response.data['trace'][1]
        self.assertIsNotNone(agent_trace.get('usedMemory'))

    def test_execute_workflow_trace_structure(self):
        """Test that workflow trace has correct structure."""
        payload = {
            'nodes': [
                {'id': '1', 'type': 'input', 'data': {'value': 'test'}},
                {'id': '2', 'type': 'output', 'data': {}}
            ],
            'edges': [
                {'source': '1', 'target': '2', 'id': 'e1'}
            ],
            'context': {}
        }
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        trace = response.data['trace']
        self.assertEqual(len(trace), 2)

        # Check trace entry structure
        entry = trace[0]
        self.assertIn('nodeId', entry)
        self.assertIn('type', entry)
        self.assertIn('result', entry)
        self.assertIn('edgeId', entry)
        self.assertIn('nextNodeId', entry)

    def test_execute_workflow_node_error_handling(self):
        """Test workflow handles node execution errors."""
        payload = {
            'nodes': [
                {'id': '1', 'type': 'invalid_type', 'data': {}},
                {'id': '2', 'type': 'output', 'data': {}}
            ],
            'edges': [
                {'source': '1', 'target': '2', 'id': 'e1'}
            ],
            'context': {}
        }
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['status'], 'error')
        self.assertIn('error', response.data)

    @patch('api.orchestration.workflow_executor.execute_node_by_type')
    def test_execute_workflow_uses_executor(self, mock_execute):
        """Test that execute_workflow uses WorkflowExecutor."""
        mock_execute.return_value = DriverResponse({'status': 'ok', 'output': 'test'})

        payload = {
            'nodes': [
                {'id': '1', 'type': 'input', 'data': {'value': 'test'}},
                {'id': '2', 'type': 'output', 'data': {}}
            ],
            'edges': [
                {'source': '1', 'target': '2', 'id': 'e1'}
            ],
            'context': {}
        }
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify execute_node_by_type was called
        self.assertTrue(mock_execute.called)

    def test_execute_workflow_complex_graph(self):
        """Test workflow with complex node graph."""
        payload = {
            'nodes': [
                {'id': '1', 'type': 'input', 'data': {'value': 'start'}},
                {'id': '2', 'type': 'router', 'data': {}},
                {'id': '3', 'type': 'tool', 'data': {'operation': 'uppercase'}},
                {'id': '4', 'type': 'tool', 'data': {'operation': 'lowercase'}},
                {'id': '5', 'type': 'output', 'data': {}}
            ],
            'edges': [
                {'source': '1', 'target': '2', 'id': 'e1'},
                {'source': '2', 'target': '3', 'id': 'e2', 'sourceHandle': 'yes'},
                {'source': '2', 'target': '4', 'id': 'e3', 'sourceHandle': 'no'},
                {'source': '3', 'target': '5', 'id': 'e4'},
                {'source': '4', 'target': '5', 'id': 'e5'}
            ],
            'context': {
                'condition': False
            }
        }
        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should go through lowercase path
        self.assertEqual(response.data['final'], 'start')


class WorkflowModelViewSetTestCase(TestCase):
    """Test suite for Workflow model CRUD operations."""

    def setUp(self):
        self.client = APIClient()
        self.list_url = '/api/workflows/'

    def test_list_workflows(self):
        """Test listing workflows."""
        # Create test workflows
        Workflow.objects.create(name='Workflow 1', nodes=[], edges=[])
        Workflow.objects.create(name='Workflow 2', nodes=[], edges=[])

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_create_workflow(self):
        """Test creating a workflow."""
        payload = {
            'name': 'Test Workflow',
            'description': 'Test description',
            'nodes': [{'id': '1', 'type': 'input'}],
            'edges': [{'id': 'e1', 'source': '1', 'target': '2'}]
        }
        response = self.client.post(self.list_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Test Workflow')
        self.assertEqual(Workflow.objects.count(), 1)

    def test_retrieve_workflow(self):
        """Test retrieving a specific workflow."""
        workflow = Workflow.objects.create(
            name='Test Workflow',
            nodes=[{'id': '1'}],
            edges=[]
        )
        url = f'/api/workflows/{workflow.id}/'

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Workflow')

    def test_update_workflow(self):
        """Test updating a workflow."""
        workflow = Workflow.objects.create(
            name='Original Name',
            nodes=[],
            edges=[]
        )
        url = f'/api/workflows/{workflow.id}/'
        payload = {
            'name': 'Updated Name',
            'nodes': [{'id': '1'}],
            'edges': []
        }

        response = self.client.put(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Name')
        workflow.refresh_from_db()
        self.assertEqual(workflow.name, 'Updated Name')

    def test_delete_workflow(self):
        """Test deleting a workflow."""
        workflow = Workflow.objects.create(name='To Delete', nodes=[], edges=[])
        url = f'/api/workflows/{workflow.id}/'

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Workflow.objects.count(), 0)


class NodeTypeViewSetTestCase(TestCase):
    """Test suite for NodeType read-only viewset."""

    def setUp(self):
        self.client = APIClient()
        self.list_url = '/api/node-types/'

    def test_list_node_types(self):
        """Test listing node types."""
        # Clear existing node types from migrations
        NodeType.objects.all().delete()

        NodeType.objects.create(
            name='test_input',
            display_name='Input',
            icon='📥',
            color='#00ff00'
        )
        NodeType.objects.create(
            name='test_output',
            display_name='Output',
            icon='📤',
            color='#ff0000'
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_retrieve_node_type(self):
        """Test retrieving a specific node type."""
        node_type = NodeType.objects.create(
            name='test',
            display_name='Test Node',
            icon='🔧',
            color='#0000ff'
        )
        url = f'/api/node-types/{node_type.id}/'

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'test')

    def test_create_node_type_not_allowed(self):
        """Test that creating node types via API is not allowed (read-only)."""
        payload = {
            'name': 'new_type',
            'display_name': 'New Type',
            'icon': '🆕',
            'color': '#ffffff'
        }
        response = self.client.post(self.list_url, payload, format='json')

        # Should be forbidden (405 Method Not Allowed for read-only viewset)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_node_type_not_allowed(self):
        """Test that deleting node types via API is not allowed (read-only)."""
        node_type = NodeType.objects.create(
            name='test',
            display_name='Test',
            icon='🔧',
            color='#000000'
        )
        url = f'/api/node-types/{node_type.id}/'

        response = self.client.delete(url)

        # Should be forbidden (405 Method Not Allowed for read-only viewset)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
