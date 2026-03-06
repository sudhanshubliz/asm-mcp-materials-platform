import os

from dotenv import load_dotenv

load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SQL_CONNECTION = os.getenv("SQL_CONNECTION_STRING") or os.getenv(
        "SQL_CONNECTION", "sqlite+pysqlite:///:memory:"
    )
    MATERIALS_API = os.getenv("MATERIALS_API", "https://next-gen.materialsproject.org/api")
    MATERIALS_SUMMARY_PATH = os.getenv("MATERIALS_SUMMARY_PATH", "/materials/summary")
    MATERIALS_API_KEY_HEADER = os.getenv("MATERIALS_API_KEY_HEADER", "X-API-KEY")
    MATERIALS_API_MODE = os.getenv("MATERIALS_API_MODE", "auto")
    OQMD_API = os.getenv("OQMD_API", "https://oqmd.org/api")
    OQMD_RESOURCE = os.getenv("OQMD_RESOURCE", "formationenergy")
    OQMD_REQUIRED = _as_bool(os.getenv("OQMD_REQUIRED"), default=True)

    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

    VECTOR_DB = os.getenv("VECTOR_DB", "http://localhost:6333")
    RAG_COLLECTION = os.getenv("RAG_COLLECTION", "materials_papers")
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))

    MATERIALS_API_KEY = os.getenv("MATERIALS_API_KEY", "")

    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
    SQL_MAX_ROWS = int(os.getenv("SQL_MAX_ROWS", "100"))

    MCP_REQUIRE_AUTH = _as_bool(os.getenv("MCP_REQUIRE_AUTH"), default=False)
    ALLOWED_ROLES = tuple(
        role.strip()
        for role in os.getenv(
            "ALLOWED_ROLES", "MaterialsReader,MaterialsEngineer,MaterialsAdmin"
        ).split(",")
        if role.strip()
    )

    APP_INSIGHTS_CONNECTION_STRING = os.getenv("APP_INSIGHTS_CONNECTION_STRING", "")


config = Config()
