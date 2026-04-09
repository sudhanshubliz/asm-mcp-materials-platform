from unittest.mock import MagicMock

from streamlit_ui.services.mcp_client import MCPClientService


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
