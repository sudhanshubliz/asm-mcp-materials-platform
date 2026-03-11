# ASM MCP Materials Platform

Production-oriented MCP server scaffold for AI-driven materials discovery with Copilot.

## What this implements

- `FastMCP` server with tools:
  - `search_material_tool`
  - `run_sql_query`
  - `rag_search_tool`
- `FastAPI` service endpoints for API-style access.
- Services for Materials Project, OQMD, SQL, and RAG (Qdrant + embeddings).
- Azure AD token helper and role-based request guards.
- Input validation via Pydantic schemas.
- Read-only SQL safety checks (SELECT/CTE only, limited rows).
- Redis cache with in-memory fallback when Redis is unavailable.

## Project layout

- `app/main.py`: MCP + API entrypoints
- `app/tools/`: MCP-callable tools
- `app/services/`: external/internal data access
- `app/models/`: request schemas and validation
- `app/cache/`: Redis cache abstraction
- `tests/`: unit tests

## Environment variables

- `SQL_CONNECTION_STRING` or `SQL_CONNECTION`
- `MATERIALS_API` (default: `https://next-gen.materialsproject.org/api`)
- `MATERIALS_SUMMARY_PATH` (default: `/materials/summary`)
- `MATERIALS_API_KEY`
- `MATERIALS_API_KEY_HEADER` (default: `X-API-KEY`)
- `MATERIALS_API_MODE` (`auto`/`rest`/`mp_api`, default: `auto`)
- `OQMD_API` (default: `https://oqmd.org/api`)
- `OQMD_RESOURCE` (default: `formationenergy`)
- `OQMD_REQUIRED` (`true` by default; set `false` to skip OQMD)
- `REDIS_HOST`
- `REDIS_PORT`
- `VECTOR_DB`
- `RAG_COLLECTION`
- `RAG_TOP_K`
- `REQUEST_TIMEOUT`
- `SQL_MAX_ROWS`
- `MCP_REQUIRE_AUTH` (`true`/`false`)
- `ALLOWED_ROLES` (comma-separated)

## Run locally

```bash
pip install -r requirements.txt
python app/main.py
```

You can keep local configuration in `.env` (auto-loaded):

```bash
cp .env.example .env
```

## Materials Project API key setup

Set your key as an environment variable (do not hardcode in source):

```bash
export MATERIALS_API_KEY="<your_api_key>"
```

The integration uses the official `mp-api` Python client (required by Materials Project).
Install dependencies again after pulling latest changes:

```bash
pip install -r requirements.txt
```

Optional legacy endpoint vars (kept for compatibility):

```bash
export MATERIALS_API="https://next-gen.materialsproject.org/api"
export MATERIALS_SUMMARY_PATH="/materials/summary"
export MATERIALS_API_KEY_HEADER="X-API-KEY"
export MATERIALS_API_MODE="auto"
export OQMD_API="https://oqmd.org/api"
export OQMD_RESOURCE="formationenergy"
export OQMD_REQUIRED="true"
```

## Test

```bash
pytest
```

## MCP Inspector (local tool testing)

Use MCP Inspector to test MCP tools interactively.

Prerequisites:
- Node.js installed (`npx` available)
- `.venv` created with dependencies installed
- `MATERIALS_API_KEY` set in `.env` or exported in shell

Run:

```bash
./scripts/run_mcp_inspector.sh
```

This launches MCP Inspector and connects to:
- command: `.venv/bin/python`
- args: `-m app.main`

## API examples

```bash
curl -sS http://127.0.0.1:8001/api/materials/mp-csvwu
```

## Docker

```bash
docker compose up --build
```
