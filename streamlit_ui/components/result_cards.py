from __future__ import annotations

from typing import Any

import streamlit as st

from streamlit_ui.services.normalizers import NormalizedResult
from streamlit_ui.utils.exports import records_to_csv, records_to_dataframe, records_to_json


def _render_metrics(metrics: dict[str, Any]) -> None:
    columns = st.columns(len(metrics))
    for column, (label, value) in zip(columns, metrics.items()):
        column.metric(label, value)


def render_result(
    result: NormalizedResult,
    *,
    show_raw_json: bool,
    compact_mode: bool,
    key_prefix: str,
) -> None:
    st.markdown(f"#### {result.title}")
    st.caption(result.subtitle)
    if result.metrics:
        _render_metrics(result.metrics)

    records = result.records
    if records:
        dataframe = records_to_dataframe(records)
        preview = dataframe if not compact_mode else dataframe.head(5)
        st.dataframe(preview, use_container_width=True, hide_index=True)

        download_columns = st.columns(2)
        download_columns[0].download_button(
            "Download CSV",
            data=records_to_csv(records),
            file_name="materials-results.csv",
            mime="text/csv",
            key=f"{key_prefix}-download-csv",
            use_container_width=True,
        )
        download_columns[1].download_button(
            "Download JSON",
            data=records_to_json(records),
            file_name="materials-results.json",
            mime="application/json",
            key=f"{key_prefix}-download-json",
            use_container_width=True,
        )

        st.markdown("##### Result cards")
        for record in records[: (3 if compact_mode else 5)]:
            label = record.get("material_id") or record.get("formula_pretty") or "Material"
            with st.expander(f"{label} • {record.get('formula_pretty', 'Unknown formula')}", expanded=not compact_mode):
                cols = st.columns(4)
                cols[0].metric("Band gap", record.get("band_gap", "N/A"))
                cols[1].metric("Density", record.get("density", "N/A"))
                cols[2].metric("Stable", "Yes" if record.get("predicted_stable") else "No")
                cols[3].metric("Metal", "Yes" if record.get("is_metal") else "No")
                st.json(record, expanded=False)
    else:
        st.info("No records matched the current query.")

    if result.suggestions:
        st.markdown("##### Follow-up suggestions")
        for suggestion in result.suggestions[:3]:
            st.caption(f"• {suggestion}")

    if show_raw_json:
        with st.expander("Raw MCP payload", expanded=False):
            st.json(result.raw, expanded=False)
