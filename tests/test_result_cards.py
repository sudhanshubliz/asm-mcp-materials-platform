from streamlit_ui.components.result_cards import _materials_project_url, _structure_image_url


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
