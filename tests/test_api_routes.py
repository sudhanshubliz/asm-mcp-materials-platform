from fastapi.testclient import TestClient

from app import main as app_main


def test_materials_ask_rest_endpoint_delegates_to_tool(monkeypatch):
    def fake_ask_materials_project_tool(question: str, limit: int = 20, offset: int = 0):
        return {"question": question, "limit": limit, "offset": offset, "data": []}

    monkeypatch.setattr(app_main, "ask_materials_project_tool", fake_ask_materials_project_tool)
    client = TestClient(app_main.create_application())

    response = client.post(
        "/api/materials/ask",
        json={"question": "Find stable silicon materials", "limit": 3, "offset": 2},
    )

    assert response.status_code == 200
    assert response.json() == {
        "question": "Find stable silicon materials",
        "limit": 3,
        "offset": 2,
        "data": [],
    }


def test_rag_health_rest_endpoint_delegates_to_tool(monkeypatch):
    monkeypatch.setattr(
        app_main,
        "rag_health_tool",
        lambda: {"ok": True, "collection": "materials_papers", "points_count": 12},
    )
    client = TestClient(app_main.create_application())

    response = client.get("/api/rag/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "collection": "materials_papers", "points_count": 12}
