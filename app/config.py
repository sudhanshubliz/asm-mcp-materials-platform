import os

from dotenv import load_dotenv

load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


class Config:
    APP_NAME = os.getenv("APP_NAME", "ASM Materials MCP Server")
    APP_VERSION = os.getenv("APP_VERSION", "2.0.0")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

    SQL_CONNECTION = os.getenv("SQL_CONNECTION_STRING") or os.getenv(
        "SQL_CONNECTION", "sqlite+pysqlite:///:memory:"
    )
    SQL_MAX_ROWS = int(os.getenv("SQL_MAX_ROWS", "100"))

    MATERIALS_API = os.getenv("MATERIALS_API", "https://next-gen.materialsproject.org/api")
    MATERIALS_SUMMARY_PATH = os.getenv("MATERIALS_SUMMARY_PATH", "/materials/summary")
    MATERIALS_API_KEY_HEADER = os.getenv("MATERIALS_API_KEY_HEADER", "X-API-KEY")
    MATERIALS_API_MODE = os.getenv("MATERIALS_API_MODE", "auto")
    MATERIALS_API_KEY = os.getenv("MATERIALS_API_KEY", "")

    OQMD_API = os.getenv("OQMD_API", "https://oqmd.org/api")
    OQMD_RESOURCE = os.getenv("OQMD_RESOURCE", "formationenergy")
    OQMD_REQUIRED = _as_bool(os.getenv("OQMD_REQUIRED"), default=False)

    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))

    VECTOR_DB = os.getenv("VECTOR_DB", "http://localhost:6333")
    RAG_COLLECTION = os.getenv("RAG_COLLECTION", "materials_papers")
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))

    REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30"))
    REQUEST_RETRY_ATTEMPTS = int(os.getenv("REQUEST_RETRY_ATTEMPTS", "3"))
    REQUEST_RETRY_BACKOFF = float(os.getenv("REQUEST_RETRY_BACKOFF", "0.5"))

    MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()
    MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
    MCP_PORT = int(os.getenv("MCP_PORT", os.getenv("PORT", "8000")))
    MCP_PATH = os.getenv("MCP_PATH", "/mcp")
    MCP_REQUIRE_AUTH = _as_bool(os.getenv("MCP_REQUIRE_AUTH"), default=False)
    MCP_PUBLISH_METADATA = _as_bool(os.getenv("MCP_PUBLISH_METADATA"), default=True)
    ALLOWED_ROLES = tuple(
        role.strip()
        for role in os.getenv(
            "ALLOWED_ROLES", "MaterialsReader,MaterialsEngineer,MaterialsAdmin"
        ).split(",")
        if role.strip()
    )

    CORS_ALLOWED_ORIGINS = _as_csv(os.getenv("CORS_ALLOWED_ORIGINS"))

    APP_INSIGHTS_CONNECTION_STRING = os.getenv("APP_INSIGHTS_CONNECTION_STRING", "")


config = Config()
