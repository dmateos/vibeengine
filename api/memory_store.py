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
    """Simple key-value memory store with DB priority.

    Priority order:
    1) Django ORM model (when Django apps are ready)
    2) Redis if REDIS_URL/REDIS_HOST configured and reachable
    3) In-process dictionary
    """

    def __init__(self) -> None:
        self._backend = None
        self._backend_type: str = 'memory'  # 'db' | 'redis' | 'memory'
        self._init_backend()

    def _init_backend(self) -> None:
        """Initialize backing store in order of preference: DB -> Redis -> in-memory."""
        # 1) Try Django DB-backed store
        if self._try_init_db_backend():
            return

        # 2) Try Redis if configured
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
                self._backend_type = 'redis'
                return
            except Exception:
                # fall through to next backend
                self._backend = None

        # 3) In-process fallback
        self._backend = _InProcessStore()
        self._backend_type = 'memory'

    def _try_init_db_backend(self) -> bool:
        """Attempt to initialize the Django DB backend if possible."""
        try:
            from django.apps import apps  # type: ignore
            if not apps.ready:
                return False
            from .models import MemoryEntry  # type: ignore

            class _DjangoDBStore:
                def get(self, key: str):
                    try:
                        ns, k = key.split(':', 1)
                    except ValueError:
                        ns, k = 'default', key
                    try:
                        obj = MemoryEntry.objects.filter(namespace=ns, key=k).first()
                        return None if obj is None else obj.value
                    except Exception:
                        return None

                def set(self, key: str, value):
                    try:
                        ns, k = key.split(':', 1)
                    except ValueError:
                        ns, k = 'default', key
                    try:
                        obj, _created = MemoryEntry.objects.get_or_create(namespace=ns, key=k)
                        obj.value = value
                        obj.save(update_fields=['value', 'updated_at'])
                    except Exception:
                        pass

                def clear(self):
                    try:
                        MemoryEntry.objects.all().delete()
                    except Exception:
                        pass

            self._backend = _DjangoDBStore()
            self._backend_type = 'db'
            return True
        except Exception:
            return False

    def get(self, key: str) -> Any:
        # If Django apps became ready after init, upgrade to DB backend once
        if self._backend_type != 'db':
            if self._try_init_db_backend():
                return self._backend.get(key)
        if self._backend_type == 'db':
            return self._backend.get(key)
        if self._backend_type == 'redis':
            # redis returns bytes/str; we store JSON
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
        # Upgrade to DB backend if available now
        if self._backend_type != 'db':
            if self._try_init_db_backend():
                self._backend.set(key, value)
                return
        if self._backend_type == 'db':
            self._backend.set(key, value)
            return
        if self._backend_type == 'redis':
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
        # Upgrade to DB backend if now available, but still clear active backend
        if self._backend_type != 'db':
            self._try_init_db_backend()

        if self._backend_type == 'db':
            self._backend.clear()
        elif isinstance(self._backend, _InProcessStore):
            self._backend._data.clear()
        elif hasattr(self._backend, 'flushdb'):
            # Redis backend
            self._backend.flushdb()


store = MemoryStore()
