from fastapi import Depends, FastAPI, HTTPException, Path
from fastmcp import FastMCP

from app.auth import require_authenticated_user, require_role
from app.app_logging import setup_logging
from app.models.schemas import MaterialSearchRequest, RagSearchRequest, SQLQueryRequest
from app.services.exceptions import ExternalServiceError
from app.services.materials_service import get_material_by_id
from app.tools.materials_tools import ask_materials_project_tool, get_material_by_id_tool, search_material_tool
from app.tools.rag_tools import rag_search_tool
from app.tools.sql_tools import run_sql_query

import logging
logging.basicConfig(level=logging.ERROR)

setup_logging()

mcp = FastMCP(name="ASM Materials MCP Server")
mcp.add_tool(search_material_tool)
mcp.add_tool(get_material_by_id_tool)
mcp.add_tool(ask_materials_project_tool)
mcp.add_tool(run_sql_query)
mcp.add_tool(rag_search_tool)

api = FastAPI(title="ASM Materials MCP Server", version="1.1.0")


@api.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@api.post("/api/materials/search")
def materials_search(
    payload: MaterialSearchRequest,
    _auth: str | None = Depends(require_authenticated_user),
    _roles: set[str] = Depends(require_role({"MaterialsReader", "MaterialsEngineer", "MaterialsAdmin"})),
):
    try:
        return search_material_tool(payload.formula, payload.limit, payload.offset)
    except ExternalServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.to_dict(),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error while searching materials: {exc}",
        ) from exc


@api.get("/api/materials/{material_id}")
def materials_by_id(
    material_id: str = Path(
        ...,
        min_length=3,
        max_length=40,
        pattern=r"^mp-[A-Za-z0-9-]+$",
        description="Materials Project material ID, e.g. mp-csvwu",
    ),
    _auth: str | None = Depends(require_authenticated_user),
    _roles: set[str] = Depends(require_role({"MaterialsReader", "MaterialsEngineer", "MaterialsAdmin"})),
):
    try:
        return get_material_by_id(material_id)
    except ExternalServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.to_dict(),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error while fetching material by id: {exc}",
        ) from exc


@api.post("/api/sql/query")
def sql_query(
    payload: SQLQueryRequest,
    _auth: str | None = Depends(require_authenticated_user),
    _roles: set[str] = Depends(require_role({"MaterialsReader", "MaterialsAdmin"})),
):
    return run_sql_query(payload.query, payload.limit)


@api.post("/api/rag/search")
def rag_search(
    payload: RagSearchRequest,
    _auth: str | None = Depends(require_authenticated_user),
    _roles: set[str] = Depends(require_role({"MaterialsReader", "MaterialsEngineer", "MaterialsAdmin"})),
):
    return rag_search_tool(payload.question, payload.top_k)


if __name__ == "__main__":
    mcp.run()
