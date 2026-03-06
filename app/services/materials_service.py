from app.config import config
from app.services.exceptions import ExternalServiceError


MATERIAL_OUTPUT_COLUMNS = [
    "material_id",
    "nsites",
    "formula_pretty",
    "chemsys",
    "volume",
    "density",
    "energy_per_atom",
    "formation_energy_per_atom",
    "energy_above_hull",
    "predicted_stable",
    "band_gap",
    "is_metal",
    "total_magnetization",
    "universal_anisotropy",
    "weighted_surface_energy_EV_PER_ANG2",
    "weighted_surface_energy",
    "work_function",
    "surface_anisotropy",
    "shape_factor",
    "crystal_system",
    "space_group_symbol",
    "space_group_number",
    "magnetic_ordering",
    "bulk_modulus_voigt",
    "bulk_modulus_reuss",
    "bulk_modulus_vrh",
    "shear_modulus_voigt",
    "shear_modulus_reuss",
    "shear_modulus_vrh",
]


def _ensure_api_key() -> None:
    if not config.MATERIALS_API_KEY:
        raise ExternalServiceError(
            service="materials_project",
            message="MATERIALS_API_KEY is not configured",
            status_code=400,
        )


def _clean_doc(doc) -> dict:
    payload = doc.model_dump()
    payload.pop("fields_not_requested", None)
    return _normalize_output(payload)


def _obj_get(obj, key: str):
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _extract_metric_values(metric) -> tuple[float | None, float | None, float | None]:
    voigt = _obj_get(metric, "voigt")
    reuss = _obj_get(metric, "reuss")
    vrh = _obj_get(metric, "vrh")
    return voigt, reuss, vrh


def _normalize_output(payload: dict) -> dict:
    symmetry = payload.get("symmetry") or {}
    bulk_modulus = payload.get("bulk_modulus")
    shear_modulus = payload.get("shear_modulus")

    bulk_voigt, bulk_reuss, bulk_vrh = _extract_metric_values(bulk_modulus)
    shear_voigt, shear_reuss, shear_vrh = _extract_metric_values(shear_modulus)

    normalized = {
        "material_id": payload.get("material_id"),
        "nsites": payload.get("nsites"),
        "formula_pretty": payload.get("formula_pretty"),
        "chemsys": payload.get("chemsys"),
        "volume": payload.get("volume"),
        "density": payload.get("density"),
        "energy_per_atom": payload.get("energy_per_atom"),
        "formation_energy_per_atom": payload.get("formation_energy_per_atom"),
        "energy_above_hull": payload.get("energy_above_hull"),
        "predicted_stable": payload.get("is_stable"),
        "band_gap": payload.get("band_gap"),
        "is_metal": payload.get("is_metal"),
        "total_magnetization": payload.get("total_magnetization"),
        "universal_anisotropy": payload.get("universal_anisotropy"),
        "weighted_surface_energy_EV_PER_ANG2": payload.get("weighted_surface_energy_EV_PER_ANG2"),
        "weighted_surface_energy": payload.get("weighted_surface_energy"),
        "work_function": payload.get("weighted_work_function", payload.get("work_function")),
        "surface_anisotropy": payload.get("surface_anisotropy"),
        "shape_factor": payload.get("shape_factor"),
        "crystal_system": _obj_get(symmetry, "crystal_system"),
        "space_group_symbol": _obj_get(symmetry, "symbol"),
        "space_group_number": _obj_get(symmetry, "number"),
        "magnetic_ordering": payload.get("ordering"),
        "bulk_modulus_voigt": bulk_voigt,
        "bulk_modulus_reuss": bulk_reuss,
        "bulk_modulus_vrh": bulk_vrh,
        "shear_modulus_voigt": shear_voigt,
        "shear_modulus_reuss": shear_reuss,
        "shear_modulus_vrh": shear_vrh,
    }

    return {column: normalized.get(column) for column in MATERIAL_OUTPUT_COLUMNS}


def _summary_fields() -> list[str]:
    return [
        "material_id",
        "nsites",
        "formula_pretty",
        "chemsys",
        "volume",
        "density",
        "energy_per_atom",
        "band_gap",
        "formation_energy_per_atom",
        "is_stable",
        "energy_above_hull",
        "is_metal",
        "total_magnetization",
        "universal_anisotropy",
        "weighted_surface_energy_EV_PER_ANG2",
        "weighted_surface_energy",
        "weighted_work_function",
        "surface_anisotropy",
        "shape_factor",
        "symmetry",
        "ordering",
        "bulk_modulus",
        "shear_modulus",
    ]


def search_material(formula: str | None, limit: int = 20, offset: int = 0) -> dict:
    _ensure_api_key()

    if config.MATERIALS_API_MODE in {"auto", "rest"}:
        try:
            return _search_material_rest(formula, limit, offset)
        except ExternalServiceError as exc:
            if config.MATERIALS_API_MODE == "rest":
                raise

    if config.MATERIALS_API_MODE not in {"auto", "mp_api"}:
        raise ExternalServiceError(
            service="materials_project",
            message=f"Unsupported MATERIALS_API_MODE: {config.MATERIALS_API_MODE}",
            status_code=400,
        )

    # Fallback to official mp-api client when REST is blocked by provider policy.
    try:
        from mp_api.client import MPRester

        with MPRester(config.MATERIALS_API_KEY) as mpr:
            kwargs = {
                "num_chunks": 1,
                "chunk_size": max(1, min(limit, 100)),
                "fields": _summary_fields(),
            }
            if formula:
                kwargs["formula"] = formula
            docs = mpr.materials.summary.search(**kwargs)

        sliced = docs[offset : offset + limit] if offset > 0 else docs[:limit]
        cleaned_docs = [_clean_doc(doc) for doc in sliced]

        return {"count": len(cleaned_docs), "data": cleaned_docs}
    except ImportError as exc:
        raise ExternalServiceError(
            service="materials_project",
            message="mp-api package is not installed. Run: pip install mp-api",
            status_code=500,
        ) from exc
    except Exception as exc:
        # mp-api wraps HTTP/auth errors; surface detail to caller.
        raise ExternalServiceError(
            service="materials_project",
            message=f"Materials Project request failed: {exc}",
            status_code=403 if "403" in str(exc) else 502,
        ) from exc


def _search_material_rest(formula: str | None, limit: int, offset: int) -> dict:
    try:
        import requests
    except ImportError as exc:
        raise ExternalServiceError(
            service="materials_project",
            message="requests package is not installed",
            status_code=500,
        ) from exc

    url = f"{config.MATERIALS_API.rstrip('/')}{config.MATERIALS_SUMMARY_PATH}"
    headers = {config.MATERIALS_API_KEY_HEADER: config.MATERIALS_API_KEY}
    params = {"limit": limit, "skip": offset}
    if formula:
        params["formula"] = formula

    try:
        response = requests.get(url, headers=headers, params=params, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 502
        detail = exc.response.text if exc.response is not None else str(exc)
        raise ExternalServiceError(
            service="materials_project",
            message=f"Materials Project REST request failed ({status}): {detail[:300]}",
            status_code=status if status in {400, 401, 403, 404, 429} else 502,
        ) from exc
    except requests.RequestException as exc:
        raise ExternalServiceError(
            service="materials_project",
            message=f"Materials Project REST network error: {exc}",
            status_code=502,
        ) from exc

    rows = []
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            rows = payload["data"]
        elif isinstance(payload.get("results"), list):
            rows = payload["results"]
    elif isinstance(payload, list):
        rows = payload

    cleaned_docs = [_normalize_output(doc if isinstance(doc, dict) else {}) for doc in rows]
    return {"count": len(cleaned_docs), "data": cleaned_docs}


def get_material_by_id(material_id: str) -> dict:
    _ensure_api_key()

    try:
        from mp_api.client import MPRester

        with MPRester(config.MATERIALS_API_KEY) as mpr:
            docs = mpr.materials.summary.search(
                material_ids=[material_id],
                num_chunks=1,
                chunk_size=1,
                fields=_summary_fields(),
            )

        if not docs:
            raise ExternalServiceError(
                service="materials_project",
                message=f"Material not found: {material_id}",
                status_code=404,
            )

        return _clean_doc(docs[0])
    except ImportError as exc:
        raise ExternalServiceError(
            service="materials_project",
            message="mp-api package is not installed. Run: pip install mp-api",
            status_code=500,
        ) from exc
    except ExternalServiceError:
        raise
    except Exception as exc:
        raise ExternalServiceError(
            service="materials_project",
            message=f"Materials Project request failed: {exc}",
            status_code=403 if "403" in str(exc) else 502,
        ) from exc
