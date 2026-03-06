from sqlalchemy import create_engine, text

from app.config import config

engine = create_engine(config.SQL_CONNECTION, pool_pre_ping=True)

_DISALLOWED_SQL_TOKENS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "create",
    "merge",
    "grant",
    "revoke",
    "exec",
    "execute",
    "call",
}


def _validate_read_only_query(query: str) -> None:
    normalized = query.strip().lower()
    if not normalized.startswith(("select", "with")):
        raise ValueError("Only read-only SELECT/CTE SQL statements are allowed")

    compact = normalized.replace("\n", " ")
    if ";" in compact.rstrip(";"):
        raise ValueError("Multiple SQL statements are not allowed")

    query_tokens = set(compact.replace("(", " ").replace(")", " ").split())
    blocked = _DISALLOWED_SQL_TOKENS.intersection(query_tokens)
    if blocked:
        raise ValueError(f"Disallowed SQL operations detected: {', '.join(sorted(blocked))}")


def run_query(query: str, limit: int | None = None) -> list[dict]:
    _validate_read_only_query(query)
    max_rows = limit or config.SQL_MAX_ROWS

    with engine.connect() as conn:
        result = conn.execute(text(query))
        rows = result.fetchmany(max_rows)
        return [dict(row._mapping) for row in rows]
