from app.services.materials_service import MATERIAL_OUTPUT_COLUMNS, _normalize_output


def test_normalize_output_matches_requested_headers_and_aliases():
    payload = {
        "material_id": "mp-csvwu",
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
        "ordering": "FM",
        "bulk_modulus": {"voigt": 210, "reuss": 200, "vrh": 205},
        "shear_modulus": {"voigt": 120, "reuss": 110, "vrh": 115},
    }

    row = _normalize_output(payload)

    assert list(row.keys()) == MATERIAL_OUTPUT_COLUMNS
    assert row["predicted_stable"] is True
    assert row["work_function"] == 4.9
    assert row["crystal_system"] == "trigonal"
    assert row["bulk_modulus_vrh"] == 205
    assert row["shear_modulus_reuss"] == 110
