import os
from typing import Any, Optional


class _InProcessStore:
    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def get(self, key: str) -> Any:
        return self._data.get(key)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value


class MemoryStore:
    """Simple key-value memory store with optional Redis backend.

    If REDIS_URL/REDIS_HOST is configured and redis-py is importable, uses Redis.
    Otherwise falls back to an in-process dictionary.
    """

    def __init__(self) -> None:
        self._backend = None
        self._init_backend()

    def _init_backend(self) -> None:
        url = os.getenv('REDIS_URL')
        host = os.getenv('REDIS_HOST')
        port = int(os.getenv('REDIS_PORT', '6379'))
        if url or host:
            try:
                import redis  # type: ignore

                if url:
                    self._backend = redis.Redis.from_url(url)
                else:
                    self._backend = redis.Redis(host=host, port=port)
                # test connection
                self._backend.ping()
                return
            except Exception:
                # fall back to in-process store
                pass
        self._backend = _InProcessStore()

    def get(self, key: str) -> Any:
        if hasattr(self._backend, 'get') and not isinstance(self._backend, _InProcessStore):
            # redis returns bytes by default
            val = self._backend.get(key)
            try:
                import json
                if isinstance(val, (bytes, bytearray)):
                    val = val.decode('utf-8')
                return json.loads(val) if isinstance(val, str) else val
            except Exception:
                return val
        return self._backend.get(key)

    def set(self, key: str, value: Any) -> None:
        if hasattr(self._backend, 'set') and not isinstance(self._backend, _InProcessStore):
            try:
                import json
                payload = json.dumps(value)
                self._backend.set(key, payload)
                return
            except Exception:
                # best effort
                self._backend.set(key, str(value))
                return
        self._backend.set(key, value)

    def clear(self) -> None:
        """Clear all stored data."""
        if isinstance(self._backend, _InProcessStore):
            self._backend._data.clear()
        elif hasattr(self._backend, 'flushdb'):
            # Redis backend
            self._backend.flushdb()


store = MemoryStore()

