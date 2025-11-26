from typing import Any, Dict, List, Optional
import os
import json
import subprocess
import time
from .base import BaseDriver, DriverResponse


class MCPToolDriver(BaseDriver):
    """Driver for executing tools from MCP (Model Context Protocol) servers.

    Supports both stdio-based MCP servers (launched via command) and HTTP/SSE servers.
    """
    type = "mcp_tool"

    def _parse_mcp_error(self, exc: Exception, context: str = "") -> str:
        """Parse MCP-specific errors and return helpful messages."""
        error_str = str(exc)

        if "connection refused" in error_str.lower():
            return f"MCP Server: Connection refused. {context}"
        elif "timeout" in error_str.lower():
            return f"MCP Server: Request timeout. The server may be slow or unresponsive."
        elif "command not found" in error_str.lower() or "no such file" in error_str.lower():
            return f"MCP Server: Command not found. Check that the server is installed and in PATH."
        elif "permission denied" in error_str.lower():
            return f"MCP Server: Permission denied. Check file/directory permissions."
        else:
            return f"MCP Server error: {error_str}"

    def _execute_stdio_server(
        self,
        command: str,
        args: List[str],
        tool_name: str,
        tool_params: Dict[str, Any],
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Execute a tool on a stdio-based MCP server.

        This launches the server as a subprocess and communicates via JSON-RPC 2.0.
        """
        try:
            # Build the command
            cmd = [command] + args

            # Start the MCP server process
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            try:
                # MCP handshake: initialize
                initialize_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "vibeengine",
                            "version": "1.0.0"
                        }
                    }
                }

                process.stdin.write(json.dumps(initialize_request) + "\n")
                process.stdin.flush()

                # Read initialization response
                init_response = process.stdout.readline()
                if not init_response:
                    raise Exception("No response from MCP server during initialization")

                init_data = json.loads(init_response)
                if "error" in init_data:
                    raise Exception(f"Initialization failed: {init_data['error']}")

                # Send initialized notification
                initialized_notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                }
                process.stdin.write(json.dumps(initialized_notification) + "\n")
                process.stdin.flush()

                # List available tools
                list_tools_request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {}
                }

                process.stdin.write(json.dumps(list_tools_request) + "\n")
                process.stdin.flush()

                tools_response = process.stdout.readline()
                if not tools_response:
                    raise Exception("No response when listing tools")

                tools_data = json.loads(tools_response)
                if "error" in tools_data:
                    raise Exception(f"Failed to list tools: {tools_data['error']}")

                available_tools = tools_data.get("result", {}).get("tools", [])
                tool_names = [t.get("name") for t in available_tools]

                if tool_name not in tool_names:
                    raise Exception(
                        f"Tool '{tool_name}' not found. Available tools: {', '.join(tool_names)}"
                    )

                # Execute the tool
                call_tool_request = {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": tool_params
                    }
                }

                process.stdin.write(json.dumps(call_tool_request) + "\n")
                process.stdin.flush()

                # Read tool execution response
                start_time = time.time()
                result_response = None

                while time.time() - start_time < timeout:
                    line = process.stdout.readline()
                    if not line:
                        break

                    try:
                        data = json.loads(line)
                        # Look for response with id=3 (our tool call)
                        if data.get("id") == 3:
                            result_response = data
                            break
                    except json.JSONDecodeError:
                        continue

                if not result_response:
                    raise Exception(f"Tool execution timeout ({timeout}s)")

                if "error" in result_response:
                    error = result_response["error"]
                    raise Exception(f"Tool execution failed: {error.get('message', error)}")

                return result_response.get("result", {})

            finally:
                # Clean up the process
                try:
                    process.stdin.close()
                    process.terminate()
                    process.wait(timeout=2)
                except:
                    process.kill()

        except subprocess.SubprocessError as e:
            raise Exception(self._parse_mcp_error(e, "Failed to start MCP server"))
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response from MCP server: {e}")
        except Exception as e:
            if "MCP Server" in str(e):
                raise
            raise Exception(self._parse_mcp_error(e))

    def _execute_http_server(
        self,
        server_url: str,
        tool_name: str,
        tool_params: Dict[str, Any],
        api_key: Optional[str] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Execute a tool on an HTTP/SSE-based MCP server."""
        try:
            import requests

            headers = {
                "Content-Type": "application/json"
            }

            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            # Initialize connection
            init_response = requests.post(
                f"{server_url}/mcp/v1/initialize",
                json={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "vibeengine",
                        "version": "1.0.0"
                    }
                },
                headers=headers,
                timeout=timeout
            )
            init_response.raise_for_status()

            # List tools
            tools_response = requests.post(
                f"{server_url}/mcp/v1/tools/list",
                json={},
                headers=headers,
                timeout=timeout
            )
            tools_response.raise_for_status()
            tools_data = tools_response.json()

            available_tools = tools_data.get("tools", [])
            tool_names = [t.get("name") for t in available_tools]

            if tool_name not in tool_names:
                raise Exception(
                    f"Tool '{tool_name}' not found. Available tools: {', '.join(tool_names)}"
                )

            # Call tool
            call_response = requests.post(
                f"{server_url}/mcp/v1/tools/call",
                json={
                    "name": tool_name,
                    "arguments": tool_params
                },
                headers=headers,
                timeout=timeout
            )
            call_response.raise_for_status()

            return call_response.json()

        except Exception as e:
            if "requests" in str(type(e).__module__):
                import requests
                if isinstance(e, requests.exceptions.HTTPError):
                    status = e.response.status_code
                    if status == 401:
                        raise Exception("MCP Server: Authentication failed (401). Check your API key.")
                    elif status == 404:
                        raise Exception("MCP Server: Endpoint not found (404). Check the server URL.")
                    elif status >= 500:
                        raise Exception(f"MCP Server: Server error ({status}).")
                elif isinstance(e, requests.exceptions.ConnectionError):
                    raise Exception(f"MCP Server: Connection failed to {server_url}. Is the server running?")
                elif isinstance(e, requests.exceptions.Timeout):
                    raise Exception(f"MCP Server: Request timeout ({timeout}s).")

            raise Exception(self._parse_mcp_error(e))

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        """Execute an MCP tool.

        Node data should contain:
        - server_type: 'stdio' or 'http'
        - For stdio:
            - command: Command to launch the server (e.g., 'npx')
            - args: Arguments for the command
        - For HTTP:
            - server_url: Base URL of the MCP server
            - api_key: Optional API key
        - tool_name: Name of the tool to execute
        - tool_params: Parameters to pass to the tool (or use context.input)
        """
        data = node.get("data", {})
        input_val = context.get("input")

        server_type = data.get("server_type", "stdio")
        tool_name = data.get("tool_name", "")
        timeout = int(data.get("timeout", 30))

        if not tool_name:
            return DriverResponse({
                "status": "error",
                "error": "No tool_name specified in node configuration"
            })

        # Build tool parameters
        # Priority: explicit tool_params > tool_params_json > context.params > context.input
        tool_params = data.get("tool_params", {})

        # Try to parse JSON params from UI
        if not tool_params:
            tool_params_json = data.get("tool_params_json", "")
            if tool_params_json and isinstance(tool_params_json, str):
                try:
                    tool_params = json.loads(tool_params_json)
                except json.JSONDecodeError:
                    pass  # Ignore invalid JSON, will use context params

        if not tool_params and context.get("params"):
            tool_params = context.get("params")
        elif not tool_params and input_val:
            # Try to use input as a parameter
            # Common pattern: if input is a string, use it as 'input' param
            if isinstance(input_val, str):
                tool_params = {"input": input_val}
            elif isinstance(input_val, dict):
                tool_params = input_val
            else:
                tool_params = {"value": input_val}

        try:
            if server_type == "stdio":
                command = data.get("command", "")
                args = data.get("args", [])

                if not command:
                    return DriverResponse({
                        "status": "error",
                        "error": "No command specified for stdio MCP server"
                    })

                if isinstance(args, str):
                    args = args.split()

                result = self._execute_stdio_server(
                    command=command,
                    args=args,
                    tool_name=tool_name,
                    tool_params=tool_params,
                    timeout=timeout
                )

            elif server_type == "http":
                server_url = data.get("server_url", "")
                api_key = data.get("api_key") or os.getenv("MCP_API_KEY")

                if not server_url:
                    return DriverResponse({
                        "status": "error",
                        "error": "No server_url specified for HTTP MCP server"
                    })

                result = self._execute_http_server(
                    server_url=server_url,
                    tool_name=tool_name,
                    tool_params=tool_params,
                    api_key=api_key,
                    timeout=timeout
                )
            else:
                return DriverResponse({
                    "status": "error",
                    "error": f"Unknown server_type: {server_type}. Use 'stdio' or 'http'"
                })

            # Extract content from MCP response
            # MCP tools return {content: [{type: "text", text: "..."}, ...]}
            content_items = result.get("content", [])

            # Combine all text content
            output_text = ""
            output_data = []

            for item in content_items:
                if item.get("type") == "text":
                    output_text += item.get("text", "")
                else:
                    output_data.append(item)

            # Return the most useful format
            if output_text and not output_data:
                output = output_text
            elif output_data and not output_text:
                output = output_data
            else:
                output = {
                    "text": output_text,
                    "data": output_data
                }

            return DriverResponse({
                "status": "ok",
                "output": output,
                "tool": tool_name,
                "mcp_result": result  # Include full MCP response for debugging
            })

        except Exception as exc:
            # Check if node configured to continue on error
            continue_on_error = data.get('continue_on_error', False)
            error_msg = str(exc)

            if continue_on_error:
                return DriverResponse({
                    "status": "ok",
                    "output": input_val,
                    "error": error_msg,
                    "error_type": "mcp_error",
                    "had_error": True,
                })
            else:
                return DriverResponse({
                    "status": "error",
                    "error": error_msg,
                    "output": input_val,
                    "error_type": "mcp_error",
                })
