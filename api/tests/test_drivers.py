from django.test import TestCase
from unittest.mock import patch, MagicMock, Mock
from api.drivers import (
    execute_node_by_type,
    InputDriver,
    OutputDriver,
    RouterDriver,
    MemoryDriver,
    ToolDriver,
    DRIVERS
)
from api.memory_store import store
import sys


class DriverRegistryTestCase(TestCase):
    """Test suite for driver registry and dispatcher."""

    def test_all_drivers_registered(self):
        """Test that all expected drivers are registered."""
        expected_types = ['input', 'output', 'router', 'memory', 'tool', 'openai_agent', 'claude_agent']
        for driver_type in expected_types:
            self.assertIn(driver_type, DRIVERS)

    def test_execute_node_by_type_with_valid_type(self):
        """Test executing a node with valid type."""
        node = {'id': '1', 'type': 'input', 'data': {}}
        context = {'input': 'test'}
        result = execute_node_by_type('input', node, context)

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['output'], 'test')

    def test_execute_node_by_type_with_invalid_type(self):
        """Test executing a node with invalid type returns error."""
        node = {'id': '1', 'type': 'invalid', 'data': {}}
        context = {'input': 'test'}
        result = execute_node_by_type('invalid', node, context)

        self.assertEqual(result['status'], 'error')
        self.assertIn('No driver registered', result['error'])

    def test_execute_node_by_type_handles_exceptions(self):
        """Test that execute_node_by_type handles driver exceptions."""
        with patch.object(InputDriver, 'execute', side_effect=Exception('Test error')):
            result = execute_node_by_type('input', {}, {})
            self.assertEqual(result['status'], 'error')
            self.assertEqual(result['error'], 'Test error')


class InputDriverTestCase(TestCase):
    """Test suite for InputDriver."""

    def setUp(self):
        self.driver = InputDriver()

    def test_driver_type(self):
        """Test driver type is correctly set."""
        self.assertEqual(self.driver.type, 'input')

    def test_execute_passes_through_input(self):
        """Test that input driver passes through input as output."""
        node = {'id': '1', 'data': {'value': 'node value'}}
        context = {'input': 'context input'}
        result = self.driver.execute(node, context)

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['output'], 'context input')

    def test_execute_with_none_input(self):
        """Test input driver with None input."""
        node = {'id': '1', 'data': {}}
        context = {'input': None}
        result = self.driver.execute(node, context)

        self.assertEqual(result['status'], 'ok')
        self.assertIsNone(result['output'])

    def test_execute_with_missing_input(self):
        """Test input driver with missing input in context."""
        node = {'id': '1', 'data': {}}
        context = {}
        result = self.driver.execute(node, context)

        self.assertEqual(result['status'], 'ok')
        self.assertIsNone(result['output'])


class OutputDriverTestCase(TestCase):
    """Test suite for OutputDriver."""

    def setUp(self):
        self.driver = OutputDriver()

    def test_driver_type(self):
        """Test driver type is correctly set."""
        self.assertEqual(self.driver.type, 'output')

    def test_execute_returns_final_value(self):
        """Test that output driver returns input as final value."""
        node = {'id': '1', 'data': {}}
        context = {'input': 'final output'}
        result = self.driver.execute(node, context)

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['final'], 'final output')

    def test_execute_with_complex_input(self):
        """Test output driver with complex input data."""
        node = {'id': '1', 'data': {}}
        context = {'input': {'key': 'value', 'nested': {'data': 123}}}
        result = self.driver.execute(node, context)

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['final'], {'key': 'value', 'nested': {'data': 123}})


class RouterDriverTestCase(TestCase):
    """Test suite for RouterDriver."""

    def setUp(self):
        self.driver = RouterDriver()

    def test_driver_type(self):
        """Test driver type is correctly set."""
        self.assertEqual(self.driver.type, 'router')

    def test_execute_returns_yes_when_condition_true(self):
        """Test router returns 'yes' route when condition is True."""
        node = {'id': '1', 'data': {}}
        context = {'condition': True}
        result = self.driver.execute(node, context)

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['route'], 'yes')

    def test_execute_returns_no_when_condition_false(self):
        """Test router returns 'no' route when condition is False."""
        node = {'id': '1', 'data': {}}
        context = {'condition': False}
        result = self.driver.execute(node, context)

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['route'], 'no')

    def test_execute_defaults_to_no_when_condition_missing(self):
        """Test router defaults to 'no' route when condition is missing."""
        node = {'id': '1', 'data': {}}
        context = {}
        result = self.driver.execute(node, context)

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['route'], 'no')

    def test_execute_with_truthy_values(self):
        """Test router with various truthy values."""
        for truthy in [1, 'yes', [1], {'a': 1}]:
            context = {'condition': truthy}
            result = self.driver.execute({}, context)
            self.assertEqual(result['route'], 'yes')

    def test_execute_with_falsy_values(self):
        """Test router with various falsy values."""
        for falsy in [0, '', [], {}, None]:
            context = {'condition': falsy}
            result = self.driver.execute({}, context)
            self.assertEqual(result['route'], 'no')


class MemoryDriverTestCase(TestCase):
    """Test suite for MemoryDriver."""

    def setUp(self):
        self.driver = MemoryDriver()
        store.clear()

    def tearDown(self):
        store.clear()

    def test_driver_type(self):
        """Test driver type is correctly set."""
        self.assertEqual(self.driver.type, 'memory')

    def test_execute_stores_value_in_memory(self):
        """Test that memory driver stores value in memory store."""
        node = {'id': '1', 'data': {'key': 'test_key', 'namespace': 'default'}}
        context = {'input': 'test value'}
        result = self.driver.execute(node, context)

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['stored'], 'test value')
        self.assertEqual(store.get('default:test_key'), 'test value')

    def test_execute_stores_value_in_state(self):
        """Test that memory driver stores value in context state."""
        node = {'id': '1', 'data': {'key': 'my_key'}}
        context = {'input': 'my value', 'state': {}}
        result = self.driver.execute(node, context)

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['state']['my_key'], 'my value')

    def test_execute_returns_previous_value(self):
        """Test that memory driver returns previous value."""
        node = {'id': '1', 'data': {'key': 'test_key', 'namespace': 'default'}}

        # First store
        context1 = {'input': 'first value'}
        result1 = self.driver.execute(node, context1)
        self.assertIsNone(result1['previous'])

        # Second store
        context2 = {'input': 'second value'}
        result2 = self.driver.execute(node, context2)
        self.assertEqual(result2['previous'], 'first value')

    def test_execute_passes_through_value(self):
        """Test that memory driver passes through value as output."""
        node = {'id': '1', 'data': {'key': 'test_key'}}
        context = {'input': 'passthrough'}
        result = self.driver.execute(node, context)

        self.assertEqual(result['output'], 'passthrough')

    def test_execute_defaults_key_to_memory(self):
        """Test that memory driver defaults key to 'memory' if not provided."""
        node = {'id': '1', 'data': {}}
        context = {'input': 'test'}
        result = self.driver.execute(node, context)

        self.assertEqual(store.get('default:memory'), 'test')

    def test_execute_defaults_namespace_to_default(self):
        """Test that memory driver defaults namespace to 'default'."""
        node = {'id': '1', 'data': {'key': 'test_key'}}
        context = {'input': 'test'}
        result = self.driver.execute(node, context)

        self.assertEqual(store.get('default:test_key'), 'test')

    def test_execute_with_custom_namespace(self):
        """Test memory driver with custom namespace."""
        node = {'id': '1', 'data': {'key': 'test_key', 'namespace': 'custom'}}
        context = {'input': 'namespaced value'}
        result = self.driver.execute(node, context)

        self.assertEqual(store.get('custom:test_key'), 'namespaced value')
        self.assertIsNone(store.get('default:test_key'))

    def test_execute_uses_explicit_value_over_input(self):
        """Test that explicit value in context takes precedence."""
        node = {'id': '1', 'data': {'key': 'test_key'}}
        context = {'input': 'input value', 'value': 'explicit value'}
        result = self.driver.execute(node, context)

        self.assertEqual(result['stored'], 'explicit value')

    def test_execute_merges_with_existing_state(self):
        """Test that memory driver merges with existing state."""
        node = {'id': '1', 'data': {'key': 'new_key'}}
        context = {'input': 'new value', 'state': {'existing_key': 'existing value'}}
        result = self.driver.execute(node, context)

        self.assertEqual(result['state']['new_key'], 'new value')
        self.assertEqual(result['state']['existing_key'], 'existing value')


class ToolDriverTestCase(TestCase):
    """Test suite for ToolDriver."""

    def setUp(self):
        self.driver = ToolDriver()

    def test_driver_type(self):
        """Test driver type is correctly set."""
        self.assertEqual(self.driver.type, 'tool')

    def test_execute_uppercase_operation(self):
        """Test tool driver with uppercase operation."""
        node = {'id': '1', 'data': {'operation': 'uppercase', 'label': 'Upper'}}
        context = {'input': 'hello world'}
        result = self.driver.execute(node, context)

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['output'], 'HELLO WORLD')
        self.assertEqual(result['tool'], 'Upper')

    def test_execute_lowercase_operation(self):
        """Test tool driver with lowercase operation."""
        node = {'id': '1', 'data': {'operation': 'lowercase', 'label': 'Lower'}}
        context = {'input': 'HELLO WORLD'}
        result = self.driver.execute(node, context)

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['output'], 'hello world')

    def test_execute_append_operation(self):
        """Test tool driver with append operation."""
        node = {'id': '1', 'data': {'operation': 'append', 'arg': ' appended', 'label': 'Append'}}
        context = {'input': 'original'}
        result = self.driver.execute(node, context)

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['output'], 'original appended')

    def test_execute_echo_operation_default(self):
        """Test tool driver defaults to echo operation."""
        node = {'id': '1', 'data': {'label': 'Echo'}}
        context = {'input': 'test', 'params': {'key': 'value'}}
        result = self.driver.execute(node, context)

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['output'], {'echo': {'key': 'value'}})

    def test_execute_with_non_string_input_for_uppercase(self):
        """Test uppercase with non-string input defaults to echo."""
        node = {'id': '1', 'data': {'operation': 'uppercase'}}
        context = {'input': 123, 'params': {}}
        result = self.driver.execute(node, context)

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['output'], {'echo': {}})

    def test_execute_defaults_label_to_tool(self):
        """Test that tool label defaults properly."""
        node = {'id': '1', 'data': {'operation': 'uppercase'}}
        context = {'input': 'test'}
        result = self.driver.execute(node, context)

        self.assertEqual(result['tool'], 'Tool')

    @patch.dict('os.environ', {}, clear=True)
    def test_google_search_missing_credentials(self):
        """Test google search without credentials returns error."""
        node = {'id': '1', 'data': {'operation': 'google_search'}}
        context = {'input': 'test query'}
        result = self.driver.execute(node, context)

        self.assertEqual(result['status'], 'error')
        self.assertIn('not configured', result['error'])

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key', 'GOOGLE_CSE_ID': 'test_cse'})
    def test_google_search_with_credentials(self):
        """Test google search with valid credentials."""
        # Mock the requests module
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            'items': [
                {
                    'title': 'Test Result',
                    'link': 'https://example.com',
                    'snippet': 'Test snippet',
                    'displayLink': 'example.com'
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_requests.get.return_value = mock_response

        with patch.dict(sys.modules, {'requests': mock_requests}):
            node = {'id': '1', 'data': {'operation': 'google_search', 'label': 'Search'}}
            context = {'input': 'test query'}
            result = self.driver.execute(node, context)

            self.assertEqual(result['status'], 'ok')
            self.assertEqual(result['output']['query'], 'test query')
            self.assertEqual(len(result['output']['results']), 1)
            self.assertEqual(result['output']['results'][0]['title'], 'Test Result')

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key', 'GOOGLE_CSE_ID': 'test_cse'})
    def test_google_search_with_params_override(self):
        """Test google search with query override from params."""
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {'items': []}
        mock_response.raise_for_status = Mock()
        mock_requests.get.return_value = mock_response

        with patch.dict(sys.modules, {'requests': mock_requests}):
            node = {'id': '1', 'data': {'operation': 'google_search', 'arg': 'extra terms'}}
            context = {'input': 'base query', 'params': {'q': 'override query', 'num': 3}}
            result = self.driver.execute(node, context)

            # Should use override query from params
            call_args = mock_requests.get.call_args
            self.assertEqual(call_args[1]['params']['q'], 'override query')
            self.assertEqual(call_args[1]['params']['num'], 3)

    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key', 'GOOGLE_CSE_ID': 'test_cse'})
    @patch('urllib.request.urlopen')
    def test_google_search_fallback_to_urllib(self, mock_urlopen):
        """Test google search falls back to urllib on requests failure."""
        mock_requests = Mock()
        mock_requests.get.side_effect = Exception('Network error')

        mock_response = Mock()
        mock_response.read.return_value = b'{"items": []}'
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_response

        with patch.dict(sys.modules, {'requests': mock_requests}):
            node = {'id': '1', 'data': {'operation': 'google_search'}}
            context = {'input': 'test'}
            result = self.driver.execute(node, context)

            self.assertEqual(result['status'], 'ok')
            mock_urlopen.assert_called_once()

    def test_execute_handles_exceptions(self):
        """Test that tool driver handles unexpected exceptions."""
        node = {'id': '1', 'data': {'operation': 'append', 'arg': ' test'}}
        # Non-string input won't match append operation, should fall back to echo
        context = {'input': None, 'params': {}}
        result = self.driver.execute(node, context)

        # Should fall back to echo operation instead of erroring
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['output'], {'echo': {}})
