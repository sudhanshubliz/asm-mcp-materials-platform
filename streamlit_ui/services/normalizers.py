from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from streamlit_ui.utils.constants import DEFAULT_SUGGESTIONS


@dataclass(frozen=True)
class NormalizedResult:
    intent: str
    title: str
    subtitle: str
    records: list[dict[str, Any]]
    columns: list[str]
    metrics: dict[str, Any]
    suggestions: list[str]
    raw: dict[str, Any]


def _summarize_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    stable_count = sum(1 for record in records if record.get("predicted_stable") is True)
    metallic_count = sum(1 for record in records if record.get("is_metal") is True)
    return {
        "Matches": len(records),
        "Stable": stable_count,
        "Metallic": metallic_count,
    }


def normalize_mcp_response(tool_name: str, payload: dict[str, Any], query: str) -> NormalizedResult:
    if tool_name == "get_material_by_id_tool":
        records = [payload]
        columns = list(payload.keys())
        return NormalizedResult(
            intent="material_id_lookup",
            title=f"Material snapshot for {payload.get('material_id', query)}",
            subtitle="Direct material lookup from the MCP server.",
            records=records,
            columns=columns,
            metrics=_summarize_metrics(records),
            suggestions=["Compare this material against another mp-id", *DEFAULT_SUGGESTIONS[:2]],
            raw=payload,
        )

    if tool_name == "search_material_tool":
        mp_payload = payload.get("materials_project", {})
        records = mp_payload.get("data", [])
        columns = list(records[0].keys()) if records else []
        return NormalizedResult(
            intent="formula_lookup",
            title=f"Formula search results for {query}",
            subtitle=f"{len(records)} normalized matches returned from Materials Project.",
            records=records,
            columns=columns,
            metrics=_summarize_metrics(records),
            suggestions=DEFAULT_SUGGESTIONS,
            raw=payload,
        )

    if tool_name == "search_materials_advanced_tool":
        records = payload.get("data", [])
        columns = payload.get("columns") or (list(records[0].keys()) if records else [])
        subtitle = f"{payload.get('count', len(records))} candidate materials matched the structured filters."
        return NormalizedResult(
            intent="advanced_search",
            title="Advanced materials search",
            subtitle=subtitle,
            records=records,
            columns=columns,
            metrics=_summarize_metrics(records),
            suggestions=["Relax one filter to widen the search", *DEFAULT_SUGGESTIONS[:2]],
            raw=payload,
        )

    intent = payload.get("intent", "chat_search")
    if intent == "material_by_id":
        material_payload = payload.get("materials_project", {})
        records = [material_payload] if material_payload else []
        columns = payload.get("columns") or (list(material_payload.keys()) if material_payload else [])
        title = f"Material profile for {payload.get('material_id', query)}"
    else:
        records = payload.get("data") or payload.get("materials_project", {}).get("data", [])
        columns = payload.get("columns") or (list(records[0].keys()) if records else [])
        title = "Materials assistant results"

    subtitle = payload.get("question") or query
    return NormalizedResult(
        intent=intent,
        title=title,
        subtitle=subtitle,
        records=records,
        columns=columns,
        metrics=_summarize_metrics(records),
        suggestions=payload.get("heuristics") or DEFAULT_SUGGESTIONS,
        raw=payload,
    )


def normalize_comparison_response(records: list[dict[str, Any]], query: str) -> NormalizedResult:
    columns = list(records[0].keys()) if records else []
    return NormalizedResult(
        intent="compare",
        title="Material comparison",
        subtitle=query,
        records=records,
        columns=columns,
        metrics=_summarize_metrics(records),
        suggestions=["Export this comparison as CSV", "Search for related materials in the Explorer page"],
        raw={"comparison": records},
    )
