from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

from cachetools import TTLCache


class Cache:
    def __init__(self, ttl_s: int, maxsize: int):
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl_s)

    @staticmethod
    def _key(prefix: str, payload: Any) -> str:
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
        h = hashlib.sha256(raw).hexdigest()
        return f"{prefix}:{h}"

    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = value
