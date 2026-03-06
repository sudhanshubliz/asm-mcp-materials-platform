from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.tools.materials_tools import search_material_tool


def test_search_material_tool_uses_cache_hit():
    with patch("app.tools.materials_tools.get_cache", return_value={"cached": True}), patch(
        "app.tools.materials_tools.search_material"
    ) as search_material_mock, patch("app.tools.materials_tools.search_oqmd") as search_oqmd_mock:
        result = search_material_tool("Fe2O3")

    assert result == {"cached": True}
    search_material_mock.assert_not_called()
    search_oqmd_mock.assert_not_called()


def test_search_material_tool_fetches_and_sets_cache():
    with patch("app.tools.materials_tools.config.OQMD_REQUIRED", False), patch(
        "app.tools.materials_tools.get_cache", return_value=None
    ), patch(
        "app.tools.materials_tools.search_material", return_value={"mp": 1}
    ), patch("app.tools.materials_tools.search_oqmd") as search_oqmd_mock, patch(
        "app.tools.materials_tools.set_cache"
    ) as set_cache_mock:
        result = search_material_tool("Fe2O3")

    assert result == {"materials_project": {"mp": 1}, "oqmd": None}
    search_oqmd_mock.assert_not_called()
    set_cache_mock.assert_called_once()


def test_search_material_tool_rejects_invalid_formula():
    with pytest.raises(ValidationError):
        search_material_tool("Fe2O3;")


def test_search_material_tool_fetches_oqmd_when_required():
    with patch("app.tools.materials_tools.config.OQMD_REQUIRED", True), patch(
        "app.tools.materials_tools.get_cache", return_value=None
    ), patch("app.tools.materials_tools.search_material", return_value={"mp": 1}), patch(
        "app.tools.materials_tools.search_oqmd", return_value={"oqmd": 2}
    ) as search_oqmd_mock, patch("app.tools.materials_tools.set_cache"):
        result = search_material_tool("Fe2O3")

    assert result["oqmd"] == {"oqmd": 2}
    search_oqmd_mock.assert_called_once()
