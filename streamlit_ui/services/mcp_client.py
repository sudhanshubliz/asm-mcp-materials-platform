from __future__ import annotations

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx
from cachetools import TTLCache
from fastmcp import Client

LOCAL_MCP_URL = "http://localhost:8000/mcp"
RENDER_MCP_URL = "https://asm-mcp-materials-platform.onrender.com/mcp"
REST_FALLBACK_TOOLS = [
    "search_material_tool",
    "search_materials_advanced_tool",
    "get_material_by_id_tool",
    "ask_materials_project_tool",
    "rag_search_tool",
    "rag_health_tool",
]
RANGE_ARGUMENT_PREFIXES = (
    "num_elements",
    "band_gap",
    "density",
    "volume",
    "energy_above_hull",
    "bulk_modulus_vrh",
    "shear_modulus_vrh",
    "weighted_surface_energy",
    "work_function",
    "surface_anisotropy",
    "shape_factor",
)


class MCPClientError(RuntimeError):
    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.detail = detail


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


def _api_base_url_for(base_url: str) -> str:
    return base_url[:-4] if base_url.endswith("/mcp") else base_url.rstrip("/")


def _advanced_rest_payload(arguments: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in arguments.items():
        if value in (None, [], {}):
            continue
        if key.endswith("_min") or key.endswith("_max"):
            continue
        payload[key] = value

    for field_name in RANGE_ARGUMENT_PREFIXES:
        minimum = arguments.get(f"{field_name}_min")
        maximum = arguments.get(f"{field_name}_max")
        if minimum is not None or maximum is not None:
            range_payload: dict[str, float] = {}
            if minimum is not None:
                range_payload["min"] = minimum
            if maximum is not None:
                range_payload["max"] = maximum
            payload[field_name] = range_payload

    return payload


def _upsert_range(payload: dict[str, Any], field_name: str, *, minimum: float | None = None, maximum: float | None = None) -> None:
    current = dict(payload.get(field_name) or {})
    if minimum is not None:
        current["min"] = minimum if "min" not in current else max(current["min"], minimum)
    if maximum is not None:
        current["max"] = maximum if "max" not in current else min(current["max"], maximum)
    if current:
        payload[field_name] = current


def _ask_compat_rest_payload(arguments: dict[str, Any]) -> dict[str, Any] | None:
    question = str(arguments.get("question") or "").strip()
    if not question:
        return None

    payload: dict[str, Any] = {
        "query": question,
        "limit": arguments.get("limit", 20),
        "offset": arguments.get("offset", 0),
    }
    lowered = question.lower()

    if "lightweight" in lowered:
        _upsert_range(payload, "density", maximum=5.0)
    if "alloy" in lowered or "alloys" in lowered:
        payload["is_metal"] = True
        _upsert_range(payload, "num_elements", minimum=2)
    if "aerospace" in lowered:
        payload["is_stable"] = True
        _upsert_range(payload, "bulk_modulus_vrh", minimum=40.0)
        _upsert_range(payload, "shear_modulus_vrh", minimum=20.0)
    if "cathode" in lowered and re.search(r"\bbatter(?:y|ies)\b", lowered):
        payload["elements"] = ["Li", "O"]
        payload["is_stable"] = True
        _upsert_range(payload, "num_elements", minimum=2)
    if "semiconductor" in lowered or "semiconductors" in lowered:
        payload["is_metal"] = False
        _upsert_range(payload, "band_gap", minimum=0.1, maximum=3.5)

    has_criteria = any(key not in {"query", "limit", "offset"} for key in payload)
    return payload if has_criteria else None


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

    def _auth_headers(self) -> dict[str, str]:
        if not self.auth_token:
            return {}
        return {"Authorization": f"Bearer {self.auth_token}"}

    def _call_tool_via_rest(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        api_base_url = _api_base_url_for(self.base_url)
        headers = self._auth_headers()

        if tool_name == "search_material_tool":
            response = httpx.post(
                f"{api_base_url}/api/materials/search",
                json=arguments,
                headers=headers,
                timeout=self.timeout_seconds,
            )
        elif tool_name == "search_materials_advanced_tool":
            response = httpx.post(
                f"{api_base_url}/api/materials/advanced-search",
                json=_advanced_rest_payload(arguments),
                headers=headers,
                timeout=self.timeout_seconds,
            )
        elif tool_name == "get_material_by_id_tool":
            response = httpx.get(
                f"{api_base_url}/api/materials/{arguments['material_id']}",
                headers=headers,
                timeout=self.timeout_seconds,
            )
        elif tool_name == "ask_materials_project_tool":
            response = httpx.post(
                f"{api_base_url}/api/materials/ask",
                json=arguments,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            if response.status_code in {404, 405}:
                compat_payload = _ask_compat_rest_payload(arguments)
                if compat_payload is None:
                    response.raise_for_status()
                response = httpx.post(
                    f"{api_base_url}/api/materials/advanced-search",
                    json=compat_payload,
                    headers=headers,
                    timeout=self.timeout_seconds,
                )
        elif tool_name == "rag_search_tool":
            response = httpx.post(
                f"{api_base_url}/api/rag/search",
                json=arguments,
                headers=headers,
                timeout=self.timeout_seconds,
            )
        elif tool_name == "rag_health_tool":
            response = httpx.get(
                f"{api_base_url}/api/rag/health",
                headers=headers,
                timeout=self.timeout_seconds,
            )
        else:
            raise MCPClientError(f"No REST fallback is configured for {tool_name}")

        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise MCPClientError(f"Unexpected REST response payload from {tool_name}: {payload!r}")
        if tool_name == "get_material_by_id_tool" and not payload.get("material_id"):
            payload["material_id"] = arguments["material_id"]
            payload.setdefault("materials_project_url", f"https://next-gen.materialsproject.org/materials/{arguments['material_id']}")
        return payload

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

        if tool_name in REST_FALLBACK_TOOLS and not _is_local_url(self.base_url):
            try:
                payload = self._call_tool_via_rest(tool_name, arguments)
                if use_cache:
                    self._cache[cache_key] = payload
                return payload
            except Exception as exc:
                last_error = exc

        raise MCPClientError(
            _friendly_tool_error(tool_name),
            detail=f"Tool call failed for {tool_name} via {self.base_url}: {last_error}",
        )

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
            try:
                tools = self._run_async(self._list_tools_once())
                error = None
            except Exception as exc:
                tools = REST_FALLBACK_TOOLS
                error = f"MCP tool listing unavailable; REST fallback is active: {exc}"
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return ConnectionStatus(
                ok=True,
                latency_ms=latency_ms,
                tools=tools,
                health=health,
                endpoint=self.base_url,
                error=error,
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

    def qdrant_health(self) -> dict[str, Any]:
        try:
            return self.call_tool("rag_health_tool", {}, use_cache=False)
        except Exception as exc:
            return {
                "ok": False,
                "collection": None,
                "points_count": None,
                "inference_model": None,
                "error": getattr(exc, "detail", None) or str(exc),
            }


def _friendly_tool_error(tool_name: str) -> str:
    if tool_name == "rag_search_tool":
        return "Nearest-neighbor search is unavailable. Check Qdrant health and try again."
    if tool_name == "get_material_by_id_tool":
        return "Material lookup is unavailable right now. Try again in a moment."
    if tool_name in {"search_material_tool", "search_materials_advanced_tool", "ask_materials_project_tool"}:
        return "Materials search is unavailable right now. Try again in a moment."
    return "The remote service is unavailable right now. Try again in a moment."
