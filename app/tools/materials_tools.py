import re
from typing import Any

from app.cache.redis_cache import get_cache, set_cache
from app.config import config
from app.models.schemas import AdvancedMaterialSearchRequest, MaterialByIdRequest, MaterialSearchRequest, NumericRange
from app.services.exceptions import ExternalServiceError
from app.services.materials_service import (
    MATERIAL_OUTPUT_COLUMNS,
    advanced_search_materials,
    get_material_by_id,
    search_material,
)
from app.services.oqmd_service import search_oqmd


def search_material_tool(formula: str, limit: int = 20, offset: int = 0) -> dict:
    request = MaterialSearchRequest(formula=formula, limit=limit, offset=offset)

    cache_key = f"mat:{request.formula}:{request.limit}:{request.offset}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    data_mp = None
    data_oqmd = None
    errors: list[dict] = []

    try:
        data_mp = search_material(request.formula, request.limit, request.offset)
    except ExternalServiceError as exc:
        errors.append(exc.to_dict())

    if config.OQMD_REQUIRED:
        try:
            data_oqmd = search_oqmd(request.formula, request.limit, request.offset)
        except ExternalServiceError as exc:
            errors.append(exc.to_dict())

    if data_mp is None and data_oqmd is None:
        raise ExternalServiceError(
            service="materials_federation",
            message=f"All upstream sources failed: {errors}",
            status_code=502,
        )

    result = {
        "materials_project": data_mp,
        "oqmd": data_oqmd,
    }
    if errors:
        result["errors"] = errors
    else:
        set_cache(cache_key, result, ttl_seconds=config.CACHE_TTL_SECONDS)

    return result


def get_material_by_id_tool(material_id: str) -> dict:
    request = MaterialByIdRequest(material_id=material_id)
    return get_material_by_id(request.material_id)


_MP_ID_PATTERN = re.compile(r"\b(mp-[A-Za-z0-9-]+)\b")
# Supports both single-element (e.g., Dy) and multi-element formulas (e.g., Fe2O3).
_FORMULA_PATTERN = re.compile(r"\b([A-Z][a-z]?\d*(?:[A-Z][a-z]?\d*)*)\b")

_FIELD_ALIASES = {
    "num elements": "num_elements",
    "number of elements": "num_elements",
    "shear modulus vrh": "shear_modulus_vrh",
    "shear_modulus_vrh": "shear_modulus_vrh",
    "bulk modulus vrh": "bulk_modulus_vrh",
    "bulk_modulus_vrh": "bulk_modulus_vrh",
    "density": "density",
    "dens": "density",
    "weighted surface energy": "weighted_surface_energy",
    "weighted_surface_energy": "weighted_surface_energy",
    "predicted stable": "predicted_stable",
    "predicted_stable": "predicted_stable",
    "work function": "work_function",
    "work_function": "work_function",
    "band gap": "band_gap",
    "band_gap": "band_gap",
    "volume": "volume",
    "vol": "volume",
    "energy above hull": "energy_above_hull",
    "energy_above_hull": "energy_above_hull",
    "shape factor": "shape_factor",
    "shape_factor": "shape_factor",
    "surface anisotropy": "surface_anisotropy",
    "surface_anisotropy": "surface_anisotropy",
}

_CRYSTAL_SYSTEMS = [
    "triclinic",
    "monoclinic",
    "orthorhombic",
    "tetragonal",
    "trigonal",
    "hexagonal",
    "cubic",
]

_COMMON_NAME_ALIASES = {
    "silicon": "Si",
    "gallium arsenide": "GaAs",
    "titanium dioxide": "TiO2",
    "iron oxide": "Fe2O3",
    "lithium iron phosphate": "LiFePO4",
}

_NORMALIZED_ELEMENT_SYMBOLS = {element.lower(): element for element in {
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar",
    "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr",
    "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn", "Sb", "Te", "I", "Xe",
    "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
    "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po", "At", "Rn",
}}


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _detect_formula(question: str) -> str | None:
    lowered = question.lower()
    for common_name, formula in _COMMON_NAME_ALIASES.items():
        if common_name in lowered:
            return formula
    explicit_material_match = re.search(r"\bmaterial\s+([A-Z][a-z]?\d*(?:[A-Z][a-z]?\d*)*)\b", question)
    formula_match = explicit_material_match or _FORMULA_PATTERN.search(question)
    return formula_match.group(1) if formula_match else None


def _extract_elements(question: str) -> list[str]:
    lowered = question.lower()
    for marker in ("containing", "contains", "include", "including", "with elements", "with element"):
        if marker not in lowered:
            continue
        fragment = question[lowered.index(marker) + len(marker) :]
        fragment = re.split(r"\b(with|where|that|having|band gap|density|compare|between)\b", fragment, maxsplit=1)[0]
        tokens = re.findall(r"\b([A-Za-z][a-z]?)\b", fragment)
        elements = [_NORMALIZED_ELEMENT_SYMBOLS[token.lower()] for token in tokens if token.lower() in _NORMALIZED_ELEMENT_SYMBOLS]
        if elements:
            return list(dict.fromkeys(elements))
    return []


def _normalize_field(raw: str) -> str | None:
    key = " ".join(raw.lower().strip().split())
    return _FIELD_ALIASES.get(key)


def _extract_filters(question: str) -> tuple[list[tuple[str, str, float]], list[str], bool | None, bool | None]:
    q = question.lower()
    filters: list[tuple[str, str, float]] = []
    crystal_filters: list[str] = []
    predicted_stable: bool | None = None
    is_metal: bool | None = None

    # Example: work function between 4.5 and 5.5
    for match in re.finditer(
        r"(work function|work_function|band gap|band_gap|density|dens|volume|vol|energy above hull|energy_above_hull|shear modulus vrh|bulk modulus vrh|shape factor|surface anisotropy|weighted surface energy|num elements|number of elements)\s*(?:between|from)\s*([0-9]*\.?[0-9]+)\s*(?:and|to)\s*([0-9]*\.?[0-9]+)",
        q,
    ):
        field = _normalize_field(match.group(1))
        if field:
            filters.append((field, "between_min", float(match.group(2))))
            filters.append((field, "between_max", float(match.group(3))))

    # Example: vol >200, dens <3, band gap >= 2
    for match in re.finditer(
        r"(shear modulus vrh|bulk modulus vrh|density|dens|weighted surface energy|work function|band gap|volume|vol|shape factor|surface anisotropy|energy above hull|num elements|number of elements)\s*(>=|<=|>|<|=)\s*([0-9]*\.?[0-9]+)",
        q,
    ):
        field = _normalize_field(match.group(1))
        if not field:
            continue
        op = match.group(2)
        value = float(match.group(3))
        filters.append((field, op, value))

    # Example: shear modulus vrh is above 80 and density is below 6
    for match in re.finditer(
        r"(shear modulus vrh|bulk modulus vrh|density|dens|weighted surface energy|work function|band gap|volume|vol|shape factor|surface anisotropy|energy above hull|num elements|number of elements)\s*(?:is\s*)?(above|below|greater than|less than)\s*([0-9]*\.?[0-9]+)",
        q,
    ):
        field = _normalize_field(match.group(1))
        if not field:
            continue
        op = ">" if match.group(2) in {"above", "greater than"} else "<"
        filters.append((field, op, float(match.group(3))))

    if "weighted surface energy is low" in q or "weighted surface energy low" in q:
        filters.append(("weighted_surface_energy", "<", 1.0))

    if "high surface anisotropy" in q:
        filters.append(("surface_anisotropy", ">", 1.0))

    if "predicted_stable = true" in q or "predicted stable = true" in q or "predicted stable true" in q:
        predicted_stable = True
    if "predicted_stable = false" in q or "predicted stable = false" in q or "predicted stable false" in q:
        predicted_stable = False

    if "non-metal" in q or "non metal" in q:
        is_metal = False
    elif "metal" in q or "metallic" in q or "alloy" in q:
        is_metal = True

    for cs in _CRYSTAL_SYSTEMS:
        if re.search(rf"\b{cs}\b", q):
            crystal_filters.append(cs)

    return filters, crystal_filters, predicted_stable, is_metal


def _match_filter(value: Any, op: str, expected: float) -> bool:
    v = _to_float(value)
    if v is None:
        return False
    if op == ">":
        return v > expected
    if op == "<":
        return v < expected
    if op == ">=":
        return v >= expected
    if op == "<=":
        return v <= expected
    if op == "=":
        return v == expected
    if op == "between_min":
        return v >= expected
    if op == "between_max":
        return v <= expected
    return False


def _apply_filters(
    rows: list[dict],
    numeric_filters: list[tuple[str, str, float]],
    crystal_filters: list[str],
    predicted_stable: bool | None,
) -> list[dict]:
    filtered = []
    for row in rows:
        ok = True

        for field, op, expected in numeric_filters:
            if not _match_filter(row.get(field), op, expected):
                ok = False
                break

        if not ok:
            continue

        if crystal_filters:
            crystal = str(row.get("crystal_system") or "").lower()
            if crystal not in crystal_filters:
                continue

        if predicted_stable is not None and row.get("predicted_stable") is not predicted_stable:
            continue

        filtered.append(row)

    return filtered


def _table_columns() -> list[str]:
    # Keep crystal_system adjacent to material_id for easier viewing.
    columns = ["material_id", "crystal_system"]
    for col in MATERIAL_OUTPUT_COLUMNS:
        if col not in columns:
            columns.append(col)
    return columns


def _upsert_range_field(payload: dict[str, Any], field_name: str, *, minimum: float | None = None, maximum: float | None = None) -> None:
    current = payload.get(field_name, {})
    if minimum is not None:
        current["min"] = minimum if "min" not in current else max(current["min"], minimum)
    if maximum is not None:
        current["max"] = maximum if "max" not in current else min(current["max"], maximum)
    if current:
        payload[field_name] = current


def _build_search_payload(question: str, limit: int, offset: int) -> tuple[dict[str, Any], list[str]]:
    elements = _extract_elements(question)
    formula = None if elements else _detect_formula(question)
    numeric_filters, crystal_filters, predicted_stable, is_metal = _extract_filters(question)

    payload: dict[str, Any] = {
        "query": question,
        "limit": limit,
        "offset": offset,
    }
    heuristics: list[str] = []

    if formula:
        payload["formula"] = formula
    if elements:
        payload["elements"] = elements
    if crystal_filters:
        payload["crystal_system"] = crystal_filters[0]
    if predicted_stable is not None:
        payload["is_stable"] = predicted_stable
    if is_metal is not None:
        payload["is_metal"] = is_metal

    for field, op, value in numeric_filters:
        if op in {">", ">=", "between_min"}:
            _upsert_range_field(payload, field, minimum=value)
        elif op in {"<", "<=", "between_max"}:
            _upsert_range_field(payload, field, maximum=value)
        elif op == "=":
            _upsert_range_field(payload, field, minimum=value, maximum=value)

    q = question.lower()
    if "lightweight" in q:
        _upsert_range_field(payload, "density", maximum=5.0)
        heuristics.append("Interpreted 'lightweight' as density <= 5 g/cm^3.")
    if "alloy" in q or "alloys" in q:
        payload["is_metal"] = True
        _upsert_range_field(payload, "num_elements", minimum=2)
        heuristics.append("Interpreted 'alloy' as metallic materials with at least two elements.")
    if "aerospace" in q:
        payload["is_stable"] = True if payload.get("is_stable") is None else payload["is_stable"]
        _upsert_range_field(payload, "bulk_modulus_vrh", minimum=40.0)
        _upsert_range_field(payload, "shear_modulus_vrh", minimum=20.0)
        heuristics.append("Interpreted 'aerospace' as stable materials with lightweight and stiffness bias.")
    if "cathode" in q and "battery" in q and not payload.get("elements"):
        payload["elements"] = ["Li", "O"]
        payload["is_stable"] = True if payload.get("is_stable") is None else payload["is_stable"]
        _upsert_range_field(payload, "num_elements", minimum=2)
        heuristics.append("Interpreted 'battery cathode' as stable Li-O containing multicomponent materials.")
    if ("semiconductor" in q or "semiconductors" in q) and payload.get("is_metal") is None:
        payload["is_metal"] = False
        _upsert_range_field(payload, "band_gap", minimum=0.1, maximum=3.5)
        heuristics.append("Interpreted 'semiconductor' as non-metallic materials with moderate band gap.")

    return payload, heuristics


def _as_request(payload: dict[str, Any]) -> AdvancedMaterialSearchRequest:
    range_fields = {
        "num_elements",
        "band_gap",
        "density",
        "volume",
        "energy_above_hull",
        "bulk_modulus_vrh",
        "shear_modulus_vrh",
        "weighted_surface_energy",
        "work_function",
        "surface_anisotropy",
        "shape_factor",
    }
    normalized = payload.copy()
    for field_name in range_fields:
        if field_name in normalized and isinstance(normalized[field_name], dict):
            normalized[field_name] = NumericRange(**normalized[field_name])
    return AdvancedMaterialSearchRequest(**normalized)


def search_materials_advanced_tool(
    query: str | None = None,
    formula: str | None = None,
    material_ids: list[str] | None = None,
    elements: list[str] | None = None,
    exclude_elements: list[str] | None = None,
    crystal_system: str | None = None,
    is_stable: bool | None = None,
    is_metal: bool | None = None,
    num_elements_min: float | None = None,
    num_elements_max: float | None = None,
    band_gap_min: float | None = None,
    band_gap_max: float | None = None,
    density_min: float | None = None,
    density_max: float | None = None,
    volume_min: float | None = None,
    volume_max: float | None = None,
    energy_above_hull_min: float | None = None,
    energy_above_hull_max: float | None = None,
    bulk_modulus_vrh_min: float | None = None,
    bulk_modulus_vrh_max: float | None = None,
    shear_modulus_vrh_min: float | None = None,
    shear_modulus_vrh_max: float | None = None,
    weighted_surface_energy_min: float | None = None,
    weighted_surface_energy_max: float | None = None,
    work_function_min: float | None = None,
    work_function_max: float | None = None,
    surface_anisotropy_min: float | None = None,
    surface_anisotropy_max: float | None = None,
    shape_factor_min: float | None = None,
    shape_factor_max: float | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    payload: dict[str, Any] = {
        "query": query,
        "formula": formula,
        "material_ids": material_ids or [],
        "elements": elements or [],
        "exclude_elements": exclude_elements or [],
        "crystal_system": crystal_system,
        "is_stable": is_stable,
        "is_metal": is_metal,
        "limit": limit,
        "offset": offset,
    }

    range_inputs = {
        "num_elements": (num_elements_min, num_elements_max),
        "band_gap": (band_gap_min, band_gap_max),
        "density": (density_min, density_max),
        "volume": (volume_min, volume_max),
        "energy_above_hull": (energy_above_hull_min, energy_above_hull_max),
        "bulk_modulus_vrh": (bulk_modulus_vrh_min, bulk_modulus_vrh_max),
        "shear_modulus_vrh": (shear_modulus_vrh_min, shear_modulus_vrh_max),
        "weighted_surface_energy": (weighted_surface_energy_min, weighted_surface_energy_max),
        "work_function": (work_function_min, work_function_max),
        "surface_anisotropy": (surface_anisotropy_min, surface_anisotropy_max),
        "shape_factor": (shape_factor_min, shape_factor_max),
    }
    for field_name, (minimum, maximum) in range_inputs.items():
        if minimum is not None or maximum is not None:
            payload[field_name] = {"min": minimum, "max": maximum}

    request = _as_request({key: value for key, value in payload.items() if value not in (None, [], {})})
    response = advanced_search_materials(request)
    return {
        "intent": "advanced_material_search",
        "query": request.query,
        "formula": request.formula,
        "elements": request.elements,
        "columns": _table_columns(),
        "count": response["count"],
        "total_source_rows": response.get("total_source_rows", response["count"]),
        "data": response["data"],
        "materials_project": response,
    }


def ask_materials_project_tool(question: str, limit: int = 20, offset: int = 0) -> dict:
    """
    Unified Materials Project tool.
    Supports:
    - material_id lookup (mp-...)
    - formula lookup
    - natural language filters across material properties
    """
    question = (question or "").strip()
    if not question:
        raise ExternalServiceError(
            service="materials_project",
            message="question is required",
            status_code=400,
        )

    mp_id_match = _MP_ID_PATTERN.search(question)
    if mp_id_match:
        material_id = mp_id_match.group(1)
        return {
            "intent": "material_by_id",
            "material_id": material_id,
            "materials_project": get_material_by_id_tool(material_id),
            "columns": _table_columns(),
        }

    request_payload, heuristics = _build_search_payload(question, limit, offset)
    if not any(
        (
            request_payload.get("formula"),
            request_payload.get("elements"),
            request_payload.get("crystal_system"),
            request_payload.get("is_stable") is not None,
            request_payload.get("is_metal") is not None,
            any(field in request_payload for field in _FIELD_ALIASES.values()),
        )
    ):
        raise ExternalServiceError(
            service="materials_project",
            message="No material formula, material_id, elements, or supported filters found in question",
            status_code=400,
        )

    request = _as_request(request_payload)
    mp_payload = advanced_search_materials(request)
    paged_rows = mp_payload.get("data", [])

    oqmd_payload = None
    oqmd_errors = []
    if config.OQMD_REQUIRED and request.formula:
        try:
            oqmd_payload = search_oqmd(request.formula, limit, offset)
        except ExternalServiceError as exc:
            oqmd_errors.append(exc.to_dict())

    response = {
        "intent": "material_search_federated" if request.formula else "advanced_material_search",
        "question": question,
        "formula": request.formula,
        "elements": request.elements,
        "applied_filters": request.model_dump(exclude_none=True),
        "heuristics": heuristics,
        "columns": _table_columns(),
        "total_source_rows": mp_payload.get("total_source_rows", len(paged_rows)),
        "count": len(paged_rows),
        "data": paged_rows,
        "materials_project": {
            "count": len(paged_rows),
            "data": paged_rows,
            "query": mp_payload.get("query", request.model_dump(exclude_none=True)),
        },
        "oqmd": oqmd_payload,
    }

    if oqmd_errors:
        response["errors"] = oqmd_errors

    return response
