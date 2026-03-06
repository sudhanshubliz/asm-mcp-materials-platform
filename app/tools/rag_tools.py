from app.models.schemas import RagSearchRequest
from app.services.rag_service import search_documents


def rag_search_tool(question: str, top_k: int = 5):
    request = RagSearchRequest(question=question, top_k=top_k)
    return search_documents(request.question, request.top_k)
