import logging
from typing import Any, Dict
from io import StringIO

from .base import BaseDriver, DriverResponse

logger = logging.getLogger(__name__)


class SSHCommandDriver(BaseDriver):
    type = "ssh_command"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        data = node.get("data") or {}
        node_id = node.get("id", "unknown")
        label = data.get("label", "SSH Command")

        # SSH connection parameters
        host = data.get("host", "")
        port = data.get("port", 22)
        username = data.get("username", "")
        password = data.get("password")
        key_filename = data.get("key_filename")

        # Command to execute
        command = data.get("command", "")
        timeout = data.get("timeout", 30)

        # Debug mode
        debug = data.get("debug", False)

        # Get input from context if command uses it
        stdin_value = context.get("input", "")

        # Initial logging
        logger.info(f"[SSH Command] Starting execution - Node: {label} ({node_id})")
        logger.info(f"[SSH Command] Target: {username}@{host}:{port}")
        logger.debug(f"[SSH Command] Command preview: {command[:200]}{'...' if len(command) > 200 else ''}")

        if debug:
            logger.info(f"[SSH Command] Debug mode enabled for node {node_id}")
            logger.debug(f"[SSH Command] Full command: {command}")
            if stdin_value:
                logger.debug(f"[SSH Command] Stdin provided: {len(str(stdin_value))} characters")

        if not host or not username:
            logger.error(f"[SSH Command] Node {node_id}: Missing required parameters (host or username)")
            return DriverResponse({
                "status": "error",
                "error": "SSH host and username are required",
            })

        if not command.strip():
            logger.error(f"[SSH Command] Node {node_id}: No command specified")
            return DriverResponse({
                "status": "error",
                "error": "Command is required",
            })

        try:
            timeout_val = int(timeout) if timeout is not None else 30
            logger.debug(f"[SSH Command] Timeout set to {timeout_val} seconds")
        except Exception as e:
            timeout_val = 30
            logger.warning(f"[SSH Command] Invalid timeout value, using default: 30 seconds ({e})")

        try:
            port_val = int(port) if port is not None else 22
            logger.debug(f"[SSH Command] Port set to {port_val}")
        except Exception as e:
            port_val = 22
            logger.warning(f"[SSH Command] Invalid port value, using default: 22 ({e})")

        # Import fabric here to avoid dependency if not used
        try:
            from fabric import Connection
            logger.debug(f"[SSH Command] Fabric library loaded successfully")
        except ImportError:
            logger.error(f"[SSH Command] Fabric library not installed")
            return DriverResponse({
                "status": "error",
                "error": "fabric library not installed. Install with: pip install fabric",
            })

        # Collect debug information
        debug_info = []
        auth_method = 'password' if password else 'key' if key_filename else 'agent/default'

        if debug:
            debug_info.append(f"Connecting to {username}@{host}:{port_val}")
            debug_info.append(f"Timeout: {timeout_val}s")
            debug_info.append(f"Auth method: {auth_method}")
            debug_info.append(f"Command: {command}")
            if stdin_value:
                debug_info.append(f"Stdin length: {len(str(stdin_value))} chars")

        logger.info(f"[SSH Command] Authentication method: {auth_method}")

        conn = None
        try:
            # Build connection config
            connect_kwargs = {
                "user": username,
                "port": port_val,
                "connect_timeout": timeout_val,
            }

            if password:
                connect_kwargs["connect_kwargs"] = {"password": password}
                logger.debug(f"[SSH Command] Using password authentication")

            if key_filename:
                connect_kwargs["connect_kwargs"] = connect_kwargs.get("connect_kwargs", {})
                connect_kwargs["connect_kwargs"]["key_filename"] = key_filename
                logger.debug(f"[SSH Command] Using SSH key: {key_filename}")

            if debug:
                debug_info.append(f"Connection config: {connect_kwargs}")

            logger.info(f"[SSH Command] Connecting to {username}@{host}:{port_val}...")
            conn = Connection(host, **connect_kwargs)
            logger.info(f"[SSH Command] Connection established successfully")

            # Execute command with timeout
            logger.info(f"[SSH Command] Executing command on remote host...")
            if debug:
                logger.debug(f"[SSH Command] Full command: {command}")

            # Use fabric's run with hide to capture output cleanly
            result = conn.run(
                command,
                hide=True,
                warn=True,
                timeout=timeout_val,
                in_stream=StringIO(str(stdin_value)) if stdin_value else None
            )

            stdout_text = result.stdout if result.stdout else ""
            stderr_text = result.stderr if result.stderr else ""
            exit_code = result.return_code

            logger.info(f"[SSH Command] Command execution completed")
            logger.info(f"[SSH Command] Exit code: {exit_code}")
            logger.debug(f"[SSH Command] Stdout length: {len(stdout_text)} characters")
            logger.debug(f"[SSH Command] Stderr length: {len(stderr_text)} characters")

            if debug:
                debug_info.append(f"Exit code: {exit_code}")
                debug_info.append(f"Stdout length: {len(stdout_text)} chars")
                debug_info.append(f"Stderr length: {len(stderr_text)} chars")

            if stderr_text:
                logger.warning(f"[SSH Command] Node {node_id} stderr output: {stderr_text[:200]}{'...' if len(stderr_text) > 200 else ''}")

            if stdout_text and debug:
                logger.debug(f"[SSH Command] Stdout preview: {stdout_text[:200]}{'...' if len(stdout_text) > 200 else ''}")

            # Prepare response with debug info if enabled
            response_data = {
                "output": stdout_text,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "exit_code": exit_code,
            }

            if debug:
                response_data["debug_info"] = "\n".join(debug_info)
                logger.debug(f"[SSH Command] Debug info compiled: {len(debug_info)} entries")

            if exit_code != 0:
                logger.warning(f"[SSH Command] Node {node_id} failed with exit code {exit_code}")
                response_data["status"] = "error"
                response_data["error"] = stderr_text or f"Command exited with code {exit_code}"
                logger.error(f"[SSH Command] Error response: {response_data['error'][:200]}{'...' if len(response_data.get('error', '')) > 200 else ''}")
                return DriverResponse(response_data)

            logger.info(f"[SSH Command] Node {node_id} completed successfully")
            response_data["status"] = "ok"
            return DriverResponse(response_data)

        except Exception as exc:
            error_msg = str(exc)
            error_type = type(exc).__name__
            logger.error(f"[SSH Command] Node {node_id} execution failed: {error_type}: {error_msg}")

            # Log stack trace for unexpected errors
            import traceback
            logger.debug(f"[SSH Command] Stack trace:\n{traceback.format_exc()}")

            if debug:
                debug_info.append(f"Error: {error_msg}")
                debug_info.append(f"Error type: {error_type}")

            response_data = {
                "status": "error",
                "error": error_msg,
            }

            if debug:
                response_data["debug_info"] = "\n".join(debug_info)
                logger.debug(f"[SSH Command] Debug info with error: {response_data['debug_info']}")

            return DriverResponse(response_data)
        finally:
            if conn:
                try:
                    logger.debug(f"[SSH Command] Closing SSH connection...")
                    conn.close()
                    logger.info(f"[SSH Command] Connection closed successfully for node {node_id}")
                except Exception as e:
                    logger.warning(f"[SSH Command] Error closing connection: {e}")
