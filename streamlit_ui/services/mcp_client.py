from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx
from cachetools import TTLCache
from fastmcp import Client

LOCAL_MCP_URL = "http://localhost:8000/mcp"
RENDER_MCP_URL = "https://asm-mcp-materials-platform.onrender.com/mcp"


class MCPClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConnectionStatus:
    ok: bool
    latency_ms: float
    tools: list[str]
    health: dict[str, Any]
    endpoint: str
    error: str | None = None


def _get_env_or_secret(name: str, default: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st

        secret_value = st.secrets.get(name)
        if secret_value:
            return str(secret_value)
    except Exception:
        pass
    return default


def _health_url_for(base_url: str) -> str:
    if base_url.endswith("/mcp"):
        return f"{base_url[:-4]}/health"
    return f"{base_url}/health"


def _probe_health(base_url: str, timeout_seconds: float) -> bool:
    try:
        response = httpx.get(_health_url_for(base_url), timeout=timeout_seconds)
        return response.status_code == 200
    except Exception:
        return False


def _is_local_url(base_url: str) -> bool:
    host = urlparse(base_url).hostname
    return host in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def _resolve_mcp_server_url(timeout_seconds: float) -> str:
    configured = _get_env_or_secret("MCP_SERVER_URL", "").strip()
    if configured:
        configured = configured.rstrip("/")
        if not _is_local_url(configured):
            return configured

        probe_timeout = min(timeout_seconds, 3.0)
        if _probe_health(configured, timeout_seconds=probe_timeout):
            return configured
        if _probe_health(RENDER_MCP_URL, timeout_seconds=probe_timeout):
            return RENDER_MCP_URL
        return RENDER_MCP_URL

    for candidate in (LOCAL_MCP_URL, RENDER_MCP_URL):
        if _probe_health(candidate, timeout_seconds=min(timeout_seconds, 3.0)):
            return candidate

    return LOCAL_MCP_URL


class MCPClientService:
    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float = 45.0,
        retry_attempts: int = 2,
        retry_backoff_seconds: float = 0.6,
        cache_ttl_seconds: int = 180,
    ) -> None:
        resolved_base_url = base_url or _resolve_mcp_server_url(timeout_seconds)
        self.base_url = resolved_base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds
        self.auth_token = _get_env_or_secret("MCP_AUTH_TOKEN", "")
        self._cache: TTLCache[str, dict[str, Any]] = TTLCache(maxsize=256, ttl=cache_ttl_seconds)

    @property
    def health_url(self) -> str:
        return _health_url_for(self.base_url)

    def _cache_key(self, tool_name: str, arguments: dict[str, Any]) -> str:
        return json.dumps({"tool": tool_name, "arguments": arguments}, sort_keys=True, default=str)

    def _run_async(self, coroutine):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coroutine)
        finally:
            loop.close()

    async def _call_tool_once(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        auth = f"Bearer {self.auth_token}" if self.auth_token else None
        async with Client(self.base_url, timeout=self.timeout_seconds, auth=auth) as client:
            result = await client.call_tool(tool_name, arguments)
            payload = result.data if result.data is not None else result.structured_content
            if not isinstance(payload, dict):
                raise MCPClientError(f"Unexpected response payload from {tool_name}: {payload!r}")
            return payload

    async def _list_tools_once(self) -> list[str]:
        auth = f"Bearer {self.auth_token}" if self.auth_token else None
        async with Client(self.base_url, timeout=self.timeout_seconds, auth=auth) as client:
            tools = await client.list_tools()
            return [tool.name for tool in tools]

    def call_tool(self, tool_name: str, arguments: dict[str, Any], *, use_cache: bool = True) -> dict[str, Any]:
        cache_key = self._cache_key(tool_name, arguments)
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        last_error: Exception | None = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                payload = self._run_async(self._call_tool_once(tool_name, arguments))
                if use_cache:
                    self._cache[cache_key] = payload
                return payload
            except Exception as exc:
                last_error = exc
                if attempt == self.retry_attempts:
                    break
                time.sleep(self.retry_backoff_seconds * attempt)

        raise MCPClientError(f"Tool call failed for {tool_name} via {self.base_url}: {last_error}")

    def compare_materials(self, targets: list[str]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for target in targets[:5]:
            if target.lower().startswith("mp-"):
                record = self.call_tool("get_material_by_id_tool", {"material_id": target}, use_cache=True)
                if record:
                    records.append(record)
                continue

            payload = self.call_tool("search_material_tool", {"formula": target, "limit": 5, "offset": 0}, use_cache=True)
            data = payload.get("materials_project", {}).get("data", [])
            if data:
                records.append(data[0])
        return records

    def health_check(self) -> ConnectionStatus:
        start = time.perf_counter()
        try:
            response = httpx.get(self.health_url, timeout=self.timeout_seconds)
            response.raise_for_status()
            health = response.json()
            tools = self._run_async(self._list_tools_once())
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return ConnectionStatus(
                ok=True,
                latency_ms=latency_ms,
                tools=tools,
                health=health,
                endpoint=self.base_url,
            )
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return ConnectionStatus(
                ok=False,
                latency_ms=latency_ms,
                tools=[],
                health={},
                endpoint=self.base_url,
                error=str(exc),
            )
