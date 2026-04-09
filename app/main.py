from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Path, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastmcp import FastMCP
from fastmcp.utilities.lifespan import combine_lifespans

from app.app_logging import get_logger, setup_logging
from app.auth import require_authenticated_user, require_role
from app.config import config
from app.models.schemas import (
    AdvancedMaterialSearchRequest,
    MaterialSearchRequest,
    RagSearchRequest,
    SQLQueryRequest,
)
from app.services.exceptions import ExternalServiceError
from app.services.materials_service import get_material_by_id
from app.tools.materials_tools import (
    ask_materials_project_tool,
    get_material_by_id_tool,
    search_material_tool,
    search_materials_advanced_tool,
)
from app.tools.rag_tools import rag_search_tool
from app.tools.sql_tools import run_sql_query

setup_logging(config.LOG_LEVEL)
logger = get_logger(__name__)


def _error_payload(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: object | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "error": {
            "code": code,
            "message": message,
            "request_id": getattr(request.state, "request_id", None),
        }
    }
    if details is not None:
        payload["error"]["details"] = details
    return payload


def create_mcp_server() -> FastMCP:
    mcp_server = FastMCP(name=config.APP_NAME)
    mcp_server.add_tool(search_material_tool)
    mcp_server.add_tool(search_materials_advanced_tool)
    mcp_server.add_tool(get_material_by_id_tool)
    mcp_server.add_tool(ask_materials_project_tool)
    mcp_server.add_tool(run_sql_query)
    mcp_server.add_tool(rag_search_tool)
    return mcp_server


mcp = create_mcp_server()
mcp_http_app = mcp.http_app(path="/", transport="streamable-http")


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    logger.info(
        "application.startup",
        extra={
            "path": config.MCP_PATH,
            "method": "STARTUP",
        },
    )
    yield
    logger.info(
        "application.shutdown",
        extra={
            "path": config.MCP_PATH,
            "method": "SHUTDOWN",
        },
    )


def create_application() -> FastAPI:
    api = FastAPI(
        title=config.APP_NAME,
        version=config.APP_VERSION,
        lifespan=combine_lifespans(app_lifespan, mcp_http_app.lifespan),
    )

    if config.CORS_ALLOWED_ORIGINS:
        api.add_middleware(
            CORSMiddleware,
            allow_origins=list(config.CORS_ALLOWED_ORIGINS),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @api.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(
                "request.failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request.completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    @api.exception_handler(ExternalServiceError)
    async def external_service_error_handler(request: Request, exc: ExternalServiceError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(
                request,
                status_code=exc.status_code,
                code="external_service_error",
                message=exc.message,
                details=exc.to_dict(),
            ),
        )

    @api.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_payload(
                request,
                status_code=422,
                code="validation_error",
                message="Request validation failed",
                details=exc.errors(),
            ),
        )

    @api.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(
                request,
                status_code=exc.status_code,
                code="http_error",
                message=str(exc.detail),
                details=exc.detail,
            ),
        )

    @api.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "request.unhandled_exception",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "method": request.method,
                "path": request.url.path,
            },
        )
        return JSONResponse(
            status_code=500,
            content=_error_payload(
                request,
                status_code=500,
                code="internal_server_error",
                message="Unexpected server error",
            ),
        )

    @api.get("/")
    def root() -> dict[str, object]:
        return {
            "name": config.APP_NAME,
            "version": config.APP_VERSION,
            "health": "/health",
            "mcp": config.MCP_PATH,
            "docs": "/docs",
        }

    @api.get("/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": config.APP_NAME,
            "version": config.APP_VERSION,
            "mcp_path": config.MCP_PATH,
            "auth_required": config.MCP_REQUIRE_AUTH,
            "oqmd_required": config.OQMD_REQUIRED,
        }

    @api.get("/.well-known/mcp.json")
    def well_known_mcp(request: Request) -> dict[str, object]:
        if not config.MCP_PUBLISH_METADATA:
            raise HTTPException(status_code=404, detail="MCP metadata discovery is disabled")

        base_url = str(request.base_url).rstrip("/")
        return {
            "name": config.APP_NAME,
            "version": config.APP_VERSION,
            "transport": "streamable-http",
            "endpoint": f"{base_url}{config.MCP_PATH}",
            "health_endpoint": f"{base_url}/health",
            "auth_required": config.MCP_REQUIRE_AUTH,
        }

    @api.post("/api/materials/search")
    def materials_search(
        payload: MaterialSearchRequest,
        _auth: str | None = Depends(require_authenticated_user),
        _roles: set[str] = Depends(require_role({"MaterialsReader", "MaterialsEngineer", "MaterialsAdmin"})),
    ):
        return search_material_tool(payload.formula, payload.limit, payload.offset)

    @api.post("/api/materials/advanced-search")
    def materials_advanced_search(
        payload: AdvancedMaterialSearchRequest,
        _auth: str | None = Depends(require_authenticated_user),
        _roles: set[str] = Depends(require_role({"MaterialsReader", "MaterialsEngineer", "MaterialsAdmin"})),
    ):
        return search_materials_advanced_tool(
            query=payload.query,
            formula=payload.formula,
            material_ids=payload.material_ids,
            elements=payload.elements,
            exclude_elements=payload.exclude_elements,
            crystal_system=payload.crystal_system,
            is_stable=payload.is_stable,
            is_metal=payload.is_metal,
            num_elements_min=payload.num_elements.min if payload.num_elements else None,
            num_elements_max=payload.num_elements.max if payload.num_elements else None,
            band_gap_min=payload.band_gap.min if payload.band_gap else None,
            band_gap_max=payload.band_gap.max if payload.band_gap else None,
            density_min=payload.density.min if payload.density else None,
            density_max=payload.density.max if payload.density else None,
            volume_min=payload.volume.min if payload.volume else None,
            volume_max=payload.volume.max if payload.volume else None,
            energy_above_hull_min=payload.energy_above_hull.min if payload.energy_above_hull else None,
            energy_above_hull_max=payload.energy_above_hull.max if payload.energy_above_hull else None,
            bulk_modulus_vrh_min=payload.bulk_modulus_vrh.min if payload.bulk_modulus_vrh else None,
            bulk_modulus_vrh_max=payload.bulk_modulus_vrh.max if payload.bulk_modulus_vrh else None,
            shear_modulus_vrh_min=payload.shear_modulus_vrh.min if payload.shear_modulus_vrh else None,
            shear_modulus_vrh_max=payload.shear_modulus_vrh.max if payload.shear_modulus_vrh else None,
            weighted_surface_energy_min=payload.weighted_surface_energy.min if payload.weighted_surface_energy else None,
            weighted_surface_energy_max=payload.weighted_surface_energy.max if payload.weighted_surface_energy else None,
            work_function_min=payload.work_function.min if payload.work_function else None,
            work_function_max=payload.work_function.max if payload.work_function else None,
            surface_anisotropy_min=payload.surface_anisotropy.min if payload.surface_anisotropy else None,
            surface_anisotropy_max=payload.surface_anisotropy.max if payload.surface_anisotropy else None,
            shape_factor_min=payload.shape_factor.min if payload.shape_factor else None,
            shape_factor_max=payload.shape_factor.max if payload.shape_factor else None,
            limit=payload.limit,
            offset=payload.offset,
        )

    @api.get("/api/materials/{material_id}")
    def materials_by_id(
        material_id: str = Path(
            ...,
            min_length=3,
            max_length=40,
            pattern=r"^mp-[A-Za-z0-9-]+$",
            description="Materials Project material ID, e.g. mp-149",
        ),
        _auth: str | None = Depends(require_authenticated_user),
        _roles: set[str] = Depends(require_role({"MaterialsReader", "MaterialsEngineer", "MaterialsAdmin"})),
    ):
        return get_material_by_id(material_id)

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

    api.mount(config.MCP_PATH, mcp_http_app)
    return api


app = api = create_application()


if __name__ == "__main__":
    if config.MCP_TRANSPORT == "stdio":
        mcp.run()
    else:
        uvicorn.run("app.main:app", host=config.MCP_HOST, port=config.MCP_PORT, reload=False)
