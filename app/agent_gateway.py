from fastapi import FastAPI
import requests

app = FastAPI()

MCP_URL = "http://localhost:8000/mcp"

@app.post("/search-material")
def search_material(formula: str):

    payload = {
        "jsonrpc": "2.0",
        "method": "tools.call",
        "params": {
            "name": "search_material_tool",
            "arguments": {
                "formula": formula
            }
        }
    }

    r = requests.post(MCP_URL, json=payload)

    return r.json()