from app.services.db_service import run_query


def query_database(query: str) -> list[dict]:
    return run_query(query)
