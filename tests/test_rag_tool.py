from app.tools import rag_tools


def test_rag_search_tool_returns_nearest_neighbor_payload(monkeypatch):
    def fake_search_documents(question, top_k):
        return [
            {
                "id": "chunk-1",
                "score": 0.91,
                "text": "Lithium cathode text chunk",
                "payload": {"text": "Lithium cathode text chunk", "source": "paper.pdf"},
            }
        ]

    monkeypatch.setattr(rag_tools, "search_documents", fake_search_documents)

    result = rag_tools.rag_search_tool("battery cathodes", top_k=1)

    assert result == {
        "question": "battery cathodes",
        "top_k": 1,
        "data": [
            {
                "id": "chunk-1",
                "score": 0.91,
                "text": "Lithium cathode text chunk",
                "payload": {"text": "Lithium cathode text chunk", "source": "paper.pdf"},
            }
        ],
    }
