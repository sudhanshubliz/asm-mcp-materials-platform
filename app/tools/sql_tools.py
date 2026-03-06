from app.models.schemas import SQLQueryRequest
from app.services.db_service import run_query


def run_sql_query(query: str, limit: int = 100) -> list[dict]:
    request = SQLQueryRequest(query=query, limit=limit)
    return run_query(request.query, request.limit)
