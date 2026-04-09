from unittest.mock import patch

import pytest

from app.services.exceptions import ExternalServiceError
from app.tools.materials_tools import ask_materials_project_tool


def test_ask_materials_project_routes_by_material_id():
    with patch("app.tools.materials_tools.get_material_by_id_tool", return_value={"material_id": "mp-csvwu"}):
        result = ask_materials_project_tool("Get result for material_id mp-csvwu")

    assert result["intent"] == "material_by_id"
    assert result["material_id"] == "mp-csvwu"


def test_ask_materials_project_routes_by_formula():
    with patch(
        "app.tools.materials_tools.advanced_search_materials",
        return_value={"count": 1, "total_source_rows": 1, "data": [{"material_id": "mp-1", "crystal_system": "cubic"}]},
    ), patch("app.tools.materials_tools.search_oqmd", return_value={"count": 0, "data": []}):
        result = ask_materials_project_tool("Find details for Fe2O3", limit=5, offset=0)

    assert result["intent"] == "material_search_federated"
    assert result["formula"] == "Fe2O3"
    assert "data" in result


def test_ask_materials_project_routes_single_element_formula():
    with patch(
        "app.tools.materials_tools.advanced_search_materials",
        return_value={"count": 1, "total_source_rows": 1, "data": [{"material_id": "mp-2", "crystal_system": "hexagonal"}]},
    ), patch("app.tools.materials_tools.search_oqmd", return_value={"count": 0, "data": []}):
        result = ask_materials_project_tool(
            "Retrieve full structural and electronic properties for material Dy",
            limit=5,
            offset=0,
        )

    assert result["intent"] == "material_search_federated"
    assert result["formula"] == "Dy"


def test_ask_materials_project_supports_elements_and_band_gap():
    with patch(
        "app.tools.materials_tools.advanced_search_materials",
        return_value={"count": 1, "total_source_rows": 1, "data": [{"material_id": "mp-149", "crystal_system": "cubic"}]},
    ):
        result = ask_materials_project_tool(
            "Show materials containing Si and O with band gap between 0.5 and 1.0 eV",
            limit=10,
        )

    assert result["intent"] == "advanced_material_search"
    assert result["elements"] == ["Si", "O"]
    assert result["applied_filters"]["band_gap"]["min"] == 0.5
    assert result["applied_filters"]["band_gap"]["max"] == 1.0


def test_ask_materials_project_supports_lowercase_elements():
    with patch(
        "app.tools.materials_tools.advanced_search_materials",
        return_value={"count": 1, "total_source_rows": 1, "data": [{"material_id": "mp-149", "crystal_system": "cubic"}]},
    ):
        result = ask_materials_project_tool(
            "show materials containing si and o with band gap between 0.5 and 1.0 eV",
            limit=10,
        )

    assert result["elements"] == ["Si", "O"]


def test_ask_materials_project_applies_lightweight_alloy_heuristics():
    with patch(
        "app.tools.materials_tools.advanced_search_materials",
        return_value={"count": 1, "total_source_rows": 1, "data": [{"material_id": "mp-42", "crystal_system": "hexagonal"}]},
    ):
        result = ask_materials_project_tool("Find lightweight alloys used in aerospace engineering", limit=10)

    assert result["intent"] == "advanced_material_search"
    assert result["applied_filters"]["is_metal"] is True
    assert result["applied_filters"]["density"]["max"] == 5.0
    assert result["applied_filters"]["num_elements"]["min"] == 2
    assert result["heuristics"]


def test_ask_materials_project_rejects_unparsable_question():
    with pytest.raises(ExternalServiceError):
        ask_materials_project_tool("Tell me something interesting")
