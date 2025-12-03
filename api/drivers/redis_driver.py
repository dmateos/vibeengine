"""
Redis driver for read/write operations.
"""

import os
import json
from typing import Dict, Any
from .base import BaseDriver, DriverResponse


class RedisDriver(BaseDriver):
    type = "redis"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        """Execute Redis operations."""
        try:
            import redis
        except ImportError:
            return DriverResponse({
                "status": "error",
                "error": "redis package not installed. Run: pip install redis"
            })

        # Get configuration
        host = node.get("data", {}).get("host", "localhost")
        port = int(node.get("data", {}).get("port", 6379))
        password = node.get("data", {}).get("password") or os.getenv("REDIS_PASSWORD")
        db = int(node.get("data", {}).get("db", 0))
        operation = node.get("data", {}).get("operation", "get")
        key = node.get("data", {}).get("key", "")
        value = node.get("data", {}).get("value", "")
        field = node.get("data", {}).get("field", "")  # For hash operations
        ttl = node.get("data", {}).get("ttl")  # Time to live in seconds

        # Support {input} placeholder in key and value
        input_data = context.get("input", "")
        if isinstance(input_data, (dict, list)):
            input_str = json.dumps(input_data)
        else:
            input_str = str(input_data)

        key = key.replace("{input}", input_str) if key else input_str
        value = value.replace("{input}", input_str) if value else input_str

        try:
            # Connect to Redis
            r = redis.Redis(
                host=host,
                port=port,
                password=password,
                db=db,
                decode_responses=True
            )

            # Test connection
            r.ping()

            result = None

            # Execute operation
            if operation == "get":
                result = r.get(key)
                if result is None:
                    result = f"Key '{key}' not found"

            elif operation == "set":
                if ttl:
                    r.setex(key, int(ttl), value)
                else:
                    r.set(key, value)
                result = f"Set {key} = {value}"

            elif operation == "delete":
                deleted = r.delete(key)
                result = f"Deleted {deleted} key(s)"

            elif operation == "incr":
                result = r.incr(key)

            elif operation == "decr":
                result = r.decr(key)

            elif operation == "lpush":
                r.lpush(key, value)
                result = f"Pushed to left of list {key}"

            elif operation == "rpush":
                r.rpush(key, value)
                result = f"Pushed to right of list {key}"

            elif operation == "lpop":
                result = r.lpop(key)
                if result is None:
                    result = f"List '{key}' is empty or doesn't exist"

            elif operation == "rpop":
                result = r.rpop(key)
                if result is None:
                    result = f"List '{key}' is empty or doesn't exist"

            elif operation == "lrange":
                # Get all items from list
                result = r.lrange(key, 0, -1)

            elif operation == "hset":
                if not field:
                    return DriverResponse({
                        "status": "error",
                        "error": "Field is required for HSET operation"
                    })
                r.hset(key, field, value)
                result = f"Set {key}.{field} = {value}"

            elif operation == "hget":
                if not field:
                    return DriverResponse({
                        "status": "error",
                        "error": "Field is required for HGET operation"
                    })
                result = r.hget(key, field)
                if result is None:
                    result = f"Field '{field}' not found in hash '{key}'"

            elif operation == "hgetall":
                result = r.hgetall(key)

            elif operation == "keys":
                # Get all keys matching pattern (key is used as pattern)
                pattern = key if key else "*"
                result = r.keys(pattern)

            elif operation == "exists":
                result = r.exists(key) > 0

            elif operation == "ttl":
                ttl_val = r.ttl(key)
                if ttl_val == -2:
                    result = f"Key '{key}' does not exist"
                elif ttl_val == -1:
                    result = f"Key '{key}' has no expiration"
                else:
                    result = f"TTL: {ttl_val} seconds"

            else:
                return DriverResponse({
                    "status": "error",
                    "error": f"Unknown operation: {operation}"
                })

            return DriverResponse({
                "status": "ok",
                "output": result,
                "operation": operation,
                "key": key
            })

        except redis.ConnectionError as e:
            return DriverResponse({
                "status": "error",
                "error": f"Redis connection error: {str(e)}"
            })
        except Exception as e:
            return DriverResponse({
                "status": "error",
                "error": f"Redis error: {str(e)}"
            })
