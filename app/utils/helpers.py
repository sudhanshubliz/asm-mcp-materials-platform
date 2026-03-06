import hashlib


def stable_cache_key(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"
