from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)
import socket
import json
from .base import BaseDriver, DriverResponse


class TCPOutputDriver(BaseDriver):
    type = "tcp_output"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        node_id = node.get("id", "unknown")
        data = node.get("data") or {}
        label = data.get("label", "TCP Output")

        logger.info(f"[TCP Output] Node: {label} ({node_id})")

        # Configuration
        host = data.get("host", "localhost")
        port = data.get("port", 9000)

        logger.debug(f"[TCP Output] Target: {host}:{port}")
        timeout = data.get("timeout", 10)
        format_type = data.get("format", "raw")  # raw, json, newline
        wait_response = data.get("wait_response", False)
        encoding = data.get("encoding", "utf-8")

        # Get input data
        input_val = context.get("input")

        # Validate configuration
        if not host:
            return DriverResponse({
                "status": "error",
                "error": "TCP host is required",
            })

        try:
            port = int(port)
            if port < 1 or port > 65535:
                raise ValueError("Port must be between 1 and 65535")
        except (ValueError, TypeError) as e:
            return DriverResponse({
                "status": "error",
                "error": f"Invalid port number: {e}",
            })

        try:
            timeout = float(timeout)
        except (ValueError, TypeError):
            timeout = 10.0

        # Format the data to send
        try:
            if format_type == "json":
                # Convert input to JSON
                if isinstance(input_val, str):
                    try:
                        # If it's already JSON, parse and re-serialize
                        parsed = json.loads(input_val)
                        payload = json.dumps(parsed)
                    except json.JSONDecodeError:
                        # Wrap string in JSON
                        payload = json.dumps({"data": input_val})
                else:
                    payload = json.dumps(input_val)
            elif format_type == "newline":
                # Add newline delimiter
                payload = str(input_val) + "\n"
            else:
                # Raw format - send as-is
                payload = str(input_val)

            # Encode to bytes
            data_bytes = payload.encode(encoding)

        except Exception as e:
            return DriverResponse({
                "status": "error",
                "error": f"Failed to format data: {e}",
            })

        # Connect and send
        sock = None
        try:
            # Create TCP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)

            # Connect to server
            sock.connect((host, port))

            # Send data
            sock.sendall(data_bytes)

            response = None
            if wait_response:
                # Wait for response (up to 4KB)
                response_bytes = sock.recv(4096)
                response = response_bytes.decode(encoding, errors='ignore')

            logger.info(f"[TCP Output] Successfully sent {len(data_bytes)} bytes to {host}:{port}")
            if response:
                logger.debug(f"[TCP Output] Received response: {response[:100]}...")

            return DriverResponse({
                "status": "ok",
                "output": {
                    "sent": payload,
                    "bytes_sent": len(data_bytes),
                    "host": host,
                    "port": port,
                    "response": response,
                },
            })

        except socket.timeout:
            logger.error(f"[TCP Output] Connection timeout: {host}:{port}")
            return DriverResponse({
                "status": "error",
                "error": f"Connection to {host}:{port} timed out after {timeout}s",
            })
        except socket.gaierror as e:
            logger.error(f"[TCP Output] DNS resolution failed: {host}")
            return DriverResponse({
                "status": "error",
                "error": f"Failed to resolve host {host}: {e}",
            })
        except ConnectionRefusedError:
            logger.error(f"[TCP Output] Connection refused: {host}:{port}")
            return DriverResponse({
                "status": "error",
                "error": f"Connection refused by {host}:{port}",
            })
        except Exception as e:
            logger.error(f"[TCP Output] Error: {str(e)}")
            return DriverResponse({
                "status": "error",
                "error": f"TCP error: {e}",
            })
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass
