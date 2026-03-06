import re
from typing import Any

from app.cache.redis_cache import get_cache, set_cache
from app.config import config
from app.models.schemas import MaterialByIdRequest, MaterialSearchRequest
from app.services.exceptions import ExternalServiceError
from app.services.materials_service import MATERIAL_OUTPUT_COLUMNS, get_material_by_id, search_material
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
        set_cache(cache_key, result)

    return result


def get_material_by_id_tool(material_id: str) -> dict:
    request = MaterialByIdRequest(material_id=material_id)
    return get_material_by_id(request.material_id)


_MP_ID_PATTERN = re.compile(r"\b(mp-[A-Za-z0-9-]+)\b")
# Supports both single-element (e.g., Dy) and multi-element formulas (e.g., Fe2O3).
_FORMULA_PATTERN = re.compile(r"\b([A-Z][a-z]?\d*(?:[A-Z][a-z]?\d*)*)\b")

_FIELD_ALIASES = {
    "shear modulus vrh": "shear_modulus_vrh",
    "shear_modulus_vrh": "shear_modulus_vrh",
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


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _detect_formula(question: str) -> str | None:
    explicit_material_match = re.search(r"\bmaterial\s+([A-Z][a-z]?\d*(?:[A-Z][a-z]?\d*)*)\b", question)
    formula_match = explicit_material_match or _FORMULA_PATTERN.search(question)
    return formula_match.group(1) if formula_match else None


def _normalize_field(raw: str) -> str | None:
    key = " ".join(raw.lower().strip().split())
    return _FIELD_ALIASES.get(key)


def _extract_filters(question: str) -> tuple[list[tuple[str, str, float]], list[str], bool | None]:
    q = question.lower()
    filters: list[tuple[str, str, float]] = []
    crystal_filters: list[str] = []
    predicted_stable: bool | None = None

    # Example: work function between 4.5 and 5.5
    for match in re.finditer(
        r"(work function|work_function)\s*(?:between|from)\s*([0-9]*\.?[0-9]+)\s*(?:and|to)\s*([0-9]*\.?[0-9]+)",
        q,
    ):
        field = _normalize_field(match.group(1))
        if field:
            filters.append((field, "between_min", float(match.group(2))))
            filters.append((field, "between_max", float(match.group(3))))

    # Example: vol >200, dens <3, band gap >= 2
    for match in re.finditer(
        r"(shear modulus vrh|density|dens|weighted surface energy|work function|band gap|volume|vol|shape factor|surface anisotropy)\s*(>=|<=|>|<|=)\s*([0-9]*\.?[0-9]+)",
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
        r"(shear modulus vrh|density|dens|weighted surface energy|work function|band gap|volume|vol|shape factor|surface anisotropy)\s*(?:is\s*)?(above|below|greater than|less than)\s*([0-9]*\.?[0-9]+)",
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

    for cs in _CRYSTAL_SYSTEMS:
        if re.search(rf"\b{cs}\b", q):
            crystal_filters.append(cs)

    return filters, crystal_filters, predicted_stable


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

    formula = _detect_formula(question)
    numeric_filters, crystal_filters, predicted_stable = _extract_filters(question)

    fetch_limit = min(max((limit + offset) * 20, 200), 1000)
    mp_payload = search_material(formula, fetch_limit, 0)
    mp_rows = mp_payload.get("data", [])
    filtered_rows = _apply_filters(mp_rows, numeric_filters, crystal_filters, predicted_stable)

    paged_rows = filtered_rows[offset : offset + limit]

    oqmd_payload = None
    oqmd_errors = []
    if config.OQMD_REQUIRED and formula:
        try:
            oqmd_payload = search_oqmd(formula, limit, offset)
        except ExternalServiceError as exc:
            oqmd_errors.append(exc.to_dict())

    response = {
        "intent": "material_search_federated",
        "question": question,
        "formula": formula,
        "applied_filters": {
            "numeric": [{"field": f, "op": op, "value": v} for f, op, v in numeric_filters],
            "crystal_system": crystal_filters,
            "predicted_stable": predicted_stable,
        },
        "columns": _table_columns(),
        "total_source_rows": len(mp_rows),
        "count": len(paged_rows),
        "data": paged_rows,
        "materials_project": {
            "count": len(paged_rows),
            "data": paged_rows,
        },
        "oqmd": oqmd_payload,
    }

    if oqmd_errors:
        response["errors"] = oqmd_errors

    if not paged_rows and not numeric_filters and not crystal_filters and predicted_stable is None:
        raise ExternalServiceError(
            service="materials_project",
            message="No material formula or material_id found in question",
            status_code=400,
        )

    return response
