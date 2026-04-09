from __future__ import annotations

import json
from typing import Any

import pandas as pd


def records_to_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


def records_to_csv(records: list[dict[str, Any]]) -> bytes:
    dataframe = records_to_dataframe(records)
    return dataframe.to_csv(index=False).encode("utf-8")


def records_to_json(records: list[dict[str, Any]]) -> bytes:
    return json.dumps(records, indent=2, default=str).encode("utf-8")
