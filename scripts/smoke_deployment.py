from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from typing import Any


CANONICAL_MP_ID = re.compile(r"^mp-\d+$")
DEFAULT_BASE_URL = "https://asm-mcp-materials-platform.onrender.com"


def _request_json(base_url: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        headers={"Content-Type": "application/json"} if body else {},
        method="POST" if body else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"{path} returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{path} could not be reached: {exc.reason}") from exc


def run_smoke_checks(base_url: str) -> None:
    health = _request_json(base_url, "/health")
    if health.get("status") != "ok":
        raise RuntimeError(f"Backend health is not OK: {health}")

    material = _request_json(base_url, "/api/materials/mp-149")
    if material.get("material_id") != "mp-149":
        raise RuntimeError(f"mp-149 identity was not preserved: {material.get('material_id')!r}")

    search = _request_json(
        base_url,
        "/api/materials/ask",
        {"question": "Find lightweight alloys used in aerospace engineering", "limit": 5, "offset": 0},
    )
    records = search.get("data") or []
    invalid_ids = [
        record.get("material_id")
        for record in records
        if not CANONICAL_MP_ID.fullmatch(str(record.get("material_id") or ""))
    ]
    if not records or invalid_ids:
        raise RuntimeError(f"Aerospace search returned missing or invalid material IDs: {invalid_ids}")

    qdrant = _request_json(base_url, "/api/rag/health")
    if not qdrant.get("ok") or int(qdrant.get("points_count") or 0) <= 0:
        raise RuntimeError(f"Qdrant is not ready or the collection is empty: {qdrant}")

    neighbors = _request_json(
        base_url,
        "/api/rag/search",
        {"question": "lightweight aerospace alloys", "top_k": 3},
    )
    matches = neighbors.get("data") or []
    if not matches or not any(str(match.get("text") or "").strip() for match in matches):
        raise RuntimeError("Nearest-neighbor search returned no readable text chunks")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the deployed materials platform end to end.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()
    run_smoke_checks(args.base_url)
    print(f"Deployment smoke checks passed for {args.base_url}")


if __name__ == "__main__":
    main()
