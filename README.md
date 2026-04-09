# ASM MCP Materials Platform

Production-ready two-part application for Materials Project workflows:

- an MCP server in `app/`
- a Streamlit client in `streamlit_ui/`

The backend stays the integration layer to Materials Project. The Streamlit app talks to that backend over a remote MCP HTTP endpoint and does not use a local desktop `mcp.json`.

## Live Deployments

Current hosted endpoints:

- Render MCP server: [https://asm-mcp-materials-platform.onrender.com](https://asm-mcp-materials-platform.onrender.com)
- MCP endpoint: [https://asm-mcp-materials-platform.onrender.com/mcp](https://asm-mcp-materials-platform.onrender.com/mcp)
- Health: [https://asm-mcp-materials-platform.onrender.com/health](https://asm-mcp-materials-platform.onrender.com/health)
- MCP metadata: [https://asm-mcp-materials-platform.onrender.com/.well-known/mcp.json](https://asm-mcp-materials-platform.onrender.com/.well-known/mcp.json)
- Streamlit app: [https://asm-mcp-materials-platform.streamlit.app](https://asm-mcp-materials-platform.streamlit.app)

## What This Repo Does

- exposes Materials Project data through reusable MCP tools
- serves MCP over HTTP at `/mcp`
- provides a Streamlit chat UI for search, lookup, comparison, and export
- supports separate deployment for backend and frontend
- keeps configuration environment-variable based only
- includes caching, retries, normalized schemas, and tests

## Architecture

```text
User
  -> Streamlit UI
  -> MCP client over HTTP
  -> Render or local MCP server (/mcp)
  -> MCP tools
  -> Materials Project API
```

Important design rules in this repo:

- the MCP server is the only integration boundary to Materials Project
- the Streamlit app is a remote MCP client
- the Streamlit app must use `MCP_SERVER_URL`
- the Streamlit app must not depend on Claude Desktop or `mcp.json`

## Repository Layout

```text
app/                         FastAPI app + FastMCP server + MCP tools
streamlit_ui/                Streamlit app, pages, services, utilities
tests/                       Unit tests for client, parsing, normalization
render.yaml                  Render deployment config
requirements.txt             Full local development dependencies
requirements-render.txt      Lean backend dependency set for Render
requirements-streamlit.txt   Streamlit dependency set
streamlit_ui/requirements.txt  Streamlit Cloud entry requirements file
.env.example                 Environment template
```

## MCP Server Features

- HTTP MCP endpoint at `/mcp`
- health check at `/health`
- discovery metadata at `/.well-known/mcp.json`
- FastAPI REST helpers under `/api/...`
- structured logging
- graceful error envelopes
- retries for upstream HTTP requests
- normalized material result schema
- cache support
- environment-only configuration

Core MCP tools:

- `search_material_tool`
- `search_materials_advanced_tool`
- `get_material_by_id_tool`
- `ask_materials_project_tool`
- `run_sql_query`
- `rag_search_tool`

## Streamlit UI Features

- chat-style materials assistant
- natural-language search
- formula lookup like `Fe2O3`, `LiFePO4`, `TiO2`
- mp-id lookup like `mp-149`
- element and property range filtering
- compare flow for 2 to 5 materials
- CSV and JSON export
- recent searches and saved queries
- connection status and debug page
- remote MCP health awareness

## Local vs Remote MCP

There are two valid development modes.

### Local MCP server

Use this when you are changing backend code or testing locally.

Endpoints:

- `http://localhost:8000/mcp`
- `http://localhost:8000/health`
- `http://localhost:8000/.well-known/mcp.json`

### Remote MCP server on Render

Use this when:

- Streamlit Community Cloud needs a public MCP endpoint
- you want a stable hosted demo
- frontend and backend should deploy independently

Example:

- `https://your-render-service.onrender.com/mcp`

Current deployment:

- `https://asm-mcp-materials-platform.onrender.com/mcp`

## Environment Variables

Copy the template first:

```bash
cp .env.example .env
```

Included template:

```env
MATERIALS_API_KEY=
MATERIALS_API=https://next-gen.materialsproject.org/api
MATERIALS_SUMMARY_PATH=/materials/summary
MATERIALS_API_KEY_HEADER=X-API-KEY
MATERIALS_API_MODE=auto
OQMD_REQUIRED=false
MCP_REQUIRE_AUTH=false
MCP_SERVER_URL=http://localhost:8000/mcp

# Optional
OQMD_API=https://oqmd.org/api
OQMD_RESOURCE=formationenergy
SQL_CONNECTION=sqlite+pysqlite:///:memory:
MCP_TRANSPORT=http
MCP_HOST=0.0.0.0
MCP_PORT=8000
LOG_LEVEL=INFO
REQUEST_TIMEOUT=30
REQUEST_RETRY_ATTEMPTS=3
REQUEST_RETRY_BACKOFF=0.5
CACHE_TTL_SECONDS=3600
```

### Required backend variables

- `MATERIALS_API_KEY`
- `MATERIALS_API`
- `MATERIALS_API_MODE`
- `MCP_TRANSPORT`
- `MCP_HOST`
- `MCP_PORT`

### Common backend variables

- `MATERIALS_SUMMARY_PATH`
- `MATERIALS_API_KEY_HEADER`
- `MCP_REQUIRE_AUTH`
- `MCP_PUBLISH_METADATA`
- `OQMD_REQUIRED`
- `SQL_CONNECTION`
- `LOG_LEVEL`
- `REQUEST_TIMEOUT`
- `REQUEST_RETRY_ATTEMPTS`
- `REQUEST_RETRY_BACKOFF`
- `CACHE_TTL_SECONDS`
- `CORS_ALLOWED_ORIGINS`

### Streamlit variables

- `MCP_SERVER_URL`
- `MCP_AUTH_TOKEN` if auth is enabled on the MCP server

Important:

- Streamlit reads `MCP_SERVER_URL`
- Streamlit does not read `mcp.json`
- Streamlit Community Cloud should use Secrets, not local desktop MCP config

## Install Dependencies

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

Install all local development dependencies:

```bash
pip install -r requirements.txt
pip install -r requirements-streamlit.txt
```

## Run Locally

### 1. Start the MCP server

```bash
export MCP_TRANSPORT=http
export MCP_HOST=0.0.0.0
export MCP_PORT=8000
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Local backend URLs:

- [http://localhost:8000](http://localhost:8000)
- [http://localhost:8000/health](http://localhost:8000/health)
- [http://localhost:8000/.well-known/mcp.json](http://localhost:8000/.well-known/mcp.json)
- [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Start Streamlit against local MCP

```bash
export MCP_SERVER_URL=http://localhost:8000/mcp
streamlit run streamlit_ui/app.py
```

### 3. Start Streamlit against Render MCP

```bash
export MCP_SERVER_URL=https://asm-mcp-materials-platform.onrender.com/mcp
streamlit run streamlit_ui/app.py
```

Recommended local workflow:

1. Run the MCP server locally.
2. Run Streamlit locally.
3. Test against `localhost`.
4. Deploy the backend to Render.
5. Point `MCP_SERVER_URL` to the Render URL.
6. Deploy Streamlit separately.

## Streamlit Remote MCP Integration

The Streamlit app uses `streamlit_ui/services/mcp_client.py` to talk to MCP over HTTP.

It supports:

- `MCP_SERVER_URL` via env var or Streamlit secret
- health probing
- retries
- timeout handling
- cached repeated tool calls
- response normalization before rendering

Default behavior:

- use `MCP_SERVER_URL` if set
- otherwise probe local MCP
- otherwise fall back to the hosted Render MCP endpoint

### Streamlit Community Cloud configuration

Repository settings:

- repo: `sudhanshubliz/asm-mcp-materials-platform`
- branch: `main`
- main file path: `streamlit_ui/app.py`

Streamlit Cloud installs:

- `streamlit_ui/requirements.txt`

That file points to:

- `requirements-streamlit.txt`

Add these secrets in Streamlit Cloud:

```toml
MCP_SERVER_URL = "https://asm-mcp-materials-platform.onrender.com/mcp"
```

Optional:

```toml
MCP_AUTH_TOKEN = "your-token"
```

## Deploy MCP Server to Render

This repo includes a Render-ready config:

- `render.yaml`
- lean backend dependencies in `requirements-render.txt`

Why a separate Render requirements file exists:

- to keep deployment memory lower
- to avoid installing Streamlit-only packages
- to avoid pulling heavier optional local packages unless the backend needs them

Current `render.yaml` service name:

- `mcp_connect`

Build/start commands:

```text
Build: pip install --upgrade pip && pip install --no-cache-dir -r requirements-render.txt
Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Minimum Render environment variables

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

Then point Streamlit to:

```text
https://your-render-service.onrender.com/mcp
```

## Deploy Streamlit to Streamlit Community Cloud

1. Connect the GitHub repo.
2. Set the main file to `streamlit_ui/app.py`.
3. Let Streamlit Cloud install `streamlit_ui/requirements.txt`.
4. Add `MCP_SERVER_URL` in Streamlit Secrets.
5. Redeploy.

Do not upload a local `mcp.json`.

## Testing

Run the test suite:

```bash
pytest -q
```

Important test coverage includes:

- MCP client behavior
- query parsing
- result normalization

Useful local checks:

```bash
python -m compileall streamlit_ui
python -m compileall app
```

## Sample Prompts

- `Find lightweight alloys used in aerospace engineering`
- `Compare silicon and gallium arsenide`
- `Show materials containing Si and O with band gap between 0.5 and 1.0 eV`
- `Find stable cathode materials for batteries`
- `Get properties for mp-149`

## Manual Endpoint Checks

### Check backend health

```bash
curl https://asm-mcp-materials-platform.onrender.com/health
```

### Check MCP metadata

```bash
curl https://asm-mcp-materials-platform.onrender.com/.well-known/mcp.json
```

### Check a REST helper route

```bash
curl -X POST https://asm-mcp-materials-platform.onrender.com/api/materials/search \
  -H "Content-Type: application/json" \
  -d '{"formula":"Fe2O3","limit":3,"offset":0}'
```

## Troubleshooting

### Browser opening `/mcp` returns an error

This is expected.

`/mcp` is a Streamable HTTP MCP endpoint, not a normal JSON REST route. If you open it directly in a browser or use a client that does not accept MCP streaming, you may see errors like:

- `Client must accept text/event-stream`
- `Missing session ID`

Use:

- `/health` for health checks
- `/.well-known/mcp.json` for discovery
- an MCP-aware client for `/mcp`

### Streamlit says `ModuleNotFoundError: No module named 'streamlit_ui'`

This usually happens when Streamlit Cloud runs `streamlit_ui/app.py` directly and package paths are not set correctly. The app already includes the needed path bootstrap. Redeploy from the latest `main`.

### Streamlit says `Could not find page: streamlit_ui/app.py`

This happens when `st.switch_page()` uses the wrong path. The correct home page reference is:

```text
app.py
```

not:

```text
streamlit_ui/app.py
```

### Streamlit says `Tool call failed ... All connection attempts failed`

Usually one of these is true:

- `MCP_SERVER_URL` is missing in Streamlit secrets
- Streamlit is trying `localhost` in the cloud
- the Render backend is not healthy

Recommended secret:

```toml
MCP_SERVER_URL = "https://asm-mcp-materials-platform.onrender.com/mcp"
```

### Streamlit says `cannot be modified after the widget ... is instantiated`

This is a Streamlit widget state timing issue. The app uses a queued prompt flow with `pending_prompt` to avoid mutating text-input state after render. If you see this again, redeploy from the latest `main`.

### Streamlit shows `localhost:8501/healthz connection refused`

This usually appears briefly during app startup on Streamlit Cloud while the process is still initializing. If the app comes up afterward, this is not the real failure.

### Render returns `502 Bad Gateway`

Common causes:

- Materials Project API key is missing or invalid
- Render is cold-starting or mid-redeploy
- upstream Materials Project call failed
- backend tool execution failed and bubbled up through MCP

Check:

- backend `/health`
- backend `/.well-known/mcp.json`
- Render logs
- `MATERIALS_API_KEY`

### OQMD failures appear in logs

Set:

```env
OQMD_REQUIRED=false
```

unless you explicitly need OQMD federation.

## Dependency Notes

- `requirements.txt` is for full local development
- `requirements-render.txt` is for lean backend deployment
- `requirements-streamlit.txt` is for Streamlit runtime
- `streamlit_ui/requirements.txt` exists because Streamlit Cloud looks for requirements near the app entrypoint

## Security Notes

- never hardcode Materials Project credentials
- use Render env vars for backend secrets
- use Streamlit Cloud Secrets for frontend secrets
- if an API key was ever pasted into chat or logs, rotate it

## Summary

Use the backend as the single Materials Project integration layer, deploy it separately on Render, and point the Streamlit app at the MCP endpoint with `MCP_SERVER_URL`. For local work, run both parts on your machine. For hosted use, keep Streamlit on Streamlit Community Cloud and the MCP server on Render.
