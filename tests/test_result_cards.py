from streamlit_ui.components.result_cards import (
    _materials_project_url,
    _record_provenance,
    _structure_image_url,
    _structure_preview_svg,
    _table_records,
)


def test_materials_project_url_accepts_numeric_mp_identifier():
    assert _materials_project_url("mp-162") == "https://next-gen.materialsproject.org/materials/mp-162"


def test_materials_project_url_rejects_non_numeric_identifier():
    assert _materials_project_url("mp-djqth") is None
    assert _materials_project_url(None) is None


def test_structure_image_url_uses_known_image_fields():
    record = {"structure_image_url": "https://example.com/mp-162.png"}

    assert _structure_image_url(record) == "https://example.com/mp-162.png"


def test_structure_image_url_ignores_non_url_values():
    record = {"structure_image_url": "/local/mp-162.png", "image_url": None}

    assert _structure_image_url(record) is None


def test_structure_preview_svg_renders_atoms():
    svg = _structure_preview_svg(
        {
            "site_count": 2,
            "atoms": [
                {"element": "Al", "x": 0.1, "y": 0.2},
                {"element": "Cu", "x": 0.8, "y": 0.7},
            ],
        }
    )

    assert svg is not None
    assert "Small structure preview" in svg
    assert "Al" in svg
    assert "Cu" in svg


def test_table_records_hide_structure_preview_and_all_empty_columns():
    rows = _table_records(
        [
            {"material_id": "mp-1", "formula_pretty": "AlCu", "work_function": None, "structure_preview": {"atoms": []}},
            {"material_id": "mp-2", "formula_pretty": "AlCr", "work_function": None, "structure_preview": {"atoms": []}},
        ]
    )

    assert rows == [
        {"material_id": "mp-1", "formula_pretty": "AlCu"},
        {"material_id": "mp-2", "formula_pretty": "AlCr"},
    ]


def test_record_provenance_does_not_invent_confidence():
    assert _record_provenance({"source": "Materials Project", "confidence": None}) == (
        "Materials Project",
        "Not reported",
    )
    assert _record_provenance({"source": "Qdrant", "confidence": 0.91234}) == ("Qdrant", "0.9123")
