import pytest
from unittest.mock import MagicMock

from streamlit_ui.services.mcp_client import LOCAL_MCP_URL, MCPClientService, RENDER_MCP_URL, _ask_compat_rest_payload


def test_call_tool_retries_then_succeeds(monkeypatch):
    client = MCPClientService(base_url="http://localhost:8000/mcp", retry_attempts=2, retry_backoff_seconds=0)
    calls = {"count": 0}

    def fake_run_async(coroutine):
        coroutine.close()
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("temporary failure")
        return {"ok": True}

    monkeypatch.setattr(client, "_run_async", fake_run_async)

    result = client.call_tool("search_material_tool", {"formula": "Si"})

    assert result == {"ok": True}
    assert calls["count"] == 2


def test_call_tool_uses_cache(monkeypatch):
    client = MCPClientService(base_url="http://localhost:8000/mcp")

    def fake_run_async(coroutine):
        coroutine.close()
        return {"cached": "value"}

    monkeypatch.setattr(client, "_run_async", fake_run_async)

    first = client.call_tool("search_material_tool", {"formula": "Si"})
    second = client.call_tool("search_material_tool", {"formula": "Si"})

    assert first == second == {"cached": "value"}


def test_compare_materials_combines_mp_ids_and_formulas(monkeypatch):
    client = MCPClientService(base_url="http://localhost:8000/mcp")
    call_tool = MagicMock(
        side_effect=[
            {"material_id": "mp-149", "formula_pretty": "Si"},
            {"materials_project": {"data": [{"material_id": "mp-2534", "formula_pretty": "GaAs"}]}},
        ]
    )
    monkeypatch.setattr(client, "call_tool", call_tool)

    records = client.compare_materials(["mp-149", "GaAs"])

    assert [record["formula_pretty"] for record in records] == ["Si", "GaAs"]


def test_client_uses_explicit_base_url_without_auto_resolution():
    client = MCPClientService(base_url="https://example.com/mcp")

    assert client.base_url == "https://example.com/mcp"


def test_client_auto_falls_back_to_render_when_local_unavailable(monkeypatch):
    def fake_probe(url, timeout_seconds):
        return url == RENDER_MCP_URL

    monkeypatch.setattr("streamlit_ui.services.mcp_client._probe_health", fake_probe)
    monkeypatch.setattr("streamlit_ui.services.mcp_client._get_env_or_secret", lambda name, default="": "")

    client = MCPClientService(base_url=None)

    assert client.base_url == RENDER_MCP_URL


def test_client_ignores_configured_localhost_when_unreachable(monkeypatch):
    def fake_probe(url, timeout_seconds):
        return url == RENDER_MCP_URL

    monkeypatch.setattr("streamlit_ui.services.mcp_client._probe_health", fake_probe)
    monkeypatch.setattr(
        "streamlit_ui.services.mcp_client._get_env_or_secret",
        lambda name, default="": LOCAL_MCP_URL,
    )

    client = MCPClientService(base_url=None)

    assert client.base_url == RENDER_MCP_URL


def test_client_uses_configured_localhost_when_reachable(monkeypatch):
    monkeypatch.setattr(
        "streamlit_ui.services.mcp_client._probe_health",
        lambda url, timeout_seconds: url == LOCAL_MCP_URL,
    )
    monkeypatch.setattr(
        "streamlit_ui.services.mcp_client._get_env_or_secret",
        lambda name, default="": LOCAL_MCP_URL,
    )

    client = MCPClientService(base_url=None)

    assert client.base_url == LOCAL_MCP_URL


def test_client_defaults_to_local_when_no_probe_succeeds(monkeypatch):
    monkeypatch.setattr("streamlit_ui.services.mcp_client._probe_health", lambda url, timeout_seconds: False)
    monkeypatch.setattr("streamlit_ui.services.mcp_client._get_env_or_secret", lambda name, default="": "")

    client = MCPClientService(base_url=None)

    assert client.base_url == LOCAL_MCP_URL


def test_call_tool_falls_back_to_rest_for_remote_mcp_failure(monkeypatch):
    client = MCPClientService(base_url=RENDER_MCP_URL, retry_attempts=1)

    def fail_mcp(coroutine):
        coroutine.close()
        raise RuntimeError("Client error '421 Misdirected Request'")

    rest_call = MagicMock(return_value={"materials_project": {"data": []}})
    monkeypatch.setattr(client, "_run_async", fail_mcp)
    monkeypatch.setattr(client, "_call_tool_via_rest", rest_call)

    result = client.call_tool("search_material_tool", {"formula": "Si"})

    assert result == {"materials_project": {"data": []}}
    rest_call.assert_called_once_with("search_material_tool", {"formula": "Si"})


def test_call_tool_does_not_use_rest_fallback_for_local_mcp_failure(monkeypatch):
    client = MCPClientService(base_url=LOCAL_MCP_URL, retry_attempts=1)

    def fail_mcp(coroutine):
        coroutine.close()
        raise RuntimeError("connection refused")

    rest_call = MagicMock(return_value={"ok": True})
    monkeypatch.setattr(client, "_run_async", fail_mcp)
    monkeypatch.setattr(client, "_call_tool_via_rest", rest_call)

    with pytest.raises(Exception) as exc_info:
        client.call_tool("search_material_tool", {"formula": "Si"})

    assert "Materials search is unavailable" in str(exc_info.value)
    assert "connection refused" in exc_info.value.detail
    rest_call.assert_not_called()


def test_health_check_uses_rest_tool_list_when_mcp_listing_fails(monkeypatch):
    client = MCPClientService(base_url=RENDER_MCP_URL)
    response = MagicMock()
    response.json.return_value = {"status": "ok"}
    response.raise_for_status.return_value = None
    monkeypatch.setattr("streamlit_ui.services.mcp_client.httpx.get", MagicMock(return_value=response))

    def fail_list(coroutine):
        coroutine.close()
        raise RuntimeError("Client error '421 Misdirected Request'")

    monkeypatch.setattr(client, "_run_async", fail_list)

    status = client.health_check()

    assert status.ok is True
    assert "search_material_tool" in status.tools
    assert "REST fallback is active" in str(status.error)


def test_rest_material_lookup_preserves_requested_material_id(monkeypatch):
    client = MCPClientService(base_url=RENDER_MCP_URL)
    response = MagicMock()
    response.json.return_value = {"material_id": None, "formula_pretty": "Si"}
    response.raise_for_status.return_value = None
    monkeypatch.setattr("streamlit_ui.services.mcp_client.httpx.get", MagicMock(return_value=response))

    payload = client._call_tool_via_rest("get_material_by_id_tool", {"material_id": "mp-149"})

    assert payload["material_id"] == "mp-149"
    assert payload["materials_project_url"] == "https://next-gen.materialsproject.org/materials/mp-149"


def test_qdrant_health_returns_unavailable_payload_on_failure(monkeypatch):
    client = MCPClientService(base_url=RENDER_MCP_URL)
    monkeypatch.setattr(
        client,
        "call_tool",
        MagicMock(side_effect=RuntimeError("route missing")),
    )

    status = client.qdrant_health()

    assert status["ok"] is False
    assert "route missing" in status["error"]


def test_ask_compat_payload_handles_lightweight_aerospace_alloys():
    payload = _ask_compat_rest_payload(
        {"question": "Find lightweight alloys used in aerospace engineering", "limit": 10, "offset": 0}
    )

    assert payload == {
        "query": "Find lightweight alloys used in aerospace engineering",
        "limit": 10,
        "offset": 0,
        "density": {"max": 5.0},
        "is_metal": True,
        "num_elements": {"min": 2},
        "is_stable": True,
        "bulk_modulus_vrh": {"min": 40.0},
        "shear_modulus_vrh": {"min": 20.0},
    }


def test_ask_compat_payload_handles_battery_cathodes():
    payload = _ask_compat_rest_payload({"question": "Find stable cathode materials for batteries"})

    assert payload == {
        "query": "Find stable cathode materials for batteries",
        "limit": 20,
        "offset": 0,
        "elements": ["Li", "O"],
        "is_stable": True,
        "num_elements": {"min": 2},
    }


def test_ask_compat_payload_returns_none_for_unknown_question():
    assert _ask_compat_rest_payload({"question": "Tell me something interesting"}) is None
