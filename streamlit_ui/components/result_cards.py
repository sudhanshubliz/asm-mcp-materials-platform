from __future__ import annotations

import html
import re
from typing import Any

import streamlit as st

from streamlit_ui.services.normalizers import NormalizedResult
from streamlit_ui.utils.exports import records_to_csv, records_to_dataframe, records_to_json

_CANONICAL_MP_ID_PATTERN = re.compile(r"^mp-\d+$")
_STRUCTURE_IMAGE_FIELDS = ("structure_image_url", "structure_url", "image_url", "thumbnail_url")
_NON_TABLE_FIELDS = {"structure_preview", "confidence"}
_PRIMARY_FIELDS = (
    "material_id",
    "formula_pretty",
    "crystal_system",
    "space_group_symbol",
    "band_gap",
    "density",
    "energy_above_hull",
    "predicted_stable",
    "is_metal",
)
_ATOM_COLORS = {
    "Al": "#9aa6b2",
    "B": "#3f8f5b",
    "C": "#30343b",
    "Cr": "#5b6ee1",
    "Cu": "#c47f3a",
    "Fe": "#b14c3f",
    "Li": "#7c5ce6",
    "O": "#d94f45",
    "Re": "#5f7f95",
    "Si": "#d1a447",
    "Tc": "#6a93a8",
}


def _render_metrics(metrics: dict[str, Any]) -> None:
    columns = st.columns(len(metrics))
    for column, (label, value) in zip(columns, metrics.items()):
        column.metric(label, value)


def _materials_project_url(material_id: Any) -> str | None:
    if not isinstance(material_id, str) or not _CANONICAL_MP_ID_PATTERN.fullmatch(material_id):
        return None
    return f"https://next-gen.materialsproject.org/materials/{material_id}"


def _structure_image_url(record: dict[str, Any]) -> str | None:
    for field in _STRUCTURE_IMAGE_FIELDS:
        value = record.get(field)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
    return None


def _structure_preview_svg(preview: dict[str, Any]) -> str | None:
    atoms = preview.get("atoms")
    if not isinstance(atoms, list) or not atoms:
        return None

    circles = []
    for atom in atoms[:48]:
        if not isinstance(atom, dict):
            continue
        element = str(atom.get("element") or "X")[:2]
        try:
            x = 16 + (float(atom.get("x", 0.5)) % 1) * 128
            y = 16 + (float(atom.get("y", 0.5)) % 1) * 88
        except (TypeError, ValueError):
            continue
        color = _ATOM_COLORS.get(element, "#4b8f7a")
        safe_element = html.escape(element)
        circles.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{color}" opacity="0.86" />'
            f'<text x="{x:.1f}" y="{y + 3:.1f}" text-anchor="middle" font-size="7" fill="white">{safe_element}</text>'
        )

    if not circles:
        return None

    site_count = html.escape(str(preview.get("site_count") or len(atoms)))
    return (
        '<svg viewBox="0 0 160 120" role="img" aria-label="Small structure preview" '
        'style="width: 100%; max-width: 220px; height: auto; border: 1px solid #e5e7eb; border-radius: 8px; background: #fbfcfb;">'
        '<rect x="14" y="14" width="132" height="92" rx="6" fill="none" stroke="#cbd5d1" stroke-width="1" />'
        + "".join(circles)
        + f'<text x="80" y="116" text-anchor="middle" font-size="8" fill="#5f6f68">{site_count} sites</text>'
        + "</svg>"
    )


def _render_structure_preview(record: dict[str, Any]) -> None:
    image_url = _structure_image_url(record)
    preview = record.get("structure_preview")

    if image_url:
        st.image(image_url, caption="Structure preview", use_container_width=True)
        return

    if isinstance(preview, dict):
        svg = _structure_preview_svg(preview)
        if svg:
            st.markdown(svg, unsafe_allow_html=True)
            st.caption("Small projected structure preview")
            return

    st.caption("Inline structure preview is not available for this result.")


def _record_provenance(record: dict[str, Any]) -> tuple[str, str]:
    source = str(record.get("source") or "Materials Project")
    confidence = record.get("confidence")
    confidence_label = "Not reported" if confidence is None else _display_value(confidence)
    return source, confidence_label


def _render_material_actions(record: dict[str, Any]) -> None:
    material_url = record.get("materials_project_url") or _materials_project_url(record.get("material_id"))
    if isinstance(material_url, str):
        st.link_button("Open in Materials Project", material_url, use_container_width=True)


def _display_value(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def _record_summary(record: dict[str, Any]) -> dict[str, str]:
    return {field: _display_value(record.get(field)) for field in _PRIMARY_FIELDS if field in record}


def _table_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    visible_columns = []
    for column in records[0].keys():
        if column in _NON_TABLE_FIELDS:
            continue
        if any(record.get(column) is not None for record in records):
            visible_columns.append(column)

    return [{column: _display_value(record.get(column)) for column in visible_columns} for record in records]


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
        dataframe = records_to_dataframe(_table_records(records))
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
        card_limit = 3 if compact_mode else 5
        visible_records = records[:card_limit]
        if len(records) > len(visible_records):
            st.caption(f"Showing {len(visible_records)} of {len(records)} result cards. The table and downloads include all results.")
        for record in visible_records:
            label = record.get("material_id") or record.get("formula_pretty") or "Material"
            with st.expander(f"{label} • {record.get('formula_pretty', 'Unknown formula')}", expanded=not compact_mode):
                source, confidence = _record_provenance(record)
                st.caption(f"Source: {source} | Confidence: {confidence}")
                cols = st.columns(4)
                cols[0].metric("Band gap (eV)", _display_value(record.get("band_gap")))
                cols[1].metric("Density (g/cm³)", _display_value(record.get("density")))
                cols[2].metric("Stable", _display_value(record.get("predicted_stable")))
                cols[3].metric("Metal", _display_value(record.get("is_metal")))
                st.table(_record_summary(record))
                _render_structure_preview(record)
                _render_material_actions(record)
                with st.expander("Raw record", expanded=False):
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
