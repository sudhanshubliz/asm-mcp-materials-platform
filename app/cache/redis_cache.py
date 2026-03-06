import json
from typing import Any

from app.config import config

try:
    import redis  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    redis = None


_memory_cache: dict[str, str] = {}


def _get_redis_client():
    if redis is None:
        return None

    try:
        client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            decode_responses=True,
        )
        client.ping()
        return client
    except Exception:
        return None


redis_client = _get_redis_client()


def get_cache(key: str) -> Any:
    data = redis_client.get(key) if redis_client else _memory_cache.get(key)
    if data:
        return json.loads(data)
    return None


def set_cache(key: str, value: Any, ttl_seconds: int = 3600) -> None:
    payload = json.dumps(value)
    if redis_client:
        redis_client.set(key, payload, ex=ttl_seconds)
        return

    _memory_cache[key] = payload
