from app.config import config

try:
    from qdrant_client import QdrantClient
    from sentence_transformers import SentenceTransformer
except ModuleNotFoundError:  # pragma: no cover
    QdrantClient = None  # type: ignore
    SentenceTransformer = None  # type: ignore

_model = None
_qdrant = None


def _get_model():
    global _model
    if _model is None:
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers is not installed")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _get_qdrant():
    global _qdrant
    if _qdrant is None:
        if QdrantClient is None:
            raise RuntimeError("qdrant-client is not installed")
        client_kwargs = {"url": config.VECTOR_DB, "timeout": config.REQUEST_TIMEOUT}
        if config.QDRANT_API_KEY:
            client_kwargs["api_key"] = config.QDRANT_API_KEY
        _qdrant = QdrantClient(**client_kwargs)
    return _qdrant


def _payload_text(payload: dict | None) -> str:
    if not payload:
        return ""

    for field_name in ("text", "content", "page_content", "document", "chunk", "summary", "abstract"):
        value = payload.get(field_name)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""


def search_documents(query: str, top_k: int | None = None):
    model = _get_model()
    qdrant = _get_qdrant()

    embedding = model.encode(query)
    query_vector = embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)

    limit = top_k or config.RAG_TOP_K
    results = qdrant.search(
        collection_name=config.RAG_COLLECTION,
        query_vector=query_vector,
        limit=limit,
    )

    return [
        {
            "id": point.id,
            "score": point.score,
            "text": _payload_text(point.payload),
            "payload": point.payload,
        }
        for point in results
    ]
