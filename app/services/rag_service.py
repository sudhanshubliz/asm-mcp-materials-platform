from app.config import config

try:
    from qdrant_client import QdrantClient, models
except ModuleNotFoundError:  # pragma: no cover
    QdrantClient = None  # type: ignore
    models = None  # type: ignore

_model = None
_qdrant = None


def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError(
                "sentence-transformers is not installed and Qdrant Cloud inference is not configured"
            ) from exc
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
            client_kwargs["cloud_inference"] = True
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


def qdrant_health() -> dict:
    health = {
        "ok": False,
        "url_configured": bool(config.VECTOR_DB),
        "collection": config.RAG_COLLECTION,
        "inference_model": config.QDRANT_INFERENCE_MODEL,
        "cloud_inference": bool(config.QDRANT_API_KEY),
        "points_count": None,
        "error": None,
    }
    try:
        qdrant = _get_qdrant()
        collection = qdrant.get_collection(config.RAG_COLLECTION)
        points_count = getattr(collection, "points_count", None)
        if points_count is None and isinstance(collection, dict):
            points_count = collection.get("points_count")
        health["points_count"] = points_count
        health["ok"] = True
    except Exception as exc:
        health["error"] = str(exc)
    return health


def search_documents(query: str, top_k: int | None = None):
    qdrant = _get_qdrant()
    limit = top_k or config.RAG_TOP_K

    if config.QDRANT_API_KEY:
        if models is None:
            raise RuntimeError("qdrant-client is not installed")
        response = qdrant.query_points(
            collection_name=config.RAG_COLLECTION,
            query=models.Document(text=query, model=config.QDRANT_INFERENCE_MODEL),
            limit=limit,
            with_payload=True,
        )
        results = response.points
    else:
        model = _get_model()
        embedding = model.encode(query)
        query_vector = embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)
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
