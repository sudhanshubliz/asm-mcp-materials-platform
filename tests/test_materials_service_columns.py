from unittest.mock import Mock, patch

import pytest

from app.services.exceptions import ExternalServiceError
from app.services.materials_service import (
    MATERIAL_OUTPUT_COLUMNS,
    _canonical_material_id,
    _get_material_by_id_rest,
    _normalize_output,
)


def test_normalize_output_matches_requested_headers_and_aliases():
    payload = {
        "material_id": "mp-123",
        "nsites": 10,
        "formula_pretty": "Fe2O3",
        "chemsys": "Fe-O",
        "volume": 123.4,
        "density": 5.2,
        "energy_per_atom": -6.1,
        "formation_energy_per_atom": -1.2,
        "energy_above_hull": 0.03,
        "is_stable": True,
        "band_gap": 1.5,
        "is_metal": False,
        "total_magnetization": 3.0,
        "universal_anisotropy": 0.8,
        "weighted_surface_energy_EV_PER_ANG2": 0.1,
        "weighted_surface_energy": 1.2,
        "weighted_work_function": 4.9,
        "surface_anisotropy": 0.2,
        "shape_factor": 0.6,
        "symmetry": {"crystal_system": "trigonal", "symbol": "R-3c", "number": 167},
        "structure": {
            "sites": [
                {"species": [{"element": "Fe"}], "abc": [0.0, 0.0, 0.0]},
                {"species": [{"element": "O"}], "abc": [0.5, 0.5, 0.5]},
            ]
        },
        "ordering": "FM",
        "bulk_modulus": {"voigt": 210, "reuss": 200, "vrh": 205},
        "shear_modulus": {"voigt": 120, "reuss": 110, "vrh": 115},
    }

    row = _normalize_output(payload)

    assert list(row.keys()) == MATERIAL_OUTPUT_COLUMNS
    assert row["material_id"] == "mp-123"
    assert row["materials_project_url"] == "https://next-gen.materialsproject.org/materials/mp-123"
    assert row["structure_preview"]["site_count"] == 2
    assert row["structure_preview"]["atoms"][0]["element"] == "Fe"
    assert row["predicted_stable"] is True
    assert row["work_function"] == 4.9
    assert row["crystal_system"] == "trigonal"
    assert row["bulk_modulus_vrh"] == 205
    assert row["shear_modulus_reuss"] == 110


def test_normalize_output_drops_non_numeric_material_id():
    row = _normalize_output({"material_id": "mp-djqth"})

    assert row["material_id"] is None
    assert row["materials_project_url"] is None


def test_canonical_material_id_extracts_numeric_id_from_serialized_value():
    assert _canonical_material_id("MPID(mp-149)") == "mp-149"
    assert _canonical_material_id({"material_id": "MPID(mp-162)"}) == "mp-162"


def test_rest_material_lookup_rejects_mismatched_material_id():
    response = Mock()
    response.json.return_value = {"data": [{"material_id": "mp-gg", "formula_pretty": "Yb"}]}
    response.raise_for_status.return_value = None
    session = Mock()
    session.get.return_value = response

    with patch("app.services.materials_service.build_retrying_session", return_value=session), pytest.raises(
        ExternalServiceError
    ) as exc_info:
        _get_material_by_id_rest("mp-162")

    assert exc_info.value.status_code == 404
