# ASM MCP Materials Platform

Production-ready two-part materials application:

- `app/`: a FastAPI + FastMCP server that remains the main integration layer to Materials Project and related services
- `streamlit_ui/`: a separate Streamlit app that talks to the MCP server over a remote HTTP endpoint

The repo now supports local development, Render deployment for the MCP server, and Streamlit Community Cloud deployment for the UI.

## Architecture

```text
app/                  FastAPI + FastMCP server
streamlit_ui/         Streamlit chat and analysis UI
tests/                Unit tests for server and UI services
render.yaml           Render deployment for the MCP server
requirements.txt      Server/shared dependencies
requirements-streamlit.txt
.env.example
```

## Features

### MCP server

- Keeps the existing Materials Project MCP tool surface
- Adds clean HTTP MCP exposure at `/mcp`
- Keeps `/health` and adds `/.well-known/mcp.json`
- Supports `stdio` and HTTP deployment flows
- Uses environment-variable based configuration only
- Adds structured JSON logging
- Adds retrying HTTP sessions and normalized error responses
- Extends materials querying with advanced search criteria

### Streamlit UI

- Chat-style assistant for natural-language search and lookup
- Direct formula lookup and mp-id lookup
- Explorer page for structured filters
- Compare page for 2 to 5 materials
- Saved queries and recent searches
- Health/debug page with MCP connectivity checks
- CSV and JSON export for result tables

## MCP tools

- `search_material_tool`
- `search_materials_advanced_tool`
- `get_material_by_id_tool`
- `ask_materials_project_tool`
- `run_sql_query`
- `rag_search_tool`

## Environment

Copy the example file first:

```bash
cp .env.example .env
```

Minimum values:

```env
MATERIALS_API_KEY=your_materials_project_key
MATERIALS_API=https://next-gen.materialsproject.org/api
OQMD_REQUIRED=false
MCP_REQUIRE_AUTH=false
MCP_SERVER_URL=http://localhost:8000/mcp
```

Important variables:

- `MATERIALS_API_KEY`: required for Materials Project access
- `MCP_TRANSPORT`: `stdio` for local MCP client usage, `http` for the web server path
- `MCP_HOST` / `MCP_PORT`: HTTP bind settings for the server
- `MCP_SERVER_URL`: Streamlit-side remote MCP endpoint
- `CORS_ALLOWED_ORIGINS`: optional, only needed for browser-based cross-origin clients

## Local development

### 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

### 2. Install server dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the MCP server locally

Recommended local HTTP mode:

```bash
export MCP_TRANSPORT=http
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

You can still run the MCP server over stdio for local MCP client testing:

```bash
export MCP_TRANSPORT=stdio
python -m app.main
```

Useful endpoints:

- `http://localhost:8000/health`
- `http://localhost:8000/mcp`
- `http://localhost:8000/.well-known/mcp.json`
- `http://localhost:8000/docs`

### 4. Run the Streamlit UI locally

Install the UI dependencies:

```bash
pip install -r requirements-streamlit.txt
```

Then run:

```bash
export MCP_SERVER_URL=http://localhost:8000/mcp
streamlit run streamlit_ui/app.py
```

## Sample prompts

- `Find lightweight alloys used in aerospace engineering`
- `Compare silicon and gallium arsenide`
- `Show materials containing Si and O with band gap between 0.5 and 1.0 eV`
- `Find stable cathode materials for batteries`
- `Get properties for mp-149`

## Deployment

### Render for the MCP server

1. Push this repo to GitHub.
2. Create a new Render Web Service from the repo.
3. Render will detect `render.yaml`.
4. Set secrets in Render:
   - `MATERIALS_API_KEY`
   - any optional auth or integration settings you use
5. Deploy.

Expected production endpoint examples:

- `https://your-render-service.onrender.com/health`
- `https://your-render-service.onrender.com/mcp`

### Streamlit Community Cloud for the UI

1. Deploy `streamlit_ui/app.py` as the app entrypoint.
2. Streamlit Community Cloud can use `streamlit_ui/requirements.txt` automatically because it is in the app directory.
3. Add the following secret in the Streamlit app settings:

```toml
MCP_SERVER_URL = "https://your-render-service.onrender.com/mcp"
```

4. Do not use `mcp.json` or local Claude-style MCP config for the UI deployment.

## Testing

Run the unit tests:

```bash
pytest -q
```

Current test coverage includes:

- MCP client retries and caching
- query parsing for chat routing
- result normalization
- existing materials tool behavior

## Notes

- The Streamlit app calls the MCP server remotely over HTTP and does not depend on local MCP client configuration files.
- The MCP server remains the integration boundary to Materials Project.
- OQMD stays optional and can be disabled for simpler deployments.
