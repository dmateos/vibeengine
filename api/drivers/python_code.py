import logging
import subprocess
from typing import Any, Dict

from .base import BaseDriver, DriverResponse

logger = logging.getLogger(__name__)


class PythonCodeDriver(BaseDriver):
    type = "python_code"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        data = node.get("data") or {}
        code = data.get("code") or ""
        timeout = data.get("timeout", 10)
        stdin_value = context.get("input", "")
        node_id = node.get("id", "unknown")
        label = data.get("label", "Python Code")

        logger.info(f"[Python Code] Node: {label} ({node_id}) - Timeout: {timeout}s")
        logger.debug(f"[Python Code] Code preview: {str(code)[:200]}...")
        logger.debug(f"[Python Code] Stdin preview: {str(stdin_value)[:200]}...")

        if not str(code).strip():
            return DriverResponse({
                "status": "error",
                "error": "Python code is required",
            })

        try:
            timeout_val = float(timeout) if timeout is not None else 10.0
        except Exception:
            timeout_val = 10.0

        try:
            result = subprocess.run(
                ["python", "-c", code],
                input="" if stdin_value is None else str(stdin_value),
                capture_output=True,
                text=True,
                timeout=timeout_val,
            )
        except subprocess.TimeoutExpired:
            return DriverResponse({
                "status": "error",
                "error": f"Python code timed out after {timeout_val} seconds",
                "stdout": "",
                "stderr": "",
            })
        except FileNotFoundError:
            return DriverResponse({
                "status": "error",
                "error": "Python interpreter not found on worker",
            })
        except Exception as exc:
            logger.error("[Python Code] Execution failed: %s", exc)
            return DriverResponse({
                "status": "error",
                "error": str(exc),
            })

        stdout = result.stdout or ""
        stderr = result.stderr or ""

        if result.returncode != 0:
            return DriverResponse({
                "status": "error",
                "error": stderr or f"Process exited with code {result.returncode}",
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": result.returncode,
            })

        logger.info(f"[Python Code] Node {node_id} completed with exit code {result.returncode}")
        if stderr:
            logger.warning(f"[Python Code] Node {node_id} stderr: {stderr[:200]}...")

        return DriverResponse({
            "status": "ok",
            "output": stdout,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": result.returncode,
        })
