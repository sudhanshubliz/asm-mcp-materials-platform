from __future__ import annotations

import argparse
import json
import os
import uuid
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient, models


DEFAULT_INPUT = Path(__file__).resolve().parents[1] / "data" / "materials_papers_seed.jsonl"
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_VECTOR_SIZE = 384


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            text = str(record.get("text", "")).strip()
            if not text:
                raise ValueError(f"{path}:{line_number} is missing non-empty text")
            records.append(record)
    return records


def _point_id(record: dict[str, Any], namespace: uuid.UUID) -> str:
    raw_id = str(record.get("id") or record["text"][:80])
    return str(uuid.uuid5(namespace, raw_id))


def _ensure_collection(client: QdrantClient, collection_name: str, vector_size: int) -> None:
    collections = {collection.name for collection in client.get_collections().collections}
    if collection_name in collections:
        return

    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
    )


def ingest(
    *,
    qdrant_url: str,
    qdrant_api_key: str,
    collection_name: str,
    input_path: Path,
    model_name: str,
    vector_size: int,
) -> int:
    client = QdrantClient(
        url=qdrant_url,
        api_key=qdrant_api_key,
        cloud_inference=True,
        timeout=60,
    )
    _ensure_collection(client, collection_name, vector_size)

    records = _read_jsonl(input_path)
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, f"{qdrant_url}/{collection_name}")
    points = []
    for record in records:
        text = str(record["text"]).strip()
        payload = {
            "text": text,
            "title": record.get("title", ""),
            "source": record.get("source", str(input_path)),
            "topics": record.get("topics", []),
        }
        points.append(
            models.PointStruct(
                id=_point_id(record, namespace),
                vector=models.Document(text=text, model=model_name),
                payload=payload,
            )
        )

    client.upsert(collection_name=collection_name, points=points, wait=True)
    return len(points)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest text chunks into a Qdrant collection.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--collection", default=os.getenv("QDRANT_COLLECTION", "materials_papers"))
    parser.add_argument("--url", default=os.getenv("QDRANT_URL", ""))
    parser.add_argument("--api-key", default=os.getenv("QDRANT_API_KEY", ""))
    parser.add_argument("--model", default=os.getenv("QDRANT_INFERENCE_MODEL", DEFAULT_MODEL))
    parser.add_argument("--vector-size", type=int, default=DEFAULT_VECTOR_SIZE)
    args = parser.parse_args()

    if not args.url:
        raise SystemExit("QDRANT_URL is required")
    if not args.api_key:
        raise SystemExit("QDRANT_API_KEY is required")

    count = ingest(
        qdrant_url=args.url,
        qdrant_api_key=args.api_key,
        collection_name=args.collection,
        input_path=args.input,
        model_name=args.model,
        vector_size=args.vector_size,
    )
    print(f"Ingested {count} text chunks into {args.collection}")


if __name__ == "__main__":
    main()
