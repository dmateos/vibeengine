"""
SQL driver for MySQL and PostgreSQL read/write operations.
"""

import os
import json
from typing import Dict, Any, List
from .base import BaseDriver, DriverResponse


class SQLDriver(BaseDriver):
    type = "sql"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        """Execute SQL queries on MySQL or PostgreSQL."""
        # Get configuration
        db_type = node.get("data", {}).get("db_type", "postgresql")  # postgresql or mysql
        host = node.get("data", {}).get("host", "localhost")
        port = node.get("data", {}).get("port")
        user = node.get("data", {}).get("user", "")
        password = node.get("data", {}).get("password", "") or os.getenv(f"{db_type.upper()}_PASSWORD", "")
        database = node.get("data", {}).get("database", "")
        query = node.get("data", {}).get("query", "")
        params_str = node.get("data", {}).get("params", "")  # JSON array of parameters

        # Default ports
        if not port:
            port = 5432 if db_type == "postgresql" else 3306
        else:
            port = int(port)

        # Support {input} placeholder in query
        input_data = context.get("input", "")
        if isinstance(input_data, (dict, list)):
            input_str = json.dumps(input_data)
        else:
            input_str = str(input_data)

        query = query.replace("{input}", input_str) if query else ""

        if not query:
            return DriverResponse({
                "status": "error",
                "error": "Query is required"
            })

        # Parse parameters
        params = []
        if params_str:
            try:
                params = json.loads(params_str)
                if not isinstance(params, list):
                    params = [params]
            except json.JSONDecodeError:
                return DriverResponse({
                    "status": "error",
                    "error": "Parameters must be valid JSON array"
                })

        try:
            conn = None
            cursor = None

            if db_type == "postgresql":
                try:
                    import psycopg2
                    import psycopg2.extras
                except ImportError:
                    return DriverResponse({
                        "status": "error",
                        "error": "psycopg2 package not installed. Run: pip install psycopg2-binary"
                    })

                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=database
                )
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            elif db_type == "mysql":
                try:
                    import mysql.connector
                except ImportError:
                    return DriverResponse({
                        "status": "error",
                        "error": "mysql-connector-python package not installed. Run: pip install mysql-connector-python"
                    })

                conn = mysql.connector.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=database
                )
                cursor = conn.cursor(dictionary=True)

            else:
                return DriverResponse({
                    "status": "error",
                    "error": f"Unsupported database type: {db_type}"
                })

            # Execute query
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Determine if this is a SELECT query or a write operation
            query_type = query.strip().upper().split()[0]

            if query_type == "SELECT":
                # Fetch results
                results = cursor.fetchall()

                # Convert to list of dicts
                if db_type == "postgresql":
                    output = [dict(row) for row in results]
                else:  # mysql
                    output = results

                return DriverResponse({
                    "status": "ok",
                    "output": output,
                    "row_count": len(output),
                    "query": query
                })
            else:
                # INSERT, UPDATE, DELETE, etc.
                conn.commit()
                affected_rows = cursor.rowcount

                return DriverResponse({
                    "status": "ok",
                    "output": f"{query_type} successful: {affected_rows} row(s) affected",
                    "affected_rows": affected_rows,
                    "query": query
                })

        except Exception as e:
            if conn:
                conn.rollback()
            return DriverResponse({
                "status": "error",
                "error": f"SQL error: {str(e)}",
                "query": query
            })
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
