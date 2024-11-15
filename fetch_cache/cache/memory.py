from datetime import datetime
from typing import Optional, Any, Dict
from .base import BaseCache


class MemoryCache(BaseCache):
    def __init__(self):
        self._cache: Dict[str, Dict] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache and self._cache[key]["expires"] > datetime.now():
            return self._cache[key]["value"]
        return None

    def set(self, key: str, value: Any, expires: datetime) -> None:
        self._cache[key] = {"value": value, "expires": expires}

    def delete(self, key: str) -> None:
        self._cache.pop(key, None)

    def clear(self) -> None:
        self._cache.clear()
