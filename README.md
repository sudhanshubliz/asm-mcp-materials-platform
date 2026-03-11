# ASM MCP Materials Platform

Enterprise MCP and API server for materials discovery workflows. The project exposes Materials Project, OQMD, SQL, and RAG capabilities through:

- MCP tools for Claude, Cursor, GitHub Copilot, and other MCP clients
- FastAPI endpoints for direct REST testing

## What the project does

- Queries Materials Project using your API key
- Queries OQMD and returns federated materials results
- Supports natural-language materials prompts through `ask_materials_project_tool`
- Exposes read-only SQL query and RAG search tools
- Provides both `stdio` MCP transport and optional HTTP MCP transport

## Current MCP tools

- `search_material_tool`
- `get_material_by_id_tool`
- `ask_materials_project_tool`
- `run_sql_query`
- `rag_search_tool`

## REST endpoints

- `GET /health`
- `POST /api/materials/search`
- `GET /api/materials/{material_id}`
- `POST /api/sql/query`
- `POST /api/rag/search`

## Prerequisites

- macOS, Linux, or Windows with shell access
- Python `3.10+` and a working virtual environment
- Materials Project API key
- Optional: Node.js if you want to use MCP Inspector
- Optional: Redis, Qdrant, and Azure SQL if you want full non-mocked integrations

## Project structure

- [app/main.py](/Users/sudhanshu_thakur/Documents/workspace/asm-mcp-materials-platform/app/main.py): MCP entrypoint and FastAPI app
- [app/tools/materials_tools.py](/Users/sudhanshu_thakur/Documents/workspace/asm-mcp-materials-platform/app/tools/materials_tools.py): MCP tools
- [app/services/materials_service.py](/Users/sudhanshu_thakur/Documents/workspace/asm-mcp-materials-platform/app/services/materials_service.py): Materials Project integration
- [app/services/oqmd_service.py](/Users/sudhanshu_thakur/Documents/workspace/asm-mcp-materials-platform/app/services/oqmd_service.py): OQMD integration
- [tests/](/Users/sudhanshu_thakur/Documents/workspace/asm-mcp-materials-platform/tests): unit tests

## Installation

Create and activate a virtual environment:

```bash
cd /Users/sudhanshu_thakur/Documents/workspace/asm-mcp-materials-platform
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

## Configuration

Create local environment configuration:

```bash
cp .env.example .env
```

Minimum useful `.env` values:

```env
MATERIALS_API_KEY=replace_with_new_key
MATERIALS_API=https://next-gen.materialsproject.org/api
MATERIALS_API_MODE=auto
OQMD_API=https://oqmd.org/api
OQMD_RESOURCE=formationenergy
OQMD_REQUIRED=true
SQL_CONNECTION=sqlite+pysqlite:///:memory:
MCP_REQUIRE_AUTH=false
```

Key environment variables:

- `MATERIALS_API_KEY`: required for Materials Project access
- `MATERIALS_API`: Materials Project base URL
- `MATERIALS_API_MODE`: `auto`, `rest`, or `mp_api`
- `OQMD_API`: OQMD base URL
- `OQMD_RESOURCE`: OQMD resource path, currently `formationenergy`
- `OQMD_REQUIRED`: when `true`, federated search includes OQMD
- `MCP_REQUIRE_AUTH`: when `false`, local testing is easier

## Running locally

Run the MCP server over `stdio` for Claude, Cursor, and Copilot:

```bash
source .venv/bin/activate
python -m app.main
```

Run the REST API locally:

```bash
source .venv/bin/activate
python -m uvicorn app.main:api --host 127.0.0.1 --port 8001
```

Run MCP over HTTP only if you explicitly need it:

```bash
export MCP_TRANSPORT=http
export MCP_PORT=8000
python -m app.main
```

## Testing

Run unit tests:

```bash
source .venv/bin/activate
pytest -q
```

Test REST endpoints:

```bash
curl -sS http://127.0.0.1:8001/health
```

```bash
curl -sS -X POST http://127.0.0.1:8001/api/materials/search \
  -H "Content-Type: application/json" \
  -d '{"formula":"Fe2O3","limit":5,"offset":0}'
```

```bash
curl -sS http://127.0.0.1:8001/api/materials/mp-csvwu
```

Swagger UI:

- [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)
- [http://127.0.0.1:8001/redoc](http://127.0.0.1:8001/redoc)

## MCP Inspector

Use the bundled launcher:

```bash
./scripts/run_mcp_inspector.sh
```

This starts Inspector against:

- command: `.venv/bin/python`
- args: `-m app.main`

## Claude Desktop setup

Claude Desktop config file on macOS:

- `~/Library/Application Support/Claude/claude_desktop_config.json`

Example:

```json
{
  "mcpServers": {
    "materials-platform": {
      "command": "/Users/sudhanshu_thakur/Documents/workspace/asm-mcp-materials-platform/.venv/bin/python",
      "args": ["-m", "app.main"],
      "env": {
        "PYTHONPATH": "/Users/sudhanshu_thakur/Documents/workspace/asm-mcp-materials-platform",
        "MATERIALS_API_KEY": "YOUR_ROTATED_KEY",
        "MATERIALS_API": "https://next-gen.materialsproject.org/api",
        "OQMD_API": "https://oqmd.org/api",
        "OQMD_RESOURCE": "formationenergy",
        "OQMD_REQUIRED": "true",
        "MCP_REQUIRE_AUTH": "false"
      }
    }
  }
}
```

After editing:

1. Quit Claude Desktop fully.
2. Reopen Claude Desktop.
3. Ask Claude to call one of the MCP tools directly.

Example Claude prompts:

- `Call get_material_by_id_tool with material_id "mp-csvwu"`
- `Call ask_materials_project_tool with question "Retrieve full structural and electronic properties for material Dy"`

## Cursor setup

Cursor MCP config can be placed either globally or per-project:

- `~/.cursor/mcp.json`
- `/Users/sudhanshu_thakur/Documents/workspace/asm-mcp-materials-platform/.cursor/mcp.json`

Example:

```json
{
  "mcpServers": {
    "materials-platform": {
      "command": "/Users/sudhanshu_thakur/Documents/workspace/asm-mcp-materials-platform/.venv/bin/python",
      "args": ["-m", "app.main"],
      "cwd": "/Users/sudhanshu_thakur/Documents/workspace/asm-mcp-materials-platform",
      "env": {
        "MATERIALS_API_KEY": "YOUR_ROTATED_KEY",
        "MATERIALS_API": "https://next-gen.materialsproject.org/api",
        "OQMD_API": "https://oqmd.org/api",
        "OQMD_RESOURCE": "formationenergy",
        "OQMD_REQUIRED": "true",
        "MCP_REQUIRE_AUTH": "false"
      }
    }
  }
}
```

After editing:

1. Quit Cursor fully.
2. Reopen Cursor.
3. Verify the MCP server appears in Cursor MCP settings.

## GitHub Copilot setup

GitHub Copilot MCP support depends on the host application. Use the same server command:

```json
{
  "mcpServers": {
    "materials-platform": {
      "command": "/Users/sudhanshu_thakur/Documents/workspace/asm-mcp-materials-platform/.venv/bin/python",
      "args": ["-m", "app.main"]
    }
  }
}
```

For GitHub Copilot:

1. Open the MCP configuration UI or settings entry provided by your Copilot host.
2. Add a new MCP server named `materials-platform`.
3. Use the command and args shown above.
4. Add the required environment variables from `.env`.
5. Restart the host if the MCP tools do not appear immediately.

For current host-specific details, use the official GitHub Copilot MCP docs:

- [GitHub Copilot MCP documentation](https://docs.github.com/copilot)

## Example MCP prompts

Natural language tool prompt:

```text
Call ask_materials_project_tool with question "Retrieve full structural and electronic properties for material Dy"
```

Examples supported by the unified materials tool:

- `Pull materials where shear modulus VRH is above 80 and density is below 6`
- `List materials where weighted surface energy is low and predicted_stable = true`
- `Find materials with work function between 4.5 and 5.5`
- `List materials with cubic and show their space group symbol, space group number`
- `Find materials with vol >200 and dens <3`
- `Retrieve materials for hexagonal with band gap above 2`
- `Browse materials with high surface anisotropy and shape factor >1.2`

## Troubleshooting

- If Claude or Cursor connects and immediately disconnects, confirm you are running `stdio` transport, not forced `http`.
- If Materials Project returns `403`, use `MATERIALS_API_MODE=mp_api` or `auto`.
- If `ModuleNotFoundError: app` appears in Claude, add `PYTHONPATH` to the MCP client env.
- If OQMD is slow or unavailable, set `OQMD_REQUIRED=false`.
- If the server prints secrets in local config files or logs, rotate the API key.

## Security notes

- Do not commit `.env`
- Do not hardcode API keys into `mcp.json`, `claude_desktop_config.json`, or screenshots
- Rotate any Materials Project key that has been shared in chat, logs, or config history
