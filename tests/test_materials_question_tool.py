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
        "app.tools.materials_tools.search_material",
        return_value={"count": 1, "data": [{"material_id": "mp-1", "crystal_system": "cubic"}]},
    ), patch("app.tools.materials_tools.search_oqmd", return_value={"count": 0, "data": []}):
        result = ask_materials_project_tool("Find details for Fe2O3", limit=5, offset=0)

    assert result["intent"] == "material_search_federated"
    assert result["formula"] == "Fe2O3"
    assert "data" in result


def test_ask_materials_project_routes_single_element_formula():
    with patch(
        "app.tools.materials_tools.search_material",
        return_value={"count": 1, "data": [{"material_id": "mp-2", "crystal_system": "hexagonal"}]},
    ), patch("app.tools.materials_tools.search_oqmd", return_value={"count": 0, "data": []}):
        result = ask_materials_project_tool(
            "Retrieve full structural and electronic properties for material Dy",
            limit=5,
            offset=0,
        )

    assert result["intent"] == "material_search_federated"
    assert result["formula"] == "Dy"


def test_ask_materials_project_filters_work_function_range():
    rows = [
        {"material_id": "mp-a", "work_function": 4.2, "crystal_system": "cubic"},
        {"material_id": "mp-b", "work_function": 4.8, "crystal_system": "cubic"},
        {"material_id": "mp-c", "work_function": 5.4, "crystal_system": "hexagonal"},
        {"material_id": "mp-d", "work_function": 5.8, "crystal_system": "hexagonal"},
    ]
    with patch("app.tools.materials_tools.search_material", return_value={"count": 4, "data": rows}):
        result = ask_materials_project_tool("Find materials with work function between 4.5 and 5.5", limit=10)

    returned_ids = {row["material_id"] for row in result["data"]}
    assert returned_ids == {"mp-b", "mp-c"}


def test_ask_materials_project_filters_crystal_and_numeric():
    rows = [
        {"material_id": "mp-a", "crystal_system": "cubic", "shear_modulus_vrh": 90.0, "density": 5.0},
        {"material_id": "mp-b", "crystal_system": "cubic", "shear_modulus_vrh": 70.0, "density": 5.0},
        {"material_id": "mp-c", "crystal_system": "hexagonal", "shear_modulus_vrh": 95.0, "density": 6.5},
    ]
    with patch("app.tools.materials_tools.search_material", return_value={"count": 3, "data": rows}):
        result = ask_materials_project_tool(
            "Pull materials where shear modulus VRH is above 80 and density is below 6 and cubic",
            limit=10,
        )

    assert [row["material_id"] for row in result["data"]] == ["mp-a"]


def test_ask_materials_project_rejects_unparsable_question():
    with patch("app.tools.materials_tools.search_material", return_value={"count": 0, "data": []}):
        with pytest.raises(ExternalServiceError):
            ask_materials_project_tool("Tell me something interesting")
