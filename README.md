# ASM MCP Materials Platform

Production-ready two-part application for Materials Project workflows:

- `app/`: the MCP server and HTTP API layer
- `streamlit_ui/`: the Streamlit chat and dashboard UI

The key design rule in this repo is:

- the MCP server is the integration boundary to Materials Project
- the Streamlit app is a remote MCP client
- the Streamlit app does **not** use local `mcp.json` or Claude-style desktop MCP config

## What This Repo Contains

```text
app/                         MCP server + FastAPI app
streamlit_ui/                Streamlit UI that calls MCP over HTTP
tests/                       Unit tests
render.yaml                  Render deployment config
requirements.txt             Full local/server dependency set
requirements-render.txt      Lean Render dependency set
requirements-streamlit.txt   Streamlit dependency set
.env.example                 Local env template
```

## Architecture

```text
User -> Streamlit UI -> Remote MCP endpoint (/mcp) -> MCP tools -> Materials Project API
```

There are two ways to run the MCP server:

1. Local MCP server
   Use this during development when Streamlit runs on your machine and talks to `http://localhost:8000/mcp`

2. Remote MCP server on Render
   Use this for hosted Streamlit, shared demos, and production-style deployments

## Core MCP Tools

- `search_material_tool`
- `search_materials_advanced_tool`
- `get_material_by_id_tool`
- `ask_materials_project_tool`
- `run_sql_query`
- `rag_search_tool`

## Streamlit UI Features

- chat-style assistant for natural language materials queries
- direct formula lookup like `Fe2O3`, `TiO2`, `LiFePO4`
- direct mp-id lookup like `mp-149`
- structured explorer filters
- compare view for 2 to 5 materials
- saved queries and recent searches
- MCP connection health/debug page
- CSV and JSON export

## MCP Server Features

- clean HTTP MCP endpoint at `/mcp`
- health endpoint at `/health`
- discovery metadata at `/.well-known/mcp.json`
- structured logging
- retry-aware upstream calls
- normalized materials schemas
- environment-variable based configuration only

## Local Vs Remote MCP Server

### Local MCP server

Use local mode when:

- you are developing the backend
- you want Streamlit to talk to `localhost`
- you want to test changes before pushing to GitHub

Local MCP endpoint:

```text
http://localhost:8000/mcp
```

Health endpoint:

```text
http://localhost:8000/health
```

### Remote MCP server on Render

Use remote mode when:

- you want a hosted MCP endpoint
- Streamlit Community Cloud needs a public MCP URL
- you want the UI and backend deployed separately

Remote MCP endpoint example:

```text
https://your-render-service.onrender.com/mcp
```

Health endpoint example:

```text
https://your-render-service.onrender.com/health
```

Discovery metadata example:

```text
https://your-render-service.onrender.com/.well-known/mcp.json
```

## Environment Variables

Copy the example first:

```bash
cp .env.example .env
```

Important variables:

```env
MATERIALS_API_KEY=
MATERIALS_API=https://next-gen.materialsproject.org/api
OQMD_REQUIRED=false
MCP_REQUIRE_AUTH=false
MCP_SERVER_URL=http://localhost:8000/mcp
```

### MCP server env vars

- `MATERIALS_API_KEY`
  Required for Materials Project access
- `MATERIALS_API`
  Materials Project base API URL
- `MATERIALS_SUMMARY_PATH`
  Summary endpoint path for REST mode
- `MATERIALS_API_KEY_HEADER`
  Header used for the Materials Project key
- `MATERIALS_API_MODE`
  `auto`, `rest`, or `mp_api`
- `MCP_TRANSPORT`
  `stdio` or `http`
- `MCP_HOST`
  bind host for HTTP mode
- `MCP_PORT`
  bind port for HTTP mode
- `MCP_REQUIRE_AUTH`
  enable auth checks if needed
- `OQMD_REQUIRED`
  turn OQMD federation on or off
- `SQL_CONNECTION`
  SQL backend connection string
- `LOG_LEVEL`
  server logging level
- `REQUEST_TIMEOUT`
  upstream HTTP timeout in seconds
- `REQUEST_RETRY_ATTEMPTS`
  retry count for upstream HTTP calls
- `REQUEST_RETRY_BACKOFF`
  retry backoff factor
- `CACHE_TTL_SECONDS`
  cache TTL in seconds

### Streamlit UI env vars

- `MCP_SERVER_URL`
  The remote MCP endpoint the UI should call
- `MCP_AUTH_TOKEN`
  Optional bearer token if your MCP server is protected

Important:

- Streamlit uses `MCP_SERVER_URL`
- Streamlit does **not** use `mcp.json`
- Streamlit Community Cloud should use secrets or env vars, not local desktop MCP config

## Run Locally

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

### 2. Install local dependencies

For full local development:

```bash
pip install -r requirements.txt
pip install -r requirements-streamlit.txt
```

### 3. Run the MCP server locally over HTTP

```bash
export MCP_TRANSPORT=http
export MCP_HOST=0.0.0.0
export MCP_PORT=8000
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Local MCP server URLs:

- `http://localhost:8000/health`
- `http://localhost:8000/mcp`
- `http://localhost:8000/.well-known/mcp.json`
- `http://localhost:8000/docs`

### 4. Run the Streamlit UI against the local MCP server

```bash
export MCP_SERVER_URL=http://localhost:8000/mcp
streamlit run streamlit_ui/app.py
```

This is the recommended local developer workflow:

1. run the MCP server locally
2. run Streamlit locally
3. verify the UI is calling `localhost`
4. deploy the MCP server to Render
5. switch `MCP_SERVER_URL` to the Render URL
6. deploy Streamlit separately

## Streamlit Remote MCP Integration

The Streamlit app is built to call a remote MCP endpoint directly:

- it reads `MCP_SERVER_URL`
- it connects to the MCP server over HTTP
- it lists tools and calls tools remotely
- it normalizes tool responses before rendering

### Local Streamlit -> Local MCP

```env
MCP_SERVER_URL=http://localhost:8000/mcp
```

### Local Streamlit -> Remote Render MCP

```env
MCP_SERVER_URL=https://your-render-service.onrender.com/mcp
```

### Streamlit Community Cloud -> Remote Render MCP

Use Streamlit secrets:

```toml
MCP_SERVER_URL = "https://your-render-service.onrender.com/mcp"
```

Optional:

```toml
MCP_AUTH_TOKEN = "your-token-if-enabled"
```

## Deploy MCP Server To Render

This repo includes both:

- `render.yaml`
- a lean Docker path via `Dockerfile` + `requirements-render.txt`

The Render deployment is intentionally slimmed down so the server does not install heavy optional local-only UI or ML dependencies unless required.

### Recommended Render setup

1. Create a Render Web Service from this GitHub repo
2. Use the repo root as the service root
3. Let Render build from the included Dockerfile
4. Set the required environment variables

### Minimum Render env vars

```env
MATERIALS_API_KEY=your_materials_project_key
MATERIALS_API=https://next-gen.materialsproject.org/api
MATERIALS_API_MODE=auto
MCP_TRANSPORT=http
MCP_HOST=0.0.0.0
MCP_REQUIRE_AUTH=false
OQMD_REQUIRED=false
SQL_CONNECTION=sqlite+pysqlite:///:memory:
LOG_LEVEL=INFO
REQUEST_TIMEOUT=30
REQUEST_RETRY_ATTEMPTS=3
REQUEST_RETRY_BACKOFF=0.5
CACHE_TTL_SECONDS=3600
```

### After Render deploys

Verify:

```bash
curl https://your-render-service.onrender.com/health
curl https://your-render-service.onrender.com/.well-known/mcp.json
```

Expected MCP endpoint:

```text
https://your-render-service.onrender.com/mcp
```

## Deploy Streamlit To Streamlit Community Cloud

1. Use `streamlit_ui/app.py` as the app entrypoint
2. Ensure Streamlit sees `streamlit_ui/requirements.txt`
3. Add secrets in Streamlit:

```toml
MCP_SERVER_URL = "https://your-render-service.onrender.com/mcp"
```

4. If server auth is enabled, also add:

```toml
MCP_AUTH_TOKEN = "your-token"
```

5. Deploy

Important:

- do not configure Streamlit with `mcp.json`
- do not use Claude Desktop MCP config for Streamlit
- Streamlit is just an HTTP client to the remote MCP service

## Sample Prompts

- `Find lightweight alloys used in aerospace engineering`
- `Compare silicon and gallium arsenide`
- `Show materials containing Si and O with band gap between 0.5 and 1.0 eV`
- `Find stable cathode materials for batteries`
- `Get properties for mp-149`

## Testing

Run:

```bash
pytest -q
```

Current coverage includes:

- MCP client retry and caching behavior
- query parsing
- result normalization
- server tool behavior

## Practical Deployment Pattern

### Option A: local dev

- MCP server: local
- Streamlit: local
- `MCP_SERVER_URL=http://localhost:8000/mcp`

### Option B: backend on Render, UI local

- MCP server: Render
- Streamlit: local
- `MCP_SERVER_URL=https://your-render-service.onrender.com/mcp`

### Option C: backend on Render, UI on Streamlit Cloud

- MCP server: Render
- Streamlit: Streamlit Community Cloud
- Streamlit secret `MCP_SERVER_URL=https://your-render-service.onrender.com/mcp`

## Notes

- the MCP server remains the single backend integration layer
- the Streamlit app is a separate deployable client
- OQMD is optional and can stay disabled for simpler deployments
- `stdio` MCP mode is for local MCP desktop/tool clients, not for Streamlit remote integration
