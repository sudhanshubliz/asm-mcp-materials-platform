from streamlit_ui.services.normalizers import normalize_comparison_response, normalize_mcp_response


def test_normalize_material_lookup_response():
    payload = {"material_id": "mp-149", "formula_pretty": "Si", "predicted_stable": True, "is_metal": False}

    result = normalize_mcp_response("get_material_by_id_tool", payload, "Get properties for mp-149")

    assert result.intent == "material_id_lookup"
    assert result.records[0]["material_id"] == "mp-149"
    assert result.metrics["Matches"] == 1


def test_normalize_advanced_search_response():
    payload = {
        "count": 2,
        "columns": ["material_id", "formula_pretty"],
        "data": [
            {"material_id": "mp-1", "formula_pretty": "SiO2", "predicted_stable": True, "is_metal": False},
            {"material_id": "mp-2", "formula_pretty": "SiO", "predicted_stable": False, "is_metal": False},
        ],
    }

    result = normalize_mcp_response("search_materials_advanced_tool", payload, "advanced search")

    assert result.intent == "advanced_search"
    assert result.metrics["Matches"] == 2
    assert result.metrics["Stable"] == 1


def test_normalize_comparison_response():
    records = [
        {"material_id": "mp-149", "formula_pretty": "Si", "predicted_stable": True, "is_metal": False},
        {"material_id": "mp-2534", "formula_pretty": "GaAs", "predicted_stable": True, "is_metal": False},
    ]

    result = normalize_comparison_response(records, "Compare Si and GaAs")

    assert result.intent == "compare"
    assert result.metrics["Matches"] == 2
